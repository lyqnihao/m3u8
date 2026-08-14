#!/usr/bin/python
# coding=utf-8
import re, json, requests
from urllib.parse import quote
from base.spider import Spider

class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "酷客影院"
        self.host = "https://www.8kvod.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Referer": self.host,
            "Accept-Language": "zh-CN,zh;q=0.9"
        }
        self.cate_map = {"1":"电影","2":"电视剧","3":"动漫","4":"综艺","67":"伦理"}
        self.area_list = ["全部","大陆","香港","台湾","美国","韩国","日本","泰国","英国","法国","德国","印度","俄罗斯","意大利","西班牙","加拿大","澳大利亚","其他"]
        self.year_list = ["全部","2026","2025","2024","2023","2022","2021","2020","2019","2018","2017","2016","2015","2014","2013","2012","2011","2010","2009","2008","2007","2006","2005","2004","2003","2002","2001","2000"]
        self._filters = None

    def fix_url(self, url):
        if not url: return ""
        if url.startswith("//"): return "https:" + url
        if url.startswith("/"): return self.host + url
        return url

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'\s+', ' ', text).strip()

    def getName(self): return self.name

    def _build_filters(self):
        if self._filters: return self._filters
        area_values = [{"n":a,"v":a} for a in self.area_list]
        year_values = [{"n":y,"v":y} for y in self.year_list]
        flt = [
            {"key":"area","name":"地区","value":area_values},
            {"key":"year","name":"年份","value":year_values}
        ]
        self._filters = {tid: flt for tid in self.cate_map}
        return self._filters

    def _parse_list_items(self, html):
        videos = []
        seen = set()
        items = re.findall(r'<div class="stui-vodlist__box">(.*?)</div>\s*</div>\s*</li>', html, re.S)
        for item in items:
            try:
                m = re.search(r'href="/(edu-\d+\.html)"', item)
                if not m: continue
                vid = m.group(1)
                if vid in seen: continue
                seen.add(vid)
                name = re.search(r'title="([^"]+)"', item)
                name = name.group(1) if name else ""
                pic = re.search(r'data-original="([^"]+)"', item)
                pic = self.fix_url(pic.group(1)) if pic else ""
                remark = re.search(r'<span class="pic-text[^"]*">([^<]+)</span>', item)
                remark = remark.group(1) if remark else ""
                videos.append({"vod_id":vid,"vod_name":name,"vod_pic":pic,"vod_remarks":remark})
            except: continue
        return videos, seen

    def _parse_area_year_items(self, html):
        videos = []
        seen = set()
        items = re.findall(r'<li[^>]*>\s*<div class="thumb">(.*?)</div>\s*<div class="detail">(.*?)</div>\s*</li>', html, re.S)
        for thumb, detail in items:
            try:
                m = re.search(r'href="/(edu-\d+\.html)"', thumb)
                if not m: continue
                vid = m.group(1)
                if vid in seen: continue
                seen.add(vid)
                name = re.search(r'title="([^"]+)"', thumb)
                name = name.group(1) if name else ""
                pic = re.search(r'data-original="([^"]+)"', thumb)
                pic = self.fix_url(pic.group(1)) if pic else ""
                remark = re.search(r'<span class="pic-text[^"]*">([^<]+)</span>', thumb)
                remark = remark.group(1) if remark else ""
                videos.append({"vod_id":vid,"vod_name":name,"vod_pic":pic,"vod_remarks":remark})
            except: continue
        return videos, seen

    def homeContent(self, filter):
        classes = [{"type_id":k,"type_name":v} for k,v in self.cate_map.items()]
        rsp = requests.get(self.host, headers=self.header, timeout=10)
        rsp.encoding = 'utf-8'
        videos, _ = self._parse_list_items(rsp.text)
        return {"class":classes,"list":videos,"filters":self._build_filters()}

    def homeVideoContent(self):
        return {"list": self.homeContent(None).get("list", [])}

    def categoryContent(self, tid, pg, filter, extend):
        area = extend.get("area","") if extend else ""
        year = extend.get("year","") if extend else ""
        page = int(pg)
        if area and area != "全部":
            url = f"{self.host}/area.php?searchword={quote(area)}"
            if page > 1: url += f"&page={page}"
            rsp = requests.get(url, headers=self.header, timeout=10)
            rsp.encoding = 'utf-8'
            videos, _ = self._parse_area_year_items(rsp.text)
            return {"list":videos,"page":page,"pagecount":1,"limit":99,"total":len(videos)}
        if year and year != "全部":
            url = f"{self.host}/year.php?searchword={quote(year)}"
            if page > 1: url += f"&page={page}"
            rsp = requests.get(url, headers=self.header, timeout=10)
            rsp.encoding = 'utf-8'
            videos, _ = self._parse_area_year_items(rsp.text)
            return {"list":videos,"page":page,"pagecount":1,"limit":99,"total":len(videos)}
        url = f"{self.host}/list/{tid}.html" if page == 1 else f"{self.host}/list/{tid}-{page}.html"
        rsp = requests.get(url, headers=self.header, timeout=10)
        rsp.encoding = 'utf-8'
        html = rsp.text
        videos, seen = self._parse_list_items(html)
        pagecount = 999
        nums = re.findall(r'(?:href="/list/\d+(?:-\d+)?\.html"[^>]*>|["\']?page["\']?\s*[=:]\s*)(\d+)', html)
        if nums:
            try: pagecount = max([int(x) for x in nums])
            except: pass
        return {"list":videos,"page":page,"pagecount":pagecount,"limit":24,"total":99999}

    def detailContent(self, ids):
        vid = ids[0]
        url = f"{self.host}/{vid}"
        rsp = requests.get(url, headers=self.header, timeout=10)
        rsp.encoding = 'utf-8'
        html = rsp.text
        name = re.search(r'<h1[^>]*>(?:<a[^>]*>)?([^<]+)', html)
        name = self.clean_text(name.group(1)) if name else ""
        pic = re.search(r'(?:data-original|src|poster)="([^"]+)"[^>]*class="[^"]*stui-vodlist__thumb', html)
        if not pic: pic = re.search(r'<img[^>]+src="([^"]+)"[^>]*>', html)
        pic = self.fix_url(pic.group(1)) if pic else ""
        desc = re.search(r'剧情介绍.*?<div[^>]*class="col-pd"[^>]*>(.*?)</div>', html, re.S)
        desc = re.sub(r'<[^>]+>', '', desc.group(1)).strip() if desc else ""
        tabs = re.findall(r'<li id="tab\d+"><a[^>]*>([^<]+)</a></li>', html)
        playlists = re.findall(r'<div class="tab-pane[^"]*"(?: id="down\d+")?[^>]*>(.*?)</div>\s*</div>', html, re.S)
        if not tabs:
            nid = vid.replace("edu-", "").replace(".html", "")
            purl = f"{self.host}/gov-{nid}-0-0.html"
            prsp = requests.get(purl, headers=self.header, timeout=10)
            prsp.encoding = 'utf-8'
            phtml = prsp.text
            tabs = re.findall(r'<li id="tab\d+"><a[^>]*>([^<]+)</a></li>', phtml)
            playlists = re.findall(r'<div class="tab-pane fade in clearfix" id="down\d+">(.*?)</div>', phtml, re.S)
        from_list, url_list = [], []
        for i, tab in enumerate(tabs):
            from_list.append(tab.strip())
            pl = playlists[i] if i < len(playlists) else ""
            eps = re.findall(r'<a href="/(gov-[\d\-]+\.html)"[^>]*>([^<]+)</a>', pl)
            ep_strs = [f"{self.clean_text(ep[1])}${ep[0]}" for ep in eps]
            url_list.append("#".join(ep_strs))
        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": "$$$".join(from_list),
            "vod_play_url": "$$$".join(url_list)
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg):
        url = f"{self.host}/search.php"
        rsp = requests.post(url, data={"searchword": key}, headers=self.header, timeout=10)
        rsp.encoding = 'utf-8'
        html = rsp.text
        videos, _ = self._parse_list_items(html)
        return {"list":videos,"page":int(pg),"pagecount":1,"limit":24,"total":len(videos)}

    def playerContent(self, flag, id, vipFlags):
        if id and ('.m3u8' in id or '.mp4' in id):
            return {"parse": 0, "url": id, "header": self.header}
        url = f"{self.host}/{id}"
        rsp = requests.get(url, headers=self.header, timeout=10)
        rsp.encoding = 'utf-8'
        html = rsp.text
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            purl = iframe.group(1)
            if purl.startswith("//"): purl = "https:" + purl
            try:
                irsp = requests.get(purl, headers={"User-Agent": self.header["User-Agent"], "Referer": url}, timeout=10)
                irsp.encoding = 'utf-8'
                ihtml = irsp.text
                m3u8 = ""
                for pat in [
                    r'id\s*:\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'(?:var|const|let)\s+\w+\s*=\s*["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']',
                    r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
                ]:
                    m = re.search(pat, ihtml, re.I)
                    if m:
                        m3u8 = m.group(1)
                        break
                if m3u8:
                    if m3u8.startswith("//"): m3u8 = "https:" + m3u8
                    return {"parse": 0, "url": m3u8, "header": {"User-Agent": self.header["User-Agent"]}}
            except: pass
            return {"parse": 1, "url": purl, "header": {"User-Agent": self.header["User-Agent"], "Referer": url}}
        for pat in [r'["\']([^"\']+\.m3u8[^"\']*)["\']', r'["\']([^"\']+\.mp4[^"\']*)["\']']:
            m = re.search(pat, html)
            if m: return {"parse": 0, "url": m.group(1), "header": self.header}
        return {"parse": 1, "url": url, "header": self.header}

    def localProxy(self, param):
        return [200, "video/MP2T", b"", {}]
