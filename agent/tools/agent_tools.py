import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Any

import requests
from langchain_core.tools import tool

from utils.logger_handler import logger
from rag.rag_service import RagSummarizeService
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path

rag = RagSummarizeService()

user_ids = [
    "1001", "1002", "1003", "1004", "1005",
    "1006", "1007", "1008", "1009", "1010",
]

external_data: dict = {}

# =========================
# 高德 API 配置
# =========================
AMAP_KEY = agent_conf.get("amap_key", "").strip()
AMAP_IP_URL = "https://restapi.amap.com/v3/ip"
AMAP_DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
AMAP_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

# 可选：用于部署时从环境变量传用户真实 IP
# 例如在前端或网关把用户 IP 放入环境变量 USER_REAL_IP
USER_REAL_IP_ENV = agent_conf.get("user_real_ip_env", "USER_REAL_IP")


# =========================
# 通用辅助函数
# =========================
def _ensure_amap_key():
    if not AMAP_KEY:
        raise ValueError(
            "未配置高德 API Key，请在 config/agent.yml 中添加 amap_key"
        )


def _safe_request(url: str, params: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise ValueError("接口返回不是合法 JSON 对象")
        return data
    except requests.RequestException as e:
        raise RuntimeError(f"请求失败：{e}") from e
    except ValueError as e:
        raise RuntimeError(f"解析响应失败：{e}") from e


def _normalize_city_name(city: str) -> str:
    """尽量兼容用户输入，如 北京/北京市/杭州/杭州市"""
    city = (city or "").strip()
    if not city:
        raise ValueError("城市名称不能为空")
    return city


def _extract_best_city_from_district(district: Dict[str, Any]) -> str:
    """
    高德返回里直辖市 city 可能为空列表，所以做兼容处理
    """
    name = district.get("name", "")
    level = district.get("level", "")
    if level in ("city", "district", "province"):
        return name
    return name or "未知城市"


def _get_city_adcode(city_name: str) -> str:
    """
    根据城市名称查 adcode
    """
    _ensure_amap_key()
    city_name = _normalize_city_name(city_name)

    params = {
        "key": AMAP_KEY,
        "keywords": city_name,
        "subdistrict": 0,
        "extensions": "base",
        "output": "JSON",
    }
    data = _safe_request(AMAP_DISTRICT_URL, params)

    if data.get("status") != "1":
        raise RuntimeError(f"行政区查询失败：{data.get('info', '未知错误')}")

    districts = data.get("districts", [])
    if not districts:
        raise ValueError(f"未找到城市：{city_name}")

    return districts[0].get("adcode", "")


def _get_city_by_ip(ip: Optional[str] = None) -> Dict[str, str]:
    """
    根据 IP 获取城市。
    不传 ip 时，高德文档说明会根据请求来源定位。
    但注意：在服务端部署场景下，这通常会定位到服务器出口 IP，而不是最终用户 IP。
    """
    _ensure_amap_key()

    params = {
        "key": AMAP_KEY,
        "output": "JSON",
    }
    if ip:
        params["ip"] = ip

    data = _safe_request(AMAP_IP_URL, params)

    if data.get("status") != "1":
        raise RuntimeError(f"IP定位失败：{data.get('info', '未知错误')}")

    province = data.get("province", "") or ""
    city = data.get("city", "") or ""
    adcode = data.get("adcode", "") or ""

    # 某些情况下 city 可能为空或是 [] 的字符串表现
    if isinstance(city, list):
        city = province

    return {
        "province": province,
        "city": city if city else province,
        "adcode": adcode,
    }


def _fetch_live_weather(adcode: str) -> Dict[str, Any]:
    """
    根据 adcode 获取实时天气
    """
    _ensure_amap_key()

    if not adcode:
        raise ValueError("adcode 不能为空")

    params = {
        "key": AMAP_KEY,
        "city": adcode,
        "extensions": "base",
        "output": "JSON",
    }
    data = _safe_request(AMAP_WEATHER_URL, params)

    if data.get("status") != "1":
        raise RuntimeError(f"天气查询失败：{data.get('info', '未知错误')}")

    lives = data.get("lives", [])
    if not lives:
        raise RuntimeError("天气查询成功，但未返回实时天气数据")

    return lives[0]


# =========================
# Agent 工具
# =========================
@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="获取指定城市的实时天气，以消息字符串的形式返回")
def get_weather(city: str) -> str:
    """
    用户主动指定城市时，查询该城市实时天气
    """
    try:
        city = _normalize_city_name(city)
        adcode = _get_city_adcode(city)
        weather = _fetch_live_weather(adcode)

        province = weather.get("province", "")
        city_name = weather.get("city", "")
        weather_text = weather.get("weather", "未知")
        temperature = weather.get("temperature", "未知")
        humidity = weather.get("humidity", "未知")
        winddirection = weather.get("winddirection", "未知")
        windpower = weather.get("windpower", "未知")
        reporttime = weather.get("reporttime", "未知")

        return (
            f"{province}{city_name}当前天气：{weather_text}，"
            f"温度{temperature}℃，湿度{humidity}%，"
            f"{winddirection}风，风力{windpower}级，"
            f"数据更新时间：{reporttime}"
        )
    except Exception as e:
        logger.exception("[get_weather] 查询天气失败")
        return f"获取{city}天气失败：{e}"


@tool(description="获取用户所在城市的名称，以纯字符串形式返回")
def get_user_location() -> str:
    """
    默认尝试通过 IP 获取城市。
    注意：
    1. 本地运行时，不传 ip 通常会基于当前机器的公网出口 IP 定位。
    2. 部署到服务器后，不改前端/网关的话，拿到的往往是服务器所在城市。
    3. 更准确的做法是前端把客户端真实 IP 或城市传给后端。
    """
    try:
        real_ip = os.getenv(USER_REAL_IP_ENV, "").strip() or None
        loc = _get_city_by_ip(real_ip)
        return loc["city"] or loc["province"] or "未知城市"
    except Exception as e:
        logger.exception("[get_user_location] 获取城市失败")
        return f"未知城市（原因：{e}）"


@tool(description="获取用户的ID，以纯字符串形式返回")
def get_user_id() -> str:
    import random
    return random.choice(user_ids)


@tool(description="获取当前月份，以纯字符串形式返回")
def get_current_month() -> str:
    """
    返回中国时区的真实当前月份，格式：YYYY-MM
    """
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m")


def generate_external_data():
    """
    将 CSV 读取为：
    {
        "user_id": {
            "month": {
                "特征": xxx,
                "效率": xxx,
                "耗材": xxx,
                "对比": xxx
            }
        }
    }
    """
    if not external_data:
        external_data_path = get_abs_path(agent_conf["external_data_path"])
        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件 {external_data_path} 不存在")

        with open(external_data_path, "r", encoding="utf-8") as f:
            for line in f.readlines()[1:]:
                arr = line.strip().split(",")
                if len(arr) < 6:
                    logger.warning(f"[generate_external_data] 跳过非法行：{line}")
                    continue

                user_id = arr[0].replace('"', "")
                feature = arr[1].replace('"', "")
                efficiency = arr[2].replace('"', "")
                consumables = arr[3].replace('"', "")
                comparison = arr[4].replace('"', "")
                time = arr[5].replace('"', "")

                if user_id not in external_data:
                    external_data[user_id] = {}

                external_data[user_id][time] = {
                    "特征": feature,
                    "效率": efficiency,
                    "耗材": consumables,
                    "对比": comparison,
                }


@tool(description="从外部系统中获取指定用户在所有有效月份的使用记录，以纯字符串形式返回， 如果未检索到返回空字符串")
def fetch_external_data(user_id: str) -> str:
    generate_external_data()  # 确保外部数据被加载

    available_months = []  # 用于存储所有有效的月份和数据
    for month, data in external_data.get(user_id, {}).items():
        if data:  # 确保该月份有数据
            available_months.append(f"{month}: {data}")

    if not available_months:
        logger.warning(f"[fetch_external_data] 未检索到用户：{user_id} 的使用记录数据")
        return ""  # 如果没有有效的月份数据，返回空字符串

    # 将所有有效月份的数据合并为一个字符串返回
    return "\n".join(available_months)
    


@tool(description="无入参，无返回值，调用后触发中间件自动为报告生成的场景动态注入上下文信息，为后续提示词切换提供上下文信息")
def fill_context_for_report():
    return "fill_context_for_report已调用"