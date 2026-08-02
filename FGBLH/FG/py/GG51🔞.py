# -*- coding: utf-8 -*-
import sys
import re
import base64
import requests
from urllib.parse import quote, unquote
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://gzbk.didi51-tedb0997.cc"
        self.hosts = [self.host, "https://www.gg51.com", "https://gg51.com"]
        self.img_host = "https://oytsuig.kwvqaj.cn"
        self.valid_hosts = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; SM-G9750 Build/SP1A.210812.016; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/89.0.4389.72 MQQBrowser/6.2 TBS/046279 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Origin": self.host,
            "Accept": "application/json,text/plain,*/*"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def getName(self):
        return "GG51"

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(m3u8|mp4|flv|avi|mkv|mov|ts)(\?|$)", url or "", re.I))

    def manualVideoCheck(self):
        return False

    def homeContent(self, filter):
        classes = [
            {"type_id": "7", "type_name": "大厂原创"},
            {"type_id": "8", "type_name": "重磅泄密"},
            {"type_id": "5", "type_name": "自拍偷拍"},
            {"type_id": "6", "type_name": "绿帽偷情"},
            {"type_id": "11", "type_name": "中文字幕"},
            {"type_id": "14", "type_name": "强奸迷奸"},
            {"type_id": "12", "type_name": "高清无码"},
            {"type_id": "13", "type_name": "熟女人妻"},
            {"type_id": "15", "type_name": "剧情大片"},
            {"type_id": "16", "type_name": "黑白配"},
            {"type_id": "18", "type_name": "美颜巨乳"},
            {"type_id": "48", "type_name": "欧美少妇"},
            {"type_id": "19", "type_name": "动漫3D"},
            {"type_id": "21", "type_name": "网红主播"},
            {"type_id": "22", "type_name": "AI换脸"}
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        data = self.apiList(str(tid), str(pg))
        if str(tid) == "21" and not data:
            data = self.mergeCategory(["23", "24", "25", "27"], pg)
        return {
            "page": int(pg),
            "pagecount": 999 if data else int(pg),
            "limit": 10,
            "total": 999999 if data else 0,
            "list": data
        }

    def detailContent(self, ids):
        sid = ids[0] if ids else ""
        ps = sid.split("@@@")
        vid = ps[0] if len(ps) > 0 else sid
        play = ps[1] if len(ps) > 1 else ""
        name = unquote(ps[2]) if len(ps) > 2 else vid
        pic = unquote(ps[3]) if len(ps) > 3 else ""
        if play:
            return {"list": [{
                "vod_id": sid,
                "vod_name": name,
                "vod_pic": pic,
                "type_name": "",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_content": name,
                "vod_play_from": "GG51",
                "vod_play_url": name + "$" + play
            }]}
        html = self.get(self.host + "/view/" + vid)
        title = self.match(html, r"<title>(.*?)</title>")
        title = self.clean(title).split("-")[0].strip() if title else vid
        pic = self.match(html, r'(?:poster|data-original|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)')
        pic = self.fix(pic)
        play = self.extractPlay(html)
        return {"list": [{
            "vod_id": sid,
            "vod_name": title,
            "vod_pic": pic,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "",
            "vod_actor": "",
            "vod_director": "",
            "vod_content": title,
            "vod_play_from": "GG51",
            "vod_play_url": title + "$" + (play or sid)
        }]}

    def searchContent(self, key, quick, pg="1"):
        wd = quote(key)
        urls = [
            self.host + "/search/" + wd,
            self.host + "/search/" + wd + "/" + str(pg),
            self.host + "/search/" + wd + "/page/" + str(pg),
            self.host + "/search?keyword=" + wd + "&page=" + str(pg),
            self.host + "/search/?keyword=" + wd + "&page=" + str(pg)
        ]
        for url in urls:
            html = self.get(url)
            data = self.parseList(html)
            if data:
                return {"list": data}
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        sid = id or ""
        ps = sid.split("@@@")
        url = ps[1] if len(ps) > 1 else sid
        if self.isVideoFormat(url):
            return {"parse": 0, "url": url, "header": self.headers}
        html = self.get(self.host + "/view/" + ps[0])
        play = self.extractPlay(html)
        if play:
            return {"parse": 0, "url": play, "header": self.headers}
        return {"parse": 1, "url": url, "header": self.headers}

    def localProxy(self, param):
        return [200, "video/MP2T", {}, ""]

    def destroy(self):
        return "success"

    def apiList(self, tid, pg):
        try:
            real_pg = str(int(pg) + 1)
        except Exception:
            real_pg = "2"
        hosts = self.fastHosts()
        for h in hosts:
            data = self.postList(h, tid, real_pg)
            if data:
                return data
        for h in self.findHosts():
            if h in hosts:
                continue
            data = self.postList(h, tid, real_pg)
            if data:
                return data
        return []

    def fastHosts(self):
        res = []
        for h in [self.host] + self.valid_hosts:
            h = str(h).rstrip("/")
            if h and h not in res:
                res.append(h)
        return res

    def postList(self, h, tid, real_pg):
        try:
            h = h.rstrip("/")
            url = h + "/data/getlistbyid"
            hs = dict(self.headers)
            hs["Referer"] = h + "/category/" + str(tid)
            hs["Origin"] = h
            hs["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
            r = self.session.post(url, headers=hs, data="id=" + str(tid) + "&page=" + str(real_pg), timeout=5, verify=False)
            js = r.json()
            arr = js.get("listData") or js.get("data") or js.get("list") or []
            if not arr:
                return []
            self.host = h
            self.headers["Referer"] = self.host + "/"
            self.headers["Origin"] = self.host
            if self.host in self.valid_hosts:
                self.valid_hosts.remove(self.host)
            self.valid_hosts.insert(0, self.host)
            return self.parseApiList(arr)
        except Exception:
            return []

    def mergeCategory(self, tids, pg):
        res = []
        for tid in tids:
            arr = self.apiList(str(tid), str(pg))
            for item in arr:
                res.append(item)
                if len(res) >= 10:
                    return self.uniqueList(res)
        return self.uniqueList(res)

    def uniqueList(self, arr):
        res = []
        seen = set()
        for item in arr or []:
            vid = item.get("vod_id", "")
            key = vid.split("@@@")[0] if "@@@" in vid else vid
            if not key or key in seen:
                continue
            seen.add(key)
            res.append(item)
        return res

    def parseApiList(self, arr):
        res = []
        for item in arr or []:
            vid = str(item.get("view_key") or item.get("id") or item.get("vod_id") or "")
            name = self.clean(str(item.get("title") or item.get("name") or item.get("vod_name") or ""))
            pic = self.fix(str(item.get("poster") or item.get("pic") or item.get("vod_pic") or ""))
            play = str(item.get("play_url") or item.get("url") or item.get("vod_play_url") or "")
            remark = str(item.get("duration") or item.get("vod_remarks") or item.get("display_heat") or item.get("hits") or "")
            if not vid and play:
                vid = play
            if not vid or not name:
                continue
            sid = vid + "@@@" + play + "@@@" + quote(name) + "@@@" + quote(pic)
            res.append({
                "vod_id": sid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": remark
            })
        return res

    def findHosts(self):
        if self.valid_hosts:
            return self.valid_hosts
        res = []
        base = [self.host] + [h for h in self.hosts if h != self.host]
        for h in base:
            try:
                h = h.rstrip("/")
                url = h + "/data/domains"
                r = self.session.get(url, headers=self.headers, timeout=4, verify=False)
                js = r.json()
                ds = js.get("landingdomains") or js.get("domains") or []
                for x in ds:
                    x = str(x).rstrip("/")
                    if x and x not in res:
                        res.append(x)
                if res:
                    break
            except Exception:
                pass
        for h in base:
            h = h.rstrip("/")
            if h not in res:
                res.append(h)
        self.valid_hosts = res
        return res

    def get(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=8, verify=False)
            html = r.text
            if "/_guard/auto.js" in html or len(html.strip()) < 80:
                ck = r.cookies.get("guard") or self.session.cookies.get("guard")
                if ck:
                    self.session.cookies.set("guardret", self.guardCookie(ck))
                    r = self.session.get(url, headers=self.headers, timeout=8, verify=False)
                    html = r.text
            return self.decodeShell(html)
        except Exception:
            return ""

    def guardCookie(self, guard):
        try:
            key = guard[:8]
            tail = re.sub(r"\D", "", guard[12:])
            val = str(int(tail) * 2 + 16)
            return base64.b64encode(self.rc4(val, key)).decode()
        except Exception:
            return ""

    def rc4(self, data, key):
        s = list(range(256))
        j = 0
        out = []
        key = key.encode()
        data = data.encode()
        for i in range(256):
            j = (j + s[i] + key[i % len(key)]) % 256
            s[i], s[j] = s[j], s[i]
        i = j = 0
        for c in data:
            i = (i + 1) % 256
            j = (j + s[i]) % 256
            s[i], s[j] = s[j], s[i]
            out.append(c ^ s[(s[i] + s[j]) % 256])
        return bytes(out)

    def decodeShell(self, html):
        old = ""
        cur = html or ""
        for i in range(3):
            if cur == old:
                break
            old = cur
            cur = self.decodeShellOnce(cur)
        return cur

    def decodeShellOnce(self, html):
        if not html:
            return ""
        for p in [
            r"atob\([\"']([A-Za-z0-9+/=]+)[\"']\)",
            r"window\.atob\([\"']([A-Za-z0-9+/=]+)[\"']\)",
            r"Base64\.decode\([\"']([A-Za-z0-9+/=]+)[\"']\)"
        ]:
            m = re.search(p, html)
            if m:
                s = self.b64(m.group(1))
                if len(s) > 100:
                    return s
        m = re.search(r"Uint8Array\(\s*\[([0-9,\s]+)\]", html)
        if m:
            try:
                s = "".join([chr(int(x.strip())) for x in m.group(1).split(",") if x.strip()])
                if len(s) > 100:
                    return s
            except Exception:
                pass
        m = re.search(r"['\"]((?:%[0-9A-Fa-f]{2}){20,})['\"]", html)
        if m:
            s = self.decodeUri(m.group(1))
            if len(s) > 100:
                return s
        m = re.search(r"['\"]([0-9a-fA-F]{80,})['\"]", html)
        if m:
            s = self.decodeHex(m.group(1))
            if len(s) > 100:
                return s
        return html

    def b64(self, s):
        try:
            return base64.b64decode(s + "=" * (-len(s) % 4)).decode("utf-8", "ignore")
        except Exception:
            return ""

    def decodeHex(self, s):
        try:
            return bytes.fromhex(s).decode("utf-8", "ignore")
        except Exception:
            return ""

    def decodeUri(self, s):
        try:
            return unquote(s)
        except Exception:
            return ""

    def extractPlay(self, html):
        if not html:
            return ""
        ps = [
            r'initPlayer\([\"\']([^\"\']+)[\"\']',
            r'["\']url["\']\s*:\s*["\']([^"\']+)["\']',
            r'["\']play_url["\']\s*:\s*["\']([^"\']+)["\']',
            r'(https?://[^"\']+\.(?:m3u8|mp4)(?:\?[^"\']*)?)'
        ]
        for p in ps:
            m = re.search(p, html, re.I)
            if m:
                u = m.group(1).replace("\\/", "/")
                if self.isVideoFormat(u):
                    return u
        return ""

    def parseList(self, html):
        res = []
        if not html:
            return res
        cards = re.findall(r'<a[^>]+href=["\']([^"\']*/view/([^"\']+))["\'][\s\S]{0,800}?</a>', html, re.I)
        for href, vid in cards:
            block = self.match(html, r'<a[^>]+href=["\'][^"\']*/view/' + re.escape(vid) + r'["\'][\s\S]{0,800}?</a>')
            name = self.match(block, r'alt=["\']([^"\']+)') or self.match(block, r'title=["\']([^"\']+)') or self.clean(re.sub(r"<[^>]+>", " ", block))
            pic = self.match(block, r'(?:data-original|data-src|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)')
            remark = self.match(block, r'<span[^>]*>(.*?)</span>')
            if vid and name:
                res.append({
                    "vod_id": vid,
                    "vod_name": self.clean(name),
                    "vod_pic": self.fix(pic),
                    "vod_remarks": self.clean(remark)
                })
        return self.uniqueList(res)

    def match(self, text, pat):
        m = re.search(pat, text or "", re.I)
        return m.group(1) if m else ""

    def clean(self, text):
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def fix(self, url):
        url = (url or "").strip().replace("\\/", "/")
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.img_host.rstrip("/") + url
        return self.img_host.rstrip("/") + "/" + url