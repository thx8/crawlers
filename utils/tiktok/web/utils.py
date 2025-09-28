import os
import re
import json
import yaml
import httpx
import asyncio

from typing import Union


from utils.xbogus import XBogus as XB
from utils.hybrid.utils import (
    gen_random_str,
    get_timestamp,
    extract_valid_urls,

)

# 配置文件路径
path = os.path.abspath(os.path.dirname(__file__))

# 读取配置文件
with open(f"{path}/config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TokenManager:
    tiktok_manager = config.get("TokenManager").get("tiktok")
    token_conf = tiktok_manager.get("msToken", None)
    ttwid_conf = tiktok_manager.get("ttwid", None)
    odin_tt_conf = tiktok_manager.get("odin_tt", None)
    proxies_conf = tiktok_manager.get("proxies", None)
    proxies = {
        "http://": proxies_conf.get("http", None),
        "https://": proxies_conf.get("https", None),
    }

    @classmethod
    def gen_real_msToken(cls) -> str:
        """生成真实的msToken,当出现错误时返回虚假的值"""
        payload = json.dumps(
            {
                "magic": cls.token_conf["magic"],
                "version": cls.token_conf["version"],
                "dataType": cls.token_conf["dataType"],
                "strData": cls.token_conf["strData"],
                "tspFromClient": get_timestamp(),
            }
        )
        headers = {
            "User-Agent": cls.token_conf["User-Agent"],
            "Content-Type": "application/json",
        }

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.post(cls.token_conf["url"], headers=headers, content=payload)
                response.raise_for_status()
                msToken = str(httpx.Cookies(response.cookies).get("msToken"))
                return msToken
            except Exception as e:
                print(f"[错误] 获取 msToken 失败: {e}")
                return cls.gen_false_msToken()

    @classmethod
    def gen_false_msToken(cls) -> str:
        """生成随机msToken"""
        return gen_random_str(146) + "=="

    @classmethod
    def gen_ttwid(cls, cookie: str) -> Union[str, None]:
        """生成请求必带的ttwid"""
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.post(
                    cls.ttwid_conf["url"],
                    content=cls.ttwid_conf["data"],
                    headers={
                        "Cookie": cookie,
                        "Content-Type": "text/plain",
                    },
                )
                response.raise_for_status()
                ttwid = httpx.Cookies(response.cookies).get("ttwid")
                if ttwid is None:
                    print("[错误] ttwid 检查没有通过, 请更新配置文件")
                    return None
                return ttwid
            except Exception as e:
                print(f"[错误] 获取 ttwid 失败: {e}")
                return None

    @classmethod
    def gen_odin_tt(cls) -> Union[str, None]:
        """生成请求必带的odin_tt"""
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.get(cls.odin_tt_conf["url"])
                response.raise_for_status()
                odin_tt = httpx.Cookies(response.cookies).get("odin_tt")
                if odin_tt is None:
                    print("[错误] odin_tt 内容不符合要求")
                    return None
                return odin_tt
            except Exception as e:
                print(f"[错误] 获取 odin_tt 失败: {e}")
                return None


class BogusManager:
    @classmethod
    def xb_str_2_endpoint(cls, user_agent: str, endpoint: str) -> str:
        try:
            final_endpoint = XB(user_agent).getXBogus(endpoint)
            return final_endpoint[0]
        except Exception as e:
            print(f"[错误] 生成X-Bogus失败: {e}")
            return endpoint

    @classmethod
    def model_2_endpoint(cls, base_endpoint: str, params: dict, user_agent: str) -> str:
        if not isinstance(params, dict):
            print("[错误] 参数必须是字典类型")
            return base_endpoint
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            print(f"[错误] 生成X-Bogus失败: {e}")
            return base_endpoint
        separator = "&" if "?" in base_endpoint else "?"
        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"
        return final_endpoint


class AwemeIdFetcher:
    _TIKTOK_AWEMEID_PATTERN = re.compile(r"video/(\d+)")
    _TIKTOK_PHOTOID_PATTERN = re.compile(r"photo/(\d+)")
    _TIKTOK_NOTFOUND_PATTERN = re.compile(r"notfound")

    @classmethod
    async def get_aweme_id(cls, url: str) -> Union[str, None]:
        """获取TikTok作品aweme_id或photo_id"""
        if not isinstance(url, str):
            print("[错误] 输入参数必须是字符串")
            return None
        url = extract_valid_urls(url)
        if url is None:
            print("[错误] 输入的URL不合法")
            return None

        if "tiktok" and "@" in url:
            print(f"输入的URL无需重定向: {url}")
            video_match = cls._TIKTOK_AWEMEID_PATTERN.search(url)
            photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(url)
            if not video_match and not photo_match:
                print("[错误] 未在响应中找到 aweme_id 或 photo_id")
                return None
            return video_match.group(1) if video_match else photo_match.group(1)

        print(f"输入的URL需要重定向: {url}")
        transport = httpx.AsyncHTTPTransport(retries=10)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PATTERN.search(str(response.url)):
                        print("[错误] 页面不可用，可能是区域限制（代理）造成的")
                        return None
                    video_match = cls._TIKTOK_AWEMEID_PATTERN.search(str(response.url))
                    photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(str(response.url))
                    if not video_match and not photo_match:
                        print("[错误] 未在响应中找到 aweme_id 或 photo_id")
                        return None
                    return video_match.group(1) if video_match else photo_match.group(1)
                else:
                    print(f"[错误] 接口状态码异常 {response.status_code}")
                    return None
            except Exception as e:
                print(f"[错误] 请求失败: {e}")
                return None

    @classmethod
    async def get_all_aweme_id(cls, urls: list) -> list:
        """批量获取aweme_id"""
        if not isinstance(urls, list):
            print("[错误] 参数必须是列表类型")
            return []
        urls = extract_valid_urls(urls)
        if urls == []:
            print("[错误] 输入的URL列表不合法")
            return []
        aweme_ids = [cls.get_aweme_id(url) for url in urls]
        return await asyncio.gather(*aweme_ids)



class SecUserIdFetcher:
    # 预编译正则表达式
    _TIKTOK_SECUID_PARREN = re.compile(
        r"<script id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\" type=\"application/json\">(.*?)</script>"
    )
    _TIKTOK_UNIQUEID_PARREN = re.compile(r"/@([^/?]*)")
    _TIKTOK_NOTFOUND_PARREN = re.compile(r"notfound")

    @classmethod
    async def get_secuid(cls, url: str) -> Union[str, None]:
        """获取TikTok用户 sec_uid"""

        if not isinstance(url, str):
            print("[错误] 输入参数必须是字符串")
            return None

        url = extract_valid_urls(url)
        if url is None:
            print(f"[错误] 输入的URL不合法。类名: {cls.__name__}")
            return None

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        print(f"[错误] 页面不可用，可能是区域限制。类名: {cls.__name__}")
                        return None

                    match = cls._TIKTOK_SECUID_PARREN.search(str(response.text))
                    if not match:
                        print(f"[错误] 未在响应中找到 sec_uid，检查是否是用户主页。类名: {cls.__name__}")
                        return None

                    # 提取SIGI_STATE对象中的sec_uid
                    try:
                        data = json.loads(match.group(1))
                        default_scope = data.get("__DEFAULT_SCOPE__", {})
                        user_detail = default_scope.get("webapp.user-detail", {})
                        user_info = user_detail.get("userInfo", {}).get("user", {})
                        sec_uid = user_info.get("secUid")
                        if sec_uid is None:
                            print(f"[错误] sec_uid 获取失败, user_info={user_info}")
                            return None
                        return sec_uid
                    except Exception as e:
                        print(f"[错误] 解析 sec_uid JSON 失败: {e}")
                        return None
                else:
                    print(f"[错误] 接口状态码异常 {response.status_code}")
                    return None

            except httpx.RequestError as exc:
                print(f"[错误] 请求端点失败，url={url}, 代理={TokenManager.proxies}, 类名={cls.__name__}, 详情: {exc}")
                return None

    @classmethod
    async def get_all_secuid(cls, urls: list) -> list:
        """批量获取 sec_uid"""
        if not isinstance(urls, list):
            print("[错误] 参数必须是列表类型")
            return []

        urls = extract_valid_urls(urls)
        if urls == []:
            print(f"[错误] 输入的URL列表不合法。类名: {cls.__name__}")
            return []

        secuids = [cls.get_secuid(url) for url in urls]
        return await asyncio.gather(*secuids)

    @classmethod
    async def get_uniqueid(cls, url: str) -> Union[str, None]:
        """获取TikTok用户 unique_id"""

        if not isinstance(url, str):
            print("[错误] 输入参数必须是字符串")
            return None

        url = extract_valid_urls(url)
        if url is None:
            print(f"[错误] 输入的URL不合法。类名: {cls.__name__}")
            return None

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        print(f"[错误] 页面不可用，可能是区域限制。类名: {cls.__name__}")
                        return None

                    match = cls._TIKTOK_UNIQUEID_PARREN.search(str(response.url))
                    if not match:
                        print("[错误] 未在响应中找到 unique_id")
                        return None

                    unique_id = match.group(1)
                    if unique_id is None:
                        print(f"[错误] unique_id 获取失败, url={response.url}")
                        return None
                    return unique_id
                else:
                    print(f"[错误] 接口状态码异常 {response.status_code}")
                    return None

            except httpx.RequestError as exc:
                print(f"[错误] 连接端点失败 url={url}, 代理={TokenManager.proxies}, 类名={cls.__name__}, 详情: {exc}")
                return None

    @classmethod
    async def get_all_uniqueid(cls, urls: list) -> list:
        """批量获取 unique_id"""
        if not isinstance(urls, list):
            print("[错误] 参数必须是列表类型")
            return []

        urls = extract_valid_urls(urls)
        if urls == []:
            print(f"[错误] 输入的URL列表不合法。类名: {cls.__name__}")
            return []

        unique_ids = [cls.get_uniqueid(url) for url in urls]
        return await asyncio.gather(*unique_ids)
