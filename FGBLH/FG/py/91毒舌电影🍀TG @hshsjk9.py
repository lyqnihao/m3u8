# -*- coding: utf-8 -*-
import sys
import re
from urllib.parse import urljoin, quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

HOST = "https://www.duse0.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
CK = "cdndefend_js_cookie=29C52FC9FE9D47BA0CCD55AFA95A6C2A9AD58B7067707"

CATEGORIES = {
    "1": "电影", "2": "连续剧", "3": "动漫",
    "4": "综艺纪录", "6": "短剧",
}

class Spider(Spider):
    def init(self, extend=""):
        self.headers = {"User-Agent": UA, "Cookie": CK, "Referer": HOST + "/"}

    def homeContent(self, filter=False):
        r = {"class": [], "list": []}
        for k, v in CATEGORIES.items():
            r["class"].append({"type_id": k, "type_name": v})
        return r

    def homeVideoContent(self):
        try:
            r = self.fetch(HOST, headers=self.headers, timeout=15000)
            html = r.text if hasattr(r, 'text') else str(r)
            return {"list": self._items(html)}
        except:
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        pn = 1
        try:
            pn = max(int(str(pg)), 1)
        except:
            pass
        cat = str(tid)
        if cat not in CATEGORIES:
            cat = "1"
        try:
            url = f"{HOST}/show/{cat}-----3-{pn}.html"
            r = self.fetch(url, headers=self.headers, timeout=30000)
            html = r.text if hasattr(r, 'text') else str(r)
            items = self._items(html)
            return {
                "page": pn,
                "pagecount": self._pagecount(html, pn),
                "limit": 18,
                "total": len(items),
                "list": items
            }
        except:
            return {"page": pn, "pagecount": 1, "limit": 18, "total": 0, "list": []}

    def detailContent(self, ids):
        if isinstance(ids, list):
            vid = ids[0] if ids else ""
        else:
            vid = str(ids) if ids else ""
        m = re.search(r'(\d+)', str(vid))
        vid = m.group(1) if m else ""
        if not vid:
            return {"list": []}
        try:
            r = self.fetch(f"{HOST}/detail/{vid}.html", headers=self.headers, timeout=30000)
            h = r.text if hasattr(r, 'text') else str(r)
        except:
            return {"list": []}

        d = {
            "vod_id": vid, "vod_name": "", "vod_pic": "", "vod_year": "",
            "vod_area": "", "vod_class": "", "vod_director": "", "vod_actor": "",
            "vod_content": "", "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""
        }

        tn = re.search(r'<title>(.*?)</title>', h)
        if tn:
            d["vod_name"] = tn.group(1).split("-")[0].replace("免费在线观看", "").replace("高清完整版", "").strip()

        p = re.search(r'<img[^>]+data-original="([^"]+)"[^>]*alt="[^"]+"', h)
        if not p:
            p = re.search(r'<img[^>]+data-original="(https?://[^"]+\.(?:jpg|jpeg|png|webp))"', h)
        if not p:
            p = re.search(r'<img[^>]+alt="[^"]+"[^>]+src="(https?://[^"]+)"', h)
        if p and 'logo_placeholder' not in p.group(1):
            d["vod_pic"] = p.group(1) if p.group(1).startswith('http') else 'https://vres.cyscyy.com' + p.group(1)

        rows = re.findall(r'class="detail-info-row-side">([^<]+)</div>\s*<div class="detail-info-row-main">([\s\S]*?)</div>', h)
        for k, v in rows:
            k = k.strip().rstrip('：:').strip()
            v = re.sub(r'<[^>]+>', '', v).strip()
            if k == '导演' and not d["vod_director"]:
                d["vod_director"] = v[:100]
            elif k == '演员' and not d["vod_actor"]:
                d["vod_actor"] = v[:200]
            elif k == '备注' and not d["vod_remarks"]:
                d["vod_remarks"] = v[:50]
            elif k in ('首映', '年份') and not d["vod_year"]:
                ym2 = re.search(r'(\d{4})', v)
                if ym2:
                    d["vod_year"] = ym2.group(1)

        if not d["vod_year"]:
            tags = re.findall(r'class="detail-tags-item">([^<]+)</a>', h)
            if tags:
                ym2 = re.search(r'(\d{4})', tags[0])
                if ym2:
                    d["vod_year"] = ym2.group(1)
                if not d["vod_area"] and len(tags) > 1:
                    d["vod_area"] = tags[1].strip()

        desc_m = re.search(r'class="[^"]*(?:introduction|vod-desc|detail-desc|info-desc|intro)[^"]*"[^>]*>([\s\S]*?)</(?:p|div)>', h, re.I)
        if not desc_m:
            desc_m = re.search(r'<p[^>]*>\s*([^<]{20,})</p>', h)
        if desc_m:
            d["vod_content"] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', desc_m.group(1))).strip()[:500]

        ym = re.search(r'<a[^>]*>(20\d{2}|19\d{2})</a>', h)
        if ym:
            d["vod_year"] = ym.group(1)

        labels = re.findall(r'class="source-item-label">([^<]+)</span>', h)
        eps_blocks = re.findall(r'<div class="episode-list"[^>]*>([\s\S]*?)</div>', h)
        pairs = []
        for i, block in enumerate(eps_blocks):
            links = re.findall(r'href="(/play/\d+-\d+-\d+\.html)"[^>]*><span>([^<]+)</span>', block)
            if links:
                pairs.append((labels[i] if i < len(labels) else f"线路{i+1}", "#".join([f"{ep.strip()}${urljoin(HOST, href)}" for href, ep in links])))
        pairs = [p for p in pairs if '4K' not in p[0]]
        pairs.sort(key=lambda p: 0 if p[0].startswith('蓝光') else 1)
        if pairs:
            d["vod_play_from"] = "$$$".join(p[0] for p in pairs)
            d["vod_play_url"] = "$$$".join(p[1] for p in pairs)

        return {"list": [d]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            token = ""
            r = self.fetch(f"{HOST}/channel/1.html", headers=self.headers, timeout=15000)
            h0 = r.text if hasattr(r, 'text') else str(r)
            tm = re.search(r'name="t"\s+value="([^"]+)"', h0)
            if not tm:
                tm = re.search(r'/search\?k=[^"\s]+?&amp;t=([^"\s]+)', h0)
            if tm:
                token = tm.group(1)
            url = f"{HOST}/search?k={quote(key)}&t={quote(token, safe='')}"
            r = self.fetch(url, headers=self.headers, timeout=30000)
            html = r.text if hasattr(r, 'text') else str(r)
            items = self._items(html, 1)
            return {"list": items, "page": 1}
        except:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id) if id else str(flag)
        if url.startswith("http") and "/play/" not in url and (".m3u8" in url or ".mp4" in url):
            return {"url": url}
        if url.startswith("http"):
            full_url = url
        else:
            if not url.startswith("/"):
                url = "/" + url
            full_url = urljoin(HOST, url)
        try:
            r = self.fetch(full_url, headers=self.headers, timeout=30000)
            h = r.text if hasattr(r, 'text') else str(r)
        except:
            return {"url": ""}
        ps = re.search(r'playSource\s*=\s*\{[\s\S]*?src:\s*"([^"]+)"', h)
        if ps:
            return {"url": ps.group(1)}
        m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8)', h)
        if m3u8:
            return {"url": m3u8.group(1)}
        mp4 = re.search(r'(https?://[^\s"\'<>]+\.mp4)', h)
        if mp4:
            return {"url": mp4.group(1)}
        return {"url": ""}

    def localProxy(self, param):
        return None

    def _pagecount(self, html, current_page=1):
        pages = re.findall(r'/show/\d+-----3-(\d+)\.html', html)
        max_page = current_page
        for p in pages:
            try:
                n = int(p)
                if n > max_page:
                    max_page = n
            except:
                pass
        return max_page

    def _items(self, html, kind=0):
        items, seen = [], set()

        def _cover(seg):
            covers = re.findall(r'data-original="([^"]+)"', seg) + re.findall(r'<img[^>]+src="(https?://[^"]+)"', seg)
            for c in covers:
                if 'logo_placeholder' not in c:
                    return c if c.startswith('http') else 'https://vres.cyscyy.com' + c
            return ""

        if kind == 1:
            pat = re.finditer(r'<a href="(/detail/(\d+)\.html)" class="search-result-item"([\s\S]*?)</a>', html)
            for m in pat:
                vid = m.group(2)
                if vid in seen:
                    continue
                seg = m.group(3)
                name = re.search(r'alt="([^"]+)"', seg)
                hd = re.search(r'search-result-item-header[^>]*>\s*<div>([^<]+)</div>', seg)
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": (name.group(1) if name else "").strip()[:50],
                    "vod_pic": _cover(seg),
                    "vod_remarks": hd.group(1).strip() if hd else "",
                })
        else:
            pat = re.finditer(r'<a href="(/detail/(\d+)\.html)" class="v-item"([\s\S]*?)</a>', html)
            for m in pat:
                vid = m.group(2)
                if vid in seen:
                    continue
                seg = m.group(3)
                name = re.search(r'class="v-item-title">([^<]+)</div>', seg)
                remark = re.search(r'class="v-item-bottom"[^>]*>([\s\S]*?)</div>', seg)
                rm = re.sub(r'<[^>]+>', '', remark.group(1)).strip() if remark else ""
                seen.add(vid)
                items.append({
                    "vod_id": vid,
                    "vod_name": (name.group(1) if name else "").strip()[:50],
                    "vod_pic": _cover(seg),
                    "vod_remarks": rm[:20],
                })
        return items
