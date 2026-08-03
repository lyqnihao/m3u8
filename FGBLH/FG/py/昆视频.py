#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《遮天》TVBox 爬虫 · 轮海秘境·彼岸境
=====================================
目标站点: https://www.kunsp2.shop
修炼境界: 轮海大圆满（轻量直取，POST搜索，播放页直取）
功法特征: 传统多页站点，无加密，正则直取
作者: 九秘大师
"""

import sys
import re
import json
import time
import random
import requests
from urllib import parse

sys.path.append("..")
from base.spider import Spider


class YuanTianShu:
    """源天书——一切功法之根基"""

    session = requests.Session()
    siteUrl = "https://www.kunsp2.shop"

    ua_pool = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def fetch(self, url, headers=None, timeout=10):
        """定龙脉——发起 HTTP 请求"""
        h = {
            "User-Agent": self.ua_pool[int(time.time()) % len(self.ua_pool)],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.siteUrl,
        }
        if headers:
            h.update(headers)
        try:
            resp = self.session.get(url, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 定龙脉失败: {e}")
            return ""

    def post(self, url, data=None, headers=None, timeout=10):
        """寻神源——POST 请求"""
        h = {
            "User-Agent": self.ua_pool[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.siteUrl,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        if headers:
            h.update(headers)
        try:
            resp = self.session.post(url, data=data, headers=h, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[源天书] 寻神源失败: {e}")
            return ""

    def _full_url(self, path):
        """架设神桥——补全相对路径为绝对路径"""
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return parse.urljoin(self.siteUrl, path)


class Spider(YuanTianShu):
    """
    【轮海秘境 · 彼岸境】—— 大圆满

    此境修士已掌握轻量直取流的全部奥义：
    - 能处理分类分页（type/id/20.html / type/id/20/page/2.html）
    - 能提取播放页直链（play/id/xxx/sid/1/nid/1.html）
    - 支持 POST 搜索（wd 参数）
    - 随机 UA 变化（兵字秘·基础）
    """

    # ═══════════════════════════════════════════════════
    # 一、首页分类
    # ═══════════════════════════════════════════════════
    def homeContent(self, filter):
        """彼岸境修士看首页——分类+推荐视频"""

        classes = [
            {"type_id": "20", "type_name": "🇨🇳 国产精品"},
            {"type_id": "21", "type_name": "🎥 主播秀色"},
            {"type_id": "22", "type_name": "🇯🇵 日本无码"},
            {"type_id": "23", "type_name": "🇨🇳 中文字幕"},
            {"type_id": "24", "type_name": "🔞 强奸乱伦"},
            {"type_id": "25", "type_name": "🇺🇸 欧美情色"},
            {"type_id": "26", "type_name": "🎨 卡通动漫"},
        ]

        html = self.fetch(self.siteUrl)
        videos = self._parse_video_list(html)

        return {
            "class": classes,
            "list": videos,
        }

    # ═══════════════════════════════════════════════════
    # 二、分类/列表页
    # ═══════════════════════════════════════════════════
    def categoryContent(self, tid, pg, filter, extend):
        """彼岸境修士翻列表——分页直取"""

        if int(pg) <= 1:
            url = self._full_url(f"/index.php/vod/type/id/{tid}.html")
        else:
            url = self._full_url(f"/index.php/vod/type/id/{tid}/page/{pg}.html")

        html = self.fetch(url)
        videos = self._parse_video_list(html)
        pagecount = self._parse_pagecount(html)

        return {
            "list": videos,
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 24,
            "total": pagecount * 24,
        }

    # ═══════════════════════════════════════════════════
    # 三、详情页（此站播放页即详情页）
    # ═══════════════════════════════════════════════════
    def detailContent(self, ids):
        """彼岸境修士看详情——提取播放地址"""
        vid = ids[0]
        url = self._full_url(vid) if not vid.startswith("http") else vid
        html = self.fetch(url)

        if not html:
            return {"list": []}

        # 提取标题
        title_match = re.search(r'<title>([^<]+)</title>', html)
        title = title_match.group(1).strip() if title_match else "Unknown"
        title = re.sub(r' - 昆视频$', '', title)

        # 提取封面图
        thumb_match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html)
        thumb = thumb_match.group(1) if thumb_match else ""
        thumb = self._full_url(thumb)

        # 提取描述
        desc_match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', html)
        desc = desc_match.group(1) if desc_match else ""

        # 尝试提取 iframe 播放器
        iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe_match:
            play_url = self._full_url(iframe_match.group(1))
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": thumb,
                    "vod_remarks": "iframe",
                    "vod_content": desc,
                    "vod_play_from": "昆视频",
                    "vod_play_url": f"第1集${play_url}",
                }]
            }

        # 尝试提取直接视频链接
        video_match = re.search(r'<video[^>]+src="([^"]+m3u8)"', html)
        if not video_match:
            video_match = re.search(r'<source[^>]+src="([^"]+mp4)"', html)
        if not video_match:
            video_match = re.search(r'var\s+video_url\s*=\s*["\']([^"\']+)["\']', html)
        if not video_match:
            video_match = re.search(r'"url"\s*:\s*"([^"]+m3u8)"', html)
        if not video_match:
            video_match = re.search(r'"url"\s*:\s*"([^"]+mp4)"', html)

        if video_match:
            play_url = self._full_url(video_match.group(1))
            return {
                "list": [{
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": thumb,
                    "vod_remarks": "直链",
                    "vod_content": desc,
                    "vod_play_from": "昆视频",
                    "vod_play_url": f"第1集${play_url}",
                }]
            }

        # 兜底：返回播放页 URL，让 TVBox 嗅探
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": thumb,
                "vod_remarks": "嗅探",
                "vod_content": desc,
                "vod_play_from": "昆视频",
                "vod_play_url": f"第1集${url}",
            }]
        }

    # ═══════════════════════════════════════════════════
    # 四、播放页
    # ═══════════════════════════════════════════════════
    def playerContent(self, flag, id, vipFlags):
        """彼岸境修士播放——直链/iframe 分发"""

        if any(x in id for x in ["iframe", "embed", "player"]):
            return {"parse": 1, "url": id, "header": ""}

        if any(id.endswith(ext) for ext in [".m3u8", ".mp4", ".flv", ".mkv"]):
            return {
                "parse": 0,
                "url": id,
                "header": f"Referer={self.siteUrl}&User-Agent={self.ua_pool[0]}",
            }

        return {"parse": 1, "url": id, "header": ""}

    # ═══════════════════════════════════════════════════
    # 五、搜索（POST 请求）
    # ═══════════════════════════════════════════════════
    def searchContent(self, key, quick, pg="1"):
        """彼岸境修士搜索——POST 表单提交"""

        url = self._full_url("/index.php/vod/search.html")
        data = {"wd": key}

        html = self.post(url, data=data)
        videos = self._parse_video_list(html)

        return {
            "list": videos,
            "page": int(pg),
        }

    # ═══════════════════════════════════════════════════
    # 六、本地代理
    # ═══════════════════════════════════════════════════
    def localProxy(self, param):
        """本地代理——预留接口"""
        return [404, "text/plain", "Not Found"]

    # ═══════════════════════════════════════════════════
    # 辅助功法 · 视频列表解析
    # ═══════════════════════════════════════════════════
    def _parse_video_list(self, html):
        """解析视频列表——彼岸境核心瞳术"""
        videos = []
        if not html:
            return videos

        pattern = re.compile(
            r'<div class="item">\s*<a[^>]+href="([^"]+)" title="([^"]+)"[^>]*>.*?'
            r'<img class="thumb" src="([^"]+)".*?'
            r'<strong class="title">([^<]+)</strong>.*?'
            r'<div class="duration">([^<]+)</div>.*?'
            r'<div class="rating[^"]*">([^<]+)</div>',
            re.S
        )

        for match in pattern.finditer(html):
            href, title, pic, title_div, duration, rating = match.groups()

            # 补全图片路径
            pic = self._full_url(pic)

            # 备注：日期 | 热度
            remarks = f"{duration.strip()} | 🔥{rating.strip()}"

            videos.append({
                "vod_id": href,
                "vod_name": title.strip(),
                "vod_pic": pic,
                "vod_remarks": remarks,
            })

        return videos

    # ═══════════════════════════════════════════════════
    # 辅助功法 · 分页解析
    # ═══════════════════════════════════════════════════
    def _parse_pagecount(self, html):
        """解析总页数——推演天机"""
        if not html:
            return 999

        # 从所有页码链接取最大值
        pages = re.findall(r'href="[^"]*page/(\d+)[^"]*"', html)
        if pages:
            return max(int(p) for p in pages)

        return 999


# ═══════════════════════════════════════════════════
# TVBox 入口
# ═══════════════════════════════════════════════════
"""
【使用说明】
1. 将本文件放入 TVBox 的 py 插件目录
2. 配置 json 中填入站点信息
3. 此源为轮海大圆满境，适合无加密、无复杂反爬的直取站点

【站点特征】
- 域名: https://www.kunsp2.shop
- 框架: 传统 PHP 多页站点（疑似苹果CMS）
- 分类: 国产精品/主播秀色/日本无码/中文字幕/强奸乱伦/欧美情色/卡通动漫
- 播放: 单集单视频（play/id/xxx/sid/1/nid/1.html）
- 搜索: POST 表单（wd 参数）
- 反爬: 无（轮海境可破）

【遮天名言】
"我为天帝，当抓尽世间一切经典！" —— 彼岸境·大圆满
"""
