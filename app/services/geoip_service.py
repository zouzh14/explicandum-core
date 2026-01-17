"""
IP地理位置检测服务
用于检测用户IP是否来自中国大陆、港澳台地区
"""

import requests
import re
from typing import Optional, Tuple
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class GeoIPService:
    """IP地理位置检测服务"""

    # 中国大陆、香港、澳门、台湾的IP段
    CHINA_IP_RANGES = [
        # 中国大陆主要IP段
        r"^1\.0\.1\.",
        r"^1\.0\.2\.",
        r"^1\.0\.3\.",
        r"^1\.0\.4\.",
        r"^1\.0\.5\.",
        r"^1\.0\.6\.",
        r"^1\.0\.7\.",
        r"^1\.0\.8\.",
        r"^1\.0\.9\.",
        r"^1\.0\.16\.",
        r"^1\.2\.0\.",
        r"^1\.4\.1\.",
        r"^1\.4\.2\.",
        r"^1\.4\.5\.",
        r"^1\.8\.0\.",
        r"^1\.8\.1\.",
        r"^1\.8\.2\.",
        r"^1\.8\.3\.",
        r"^1\.12\.0\.",
        r"^1\.12\.1\.",
        r"^14\.0\.0\.",
        r"^14\.0\.1\.",
        r"^14\.0\.2\.",
        r"^14\.0\.3\.",
        r"^14\.0\.4\.",
        r"^27\.0\.0\.",
        r"^27\.0\.1\.",
        r"^27\.0\.2\.",
        r"^27\.0\.3\.",
        r"^27\.0\.4\.",
        r"^36\.0\.0\.",
        r"^36\.0\.1\.",
        r"^36\.0\.2\.",
        r"^36\.0\.3\.",
        r"^36\.0\.4\.",
        r"^39\.0\.0\.",
        r"^39\.0\.1\.",
        r"^39\.0\.2\.",
        r"^39\.0\.3\.",
        r"^39\.0\.4\.",
        r"^42\.0\.0\.",
        r"^42\.0\.1\.",
        r"^42\.0\.2\.",
        r"^42\.0\.3\.",
        r"^42\.0\.4\.",
        r"^49\.0\.0\.",
        r"^49\.0\.1\.",
        r"^49\.0\.2\.",
        r"^49\.0\.3\.",
        r"^49\.0\.4\.",
        r"^58\.0\.0\.",
        r"^58\.0\.1\.",
        r"^58\.0\.2\.",
        r"^58\.0\.3\.",
        r"^58\.0\.4\.",
        r"^59\.0\.0\.",
        r"^59\.0\.1\.",
        r"^59\.0\.2\.",
        r"^59\.0\.3\.",
        r"^59\.0\.4\.",
        r"^60\.0\.0\.",
        r"^60\.0\.1\.",
        r"^60\.0\.2\.",
        r"^60\.0\.3\.",
        r"^60\.0\.4\.",
        r"^61\.0\.0\.",
        r"^61\.0\.1\.",
        r"^61\.0\.2\.",
        r"^61\.0\.3\.",
        r"^61\.0\.4\.",
        r"^101\.0\.0\.",
        r"^101\.0\.1\.",
        r"^101\.0\.2\.",
        r"^101\.0\.3\.",
        r"^101\.0\.4\.",
        r"^103\.0\.0\.",
        r"^103\.0\.1\.",
        r"^103\.0\.2\.",
        r"^103\.0\.3\.",
        r"^103\.0\.4\.",
        r"^106\.0\.0\.",
        r"^106\.0\.1\.",
        r"^106\.0\.2\.",
        r"^106\.0\.3\.",
        r"^106\.0\.4\.",
        r"^110\.0\.0\.",
        r"^110\.0\.1\.",
        r"^110\.0\.2\.",
        r"^110\.0\.3\.",
        r"^110\.0\.4\.",
        r"^111\.0\.0\.",
        r"^111\.0\.1\.",
        r"^111\.0\.2\.",
        r"^111\.0\.3\.",
        r"^111\.0\.4\.",
        r"^112\.0\.0\.",
        r"^112\.0\.1\.",
        r"^112\.0\.2\.",
        r"^112\.0\.3\.",
        r"^112\.0\.4\.",
        r"^113\.0\.0\.",
        r"^113\.0\.1\.",
        r"^113\.0\.2\.",
        r"^113\.0\.3\.",
        r"^113\.0\.4\.",
        r"^114\.0\.0\.",
        r"^114\.0\.1\.",
        r"^114\.0\.2\.",
        r"^114\.0\.3\.",
        r"^114\.0\.4\.",
        r"^115\.0\.0\.",
        r"^115\.0\.1\.",
        r"^115\.0\.2\.",
        r"^115\.0\.3\.",
        r"^115\.0\.4\.",
        r"^116\.0\.0\.",
        r"^116\.0\.1\.",
        r"^116\.0\.2\.",
        r"^116\.0\.3\.",
        r"^116\.0\.4\.",
        r"^117\.0\.0\.",
        r"^117\.0\.1\.",
        r"^117\.0\.2\.",
        r"^117\.0\.3\.",
        r"^117\.0\.4\.",
        r"^118\.0\.0\.",
        r"^118\.0\.1\.",
        r"^118\.0\.2\.",
        r"^118\.0\.3\.",
        r"^118\.0\.4\.",
        r"^119\.0\.0\.",
        r"^119\.0\.1\.",
        r"^119\.0\.2\.",
        r"^119\.0\.3\.",
        r"^119\.0\.4\.",
        r"^120\.0\.0\.",
        r"^120\.0\.1\.",
        r"^120\.0\.2\.",
        r"^120\.0\.3\.",
        r"^120\.0\.4\.",
        r"^121\.0\.0\.",
        r"^121\.0\.1\.",
        r"^121\.0\.2\.",
        r"^121\.0\.3\.",
        r"^121\.0\.4\.",
        r"^122\.0\.0\.",
        r"^122\.0\.1\.",
        r"^122\.0\.2\.",
        r"^122\.0\.3\.",
        r"^122\.0\.4\.",
        r"^123\.0\.0\.",
        r"^123\.0\.1\.",
        r"^123\.0\.2\.",
        r"^123\.0\.3\.",
        r"^123\.0\.4\.",
        r"^124\.0\.0\.",
        r"^124\.0\.1\.",
        r"^124\.0\.2\.",
        r"^124\.0\.3\.",
        r"^124\.0\.4\.",
        r"^125\.0\.0\.",
        r"^125\.0\.1\.",
        r"^125\.0\.2\.",
        r"^125\.0\.3\.",
        r"^125\.0\.4\.",
        # 香港IP段
        r"^202\.40\.0\.",
        r"^202\.40\.1\.",
        r"^202\.40\.2\.",
        r"^202\.40\.3\.",
        r"^202\.40\.4\.",
        r"^203\.80\.0\.",
        r"^203\.80\.1\.",
        r"^203\.80\.2\.",
        r"^203\.80\.3\.",
        r"^203\.80\.4\.",
        r"^203\.81\.0\.",
        r"^203\.81\.1\.",
        r"^203\.81\.2\.",
        r"^203\.81\.3\.",
        r"^203\.81\.4\.",
        r"^203\.82\.0\.",
        r"^203\.82\.1\.",
        r"^203\.82\.2\.",
        r"^203\.82\.3\.",
        r"^203\.82\.4\.",
        r"^203\.83\.0\.",
        r"^203\.83\.1\.",
        r"^203\.83\.2\.",
        r"^203\.83\.3\.",
        r"^203\.83\.4\.",
        r"^210\.0\.0\.",
        r"^210\.0\.1\.",
        r"^210\.0\.2\.",
        r"^210\.0\.3\.",
        r"^210\.0\.4\.",
        # 澳门IP段
        r"^202\.175\.0\.",
        r"^202\.175\.1\.",
        r"^202\.175\.2\.",
        r"^202\.175\.3\.",
        r"^202\.175\.4\.",
        # 台湾IP段
        r"^202\.39\.0\.",
        r"^202\.39\.1\.",
        r"^202\.39\.2\.",
        r"^202\.39\.3\.",
        r"^202\.39\.4\.",
        r"^202\.133\.0\.",
        r"^202\.133\.1\.",
        r"^202\.133\.2\.",
        r"^202\.133\.3\.",
        r"^202\.133\.4\.",
        r"^210\.60\.0\.",
        r"^210\.60\.1\.",
        r"^210\.60\.2\.",
        r"^210\.60\.3\.",
        r"^210\.60\.4\.",
        r"^210\.61\.0\.",
        r"^210\.61\.1\.",
        r"^210\.61\.2\.",
        r"^210\.61\.3\.",
        r"^210\.61\.4\.",
        r"^211\.72\.0\.",
        r"^211\.72\.1\.",
        r"^211\.72\.2\.",
        r"^211\.72\.3\.",
        r"^211\.72\.4\.",
        r"^211\.73\.0\.",
        r"^211\.73\.1\.",
        r"^211\.73\.2\.",
        r"^211\.73\.3\.",
        r"^211\.73\.4\.",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 5

    def is_china_ip(self, ip_address: str) -> Tuple[bool, str]:
        """
        检测IP是否来自中国大陆、港澳台地区

        Args:
            ip_address: IP地址

        Returns:
            Tuple[bool, str]: (是否来自中国, 地区名称)
        """
        # 首先使用本地IP段匹配
        for pattern in self.CHINA_IP_RANGES:
            if re.match(pattern, ip_address):
                return self._get_region_by_ip_pattern(ip_address, pattern)

        # 如果本地匹配失败，使用在线API
        try:
            return self._check_with_online_api(ip_address)
        except Exception as e:
            logger.error(f"在线IP检测失败: {e}")
            return False, "unknown"

    def _get_region_by_ip_pattern(
        self, ip_address: str, pattern: str
    ) -> Tuple[bool, str]:
        """根据IP模式判断地区"""
        if (
            pattern.startswith("^202.40")
            or pattern.startswith("^203.8")
            or pattern.startswith("^210.0")
        ):
            return True, "Hong Kong"
        elif pattern.startswith("^202.175"):
            return True, "Macau"
        elif (
            pattern.startswith("^202.39")
            or pattern.startswith("^202.133")
            or pattern.startswith("^210.6")
            or pattern.startswith("^211.7")
        ):
            return True, "Taiwan"
        else:
            return True, "Mainland China"

    def _check_with_online_api(self, ip_address: str) -> Tuple[bool, str]:
        """使用在线API检测IP地理位置"""
        try:
            # 使用免费的IP地理位置API
            response = self.session.get(f"http://ip-api.com/json/{ip_address}")
            if response.status_code == 200:
                data = response.json()
                country_code = data.get("countryCode", "").upper()
                region = data.get("regionName", "")

                if country_code == "CN":
                    return True, "Mainland China"
                elif country_code == "HK":
                    return True, "Hong Kong"
                elif country_code == "MO":
                    return True, "Macau"
                elif country_code == "TW":
                    return True, "Taiwan"
                else:
                    return False, country_code

            # 备用API
            response = self.session.get(f"https://ipinfo.io/{ip_address}/json")
            if response.status_code == 200:
                data = response.json()
                country = data.get("country", "").upper()

                if country == "CN":
                    return True, "Mainland China"
                elif country == "HK":
                    return True, "Hong Kong"
                elif country == "MO":
                    return True, "Macau"
                elif country == "TW":
                    return True, "Taiwan"
                else:
                    return False, country

        except Exception as e:
            logger.error(f"IP地理位置检测失败: {e}")
            return False, "unknown"

        return False, "unknown"

    def get_client_ip(self, request) -> str:
        """从请求中获取客户端真实IP"""
        # 尝试从各种头部获取真实IP
        ip_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "X-Client-IP",
            "CF-Connecting-IP",  # Cloudflare
            "True-Client-IP",
            "HTTP_X_FORWARDED_FOR",
            "HTTP_X_REAL_IP",
            "HTTP_X_CLIENT_IP",
            "HTTP_CF_CONNECTING_IP",
            "HTTP_TRUE_CLIENT_IP",
        ]

        for header in ip_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For可能包含多个IP，取第一个
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                # 验证IP格式
                if self._is_valid_ip(ip):
                    return ip

        # 如果没有找到代理头，使用远程地址
        ip = request.client.host if request.client else "unknown"
        return ip if self._is_valid_ip(ip) else "unknown"

    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        import socket

        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False


# 全局实例
geoip_service = GeoIPService()
