# -*- coding: utf-8 -*-

import base64
import gzip
import html as _html
import json
import re
import sys
from urllib.parse import quote, unquote

sys.path.append('..')
try:
    from base.spider import BaseSpider
except ImportError:
    class BaseSpider:
        def getProxyUrl(self):
            return None
        def getDependence(self):
            return []

try:
    import requests
except ImportError:
    requests = None
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
except ImportError:
    AES = None

__all__ = ["Spider"]

_HOST = "https://bh5873.top"
_API = _HOST + "/api"
_AES_KEY = bytes([0xf6, 0x32, 0x2f, 0xa1, 0xc0, 0x64, 0x37, 0x0e, 0xa4, 0x0c, 0x8c, 0xdc, 0x20, 0x64, 0x9f, 0x8e])
_IMG_XOR_KEY = 18
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


class Spider(BaseSpider):
    filterable = False
    searchable = True

    def getName(self):
        return "笔盒"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _UA,
            "Accept": "application/json",
            "Referer": _HOST + "/home",
        })
        self.cache = {}

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(?:m3u8|mp4|flv)", url, re.I))

    def manualVideoCheck(self):
        return False

    def _aes_decrypt(self, hex_data):
        try:
            raw = bytes.fromhex(hex_data)
            if len(raw) < 16:
                return hex_data
            iv, ct = raw[:16], raw[16:]
            cipher = AES.new(_AES_KEY, AES.MODE_CBC, iv=iv)
            pt = unpad(cipher.decrypt(ct), 16)
            return pt.decode("utf-8")
        except Exception:
            return ""

    def _api(self, path, params=None, method="GET", body=None):
        url = _API + path
        kwargs = {"timeout": 15}
        if params:
            kwargs["params"] = params
        if body:
            kwargs["data"] = json.dumps(body)
            kwargs.setdefault("headers", {})["Content-Type"] = "application/json"
        try:
            resp = self.session.request(method, url, **kwargs)
            # 修复: 接受 200-299 状态码 (parse-url 返回 201)
            if not (200 <= resp.status_code < 300):
                return {}
            j = resp.json()
            if j.get("code") != 200:
                return {}
            enc = j.get("data", "")
            if not enc or not isinstance(enc, str) or len(enc) < 32:
                return enc if isinstance(enc, (dict, list)) else {}
            dec = self._aes_decrypt(enc)
            return json.loads(dec) if dec else {}
        except Exception:
            return {}

    def _image_proxy_url(self, raw_url):
        if not raw_url or not isinstance(raw_url, str):
            return ""
        # 修复: 所有图片统一走代理，确保带正确的 Referer / User-Agent
        encoded = base64.b64encode(raw_url.encode("utf-8")).decode("utf-8")
        proxy_base = self.getProxyUrl()
        if not proxy_base:
            proxy_base = "http://127.0.0.1:9980/proxy?do=py"
        sep = "&" if "?" in proxy_base else "?"
        return proxy_base + sep + "type=bh_img&url=" + quote(encoded, safe="")

    def _clean_title(self, text):
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = _html.unescape(text)
        return text.strip()

    def _make_item(self, item):
        return {
            "vod_id": str(item.get("vodId", "")),
            "vod_name": self._clean_title(item.get("vodName", "")),
            "vod_pic": self._image_proxy_url(item.get("vodPic", "")),
            "vod_remarks": item.get("rating", ""),
        }

    _CLASS_IDS = [
        "推荐", "最新", "国产精品", "黑丝巨乳", "学生空姐", "人妻少妇",
        "偷拍自拍", "无码流出", "动漫CG", "口交颜射", "SM调教",
        "美腿丝袜", "约炮外遇", "乱伦熟女", "野战车震", "露出暴露",
        "绿帽淫妻", "多人群P", "制服诱惑", "萝莉嫩妹", "巨乳肥臀",
        "三级伦理", "剧情有码", "同性耽美", "网红主播", "ASMR", "专题",
    ]

    def homeContent(self, filter=False):
        classes = []
        for tid in self._CLASS_IDS:
            classes.append({"type_name": tid, "type_id": tid})
        return {"class": classes}

    def homeVideoContent(self):
        carousel = self._api("/vod/carousel")
        vods = []
        if isinstance(carousel, list) and carousel:
            for item in carousel[:20]:
                vods.append(self._make_item(item))
        if not vods:
            latest = self._api("/vod/latest", {"page": 1, "limit": 20})
            data = latest.get("data", []) if isinstance(latest, dict) else []
            for item in data:
                vods.append(self._make_item(item))
        return {"list": vods}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        page = max(1, int(pg))
        limit = 24

        if tid == "推荐":
            data = self._api("/vod/recommend", {"page": page, "limit": limit})
            vod_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

        elif tid == "最新":
            data = self._api("/vod/latest", {"page": page, "limit": limit})
            vod_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

        elif tid == "专题":
            return self._topic_folder_list(page, limit)

        elif tid.startswith("topic:"):
            return self._topic_videos(tid)

        else:
            data = self._api("/vod/search", {"keyword": tid, "page": page})
            vod_list = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])

        items = []
        for item in vod_list:
            items.append(self._make_item(item))
            self.cache[item.get("vodId", "")] = item

        return {
            "list": items,
            "page": page,
            "pagecount": data.get("totalPages", 99) if isinstance(data, dict) else 99,
            "limit": limit,
            "total": data.get("total", 0) if isinstance(data, dict) else len(items),
        }

    def _topic_folder_list(self, page, limit):
        items = []
        data = self._api("/topic/list", {"page": page})
        topics = data.get("data", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        for t in topics:
            cover = ""
            related = t.get("relatedVods", [])
            if isinstance(related, list) and related:
                first = related[0]
                if isinstance(first, dict):
                    cover = self._image_proxy_url(first.get("vodPic", ""))
            items.append({
                "vod_id": "topic:" + str(t.get("topicId", "")),
                "vod_name": str(t.get("topicName", "")).strip(),
                "vod_pic": cover,
                "vod_remarks": "",
                "vod_tag": "folder",
            })
        return {
            "list": items,
            "page": page,
            "pagecount": data.get("totalPages", 1) if isinstance(data, dict) else 1,
            "limit": limit,
            "total": data.get("total", 0) if isinstance(data, dict) else len(items),
        }

    def _topic_videos(self, tid):
        topic_id = tid.replace("topic:", "")
        topic = self._api("/topic/detail/" + topic_id)
        related = topic.get("relatedVods", []) if isinstance(topic, dict) else []
        items = []
        for r in related:
            items.append(self._make_item(r))
        return {
            "list": items,
            "page": 1,
            "pagecount": 1,
            "limit": len(items),
            "total": len(items),
        }

    def detailContent(self, ids):
        vod_id = str(ids[0]) if ids else ""
        if not vod_id:
            return {"list": []}

        detail = self._api("/vod/detail/" + vod_id)
        if not detail or not isinstance(detail, dict) or not detail.get("vodId"):
            return {"list": [{"vod_id": vod_id, "vod_name": "加载失败", "vod_pic": "", "vod_remarks": ""}]}

        vod_play_from = []
        vod_play_url = []
        play_source = detail.get("vodPlaySource", {})
        if isinstance(play_source, dict):
            for src_name, episodes in play_source.items():
                if not isinstance(episodes, list) or not episodes:
                    continue
                vod_play_from.append(src_name)
                parts = []
                for ep in episodes:
                    play_url = ep.get("playUrl") or ep.get("url", "")
                    label = ep.get("flag", "") or "播放"
                    parts.append(label + "$" + play_url)
                vod_play_url.append("#".join(parts))

        if not vod_play_from:
            vod_play_from = ["默认"]
            vod_play_url = [""]

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": str(detail.get("vodName", "")).strip(),
            "vod_pic": self._image_proxy_url(detail.get("vodPic", "")),
            "type_name": (detail.get("vodClass", [""]) or [""])[0],
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": detail.get("rating", ""),
            "vod_actor": "",
            "vod_director": "",
            "vod_content": detail.get("vodContent", ""),
            "vod_play_from": "$$$".join(vod_play_from),
            "vod_play_url": "$$$".join(vod_play_url),
        }]}

    def playerContent(self, flag, id, vipFlags=None):
        url = unquote(str(id))

        def _direct(u):
            return bool(re.search(r"\.(?:m3u8|mp4|flv)($|\?|&)", u, re.I))

        hdr = json.dumps({"User-Agent": _UA, "Referer": _HOST + "/"})

        # 直链直接播放
        if _direct(url):
            return {"parse": 0, "playUrl": "", "url": url, "header": hdr}

        # 尝试API解析 (修复: 现在能正确处理201状态码)
        try:
            parsed = self._api("/vod/parse-url", method="POST", body={
                "playerFrom": flag or "",
                "playUrl": url,
            })
            if isinstance(parsed, dict) and parsed.get("url"):
                parsed_url = parsed["url"]
                if _direct(parsed_url):
                    return {"parse": 0, "playUrl": "", "url": parsed_url, "header": hdr}
                # 如果解析后仍非直链，但URL变了，更新url继续尝试
                if parsed_url != url:
                    url = parsed_url
        except Exception:
            pass

        if _direct(url):
            return {"parse": 0, "playUrl": "", "url": url, "header": hdr}

        # 非直链，交给TVBox webview解析
        return {"parse": 1, "playUrl": "", "url": url, "header": hdr}

    def searchContent(self, key, quick=False, pg=1):
        page = max(1, int(pg))
        data = self._api("/vod/search", {"keyword": key, "page": page})
        vod_list = data.get("data", []) if isinstance(data, dict) else []
        items = []
        for item in vod_list:
            items.append(self._make_item(item))
        return {
            "list": items,
            "page": page,
            "pagecount": data.get("totalPages", 99) if isinstance(data, dict) else 99,
            "limit": 20,
            "total": data.get("total", 0) if isinstance(data, dict) else len(items),
        }

    def localProxy(self, param):
        try:
            ptype = param.get("type", "") if isinstance(param, dict) else ""
            if ptype != "bh_img":
                return [404, "text/plain", b"not found"]

            raw_url_b64 = param.get("url", "") if isinstance(param, dict) else ""
            if not raw_url_b64:
                return [400, "text/plain", b"missing url"]

            raw_url_b64 = unquote(raw_url_b64)
            padding = 4 - len(raw_url_b64) % 4
            if padding != 4:
                raw_url_b64 += "=" * padding
            img_url = base64.b64decode(raw_url_b64).decode("utf-8")

            # 加密图片 (.txt) → gzip → XOR → data: URL → 图片bytes
            if img_url.endswith(".txt"):
                headers = {
                    "User-Agent": _UA,
                    "Referer": _HOST + "/",
                    "Accept-Encoding": "identity"
                }
                resp = self.session.get(img_url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    return [resp.status_code, "text/plain", b"image fetch failed"]

                raw = resp.content
                if raw[:2] == b'\x1f\x8b':
                    raw = gzip.decompress(raw)
                size = min(4096, len(raw))
                xor_data = bytes(b ^ _IMG_XOR_KEY for b in raw[:size]) + raw[size:]
                text = xor_data.decode("utf-8", errors="ignore")
                match = re.match(r'^data:([^;]+);base64,(.+)$', text, re.I)
                if not match:
                    return [500, "text/plain", b"decrypt failed"]
                mime, b64 = match.groups()
                img_bytes = base64.b64decode(b64)
                return [200, mime, img_bytes]

            # 普通直链
            headers = {"User-Agent": _UA, "Referer": _HOST + "/"}
            resp = self.session.get(img_url, headers=headers, timeout=30)
            if resp.status_code != 200:
                return [resp.status_code, "text/plain", b""]
            ct = resp.headers.get("Content-Type", "image/jpeg")
            return [200, ct, resp.content]

        except Exception as e:
            return [500, "text/plain", str(e).encode()]
