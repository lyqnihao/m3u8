# -*- coding: utf-8 -*-
import base64
import json
import re
import time
from urllib.parse import quote, urljoin

import requests
import urllib3

import sys

sys.path.append('..')
from base.spider import Spider


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Spider(Spider):

    HOST = 'https://rou.video'
    PAGE_SIZE = 26

    def __init__(self):
        self.host = self.HOST
        self.ext = ''
        self.session = requests.Session()
        self.proxies = {}
        self.headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/140.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.classes = [
            {'type_name': '最新视频', 'type_id': '__latest__'},
            {'type_name': '国产AV视频', 'type_id': '國產AV'},
            {'type_name': '麻豆传媒', 'type_id': '麻豆傳媒'},
            {'type_name': '探花视频', 'type_id': '探花'},
            {'type_name': '自拍流出', 'type_id': '自拍流出'},
            {'type_name': 'OnlyFans', 'type_id': 'OnlyFans'},
            {'type_name': '日本视频', 'type_id': '日本'},
        ]
        self.filters = {}
        self._filter_time = 0

    def getName(self):
        return '肉视频'

    def getDependence(self):
        return []

    def setExtendInfo(self, extend):
        self.ext = extend or ''
        return None

    def init(self, extend=''):
        if extend:
            self.ext = extend
        else:
            self.ext = getattr(self, 'ext', '') or ''
        config = self._parse_config(self.ext)
        host = str(config.get('host') or '').strip().rstrip('/')
        if host.startswith(('http://', 'https://')):
            self.host = host
        self._set_proxy(config.get('proxy'))
        return None

    def homeLayout(self):
        return 0

    def manualVideoCheck(self):
        return True

    def isVideoFormat(self, url):
        value = str(url or '').lower()
        return value.startswith('http://127.0.0.1:') or bool(
            re.search(r'\.(?:m3u8|mp4|flv|ts)(?:\?|$)', value)
        )

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def homeContent(self, filter=False):
        result = {'class': self.classes, 'filters': self._filters() if filter else {}}
        try:
            data = self._page('/home')
            result['list'] = [self._video(item) for item in data.get('latestVideos') or []]
        except Exception as error:
            self.log('RouVideo 首页加载失败: %s' % error)
            result['list'] = []
        return result

    def getHomeContent(self, filter=False):
        return self.homeContent(filter)

    def homeVideoContent(self):
        try:
            data = self._page('/home')
            videos = []
            seen = set()
            sections = [
                'latestVideos', 'dailyHotCNAV', 'dailyHotSelfie', 'dailyHot91',
                'dailyOnlyFans', 'dailyJV',
            ]
            for section in sections:
                for item in data.get(section) or []:
                    video = self._video(item)
                    video_id = video.get('vod_id')
                    if video_id and video_id not in seen:
                        seen.add(video_id)
                        videos.append(video)
                    if len(videos) >= 60:
                        return {'list': videos}
            return {'list': videos}
        except Exception as error:
            self.log('RouVideo 首页推荐加载失败: %s' % error)
            return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, self._int(pg, 1))
        ext = extend if isinstance(extend, dict) else {}
        try:
            selected_tag = str(ext.get('tag') or '').strip()
            tag = selected_tag or str(tid or '').strip()
            order = str(ext.get('order') or 'createdAt').strip()
            params = {'page': page}
            if order in ('createdAt', 'viewCount', 'likeCount'):
                params['order'] = order
            path = '/v' if tag == '__latest__' else '/t/' + quote(tag, safe='')
            data = self._page(path, params)
            items = data.get('videos') or []
            videos = [self._video(item) for item in items]
            page_count = max(page, self._int(data.get('totalPage'), page))
            total = max(len(videos), self._int(data.get('totalVideoNum'), len(videos)))
            return {
                'list': videos,
                'page': page,
                'pagecount': page_count,
                'limit': len(videos) or self.PAGE_SIZE,
                'total': total,
            }
        except Exception as error:
            self.log('RouVideo 分类加载失败: %s' % error)
            return {
                'list': [], 'page': page, 'pagecount': page,
                'limit': self.PAGE_SIZE, 'total': 0,
            }

    def detailContent(self, ids):
        video_id = str(ids[0] if ids else '').strip()
        if not video_id:
            return {'list': []}
        try:
            data = self._page('/v/' + quote(video_id, safe=''))
            item = data.get('video') or {}
            if not isinstance(item, dict) or not item:
                return {'list': []}
            title = self._text(item.get('nameZh') or item.get('name')) or '肉视频'
            tags = item.get('tagsZh') or item.get('tags') or []
            if not isinstance(tags, list):
                tags = []
            vod = {
                'vod_id': video_id,
                'vod_name': title,
                'vod_pic': str(item.get('coverImageUrl') or ''),
                'vod_remarks': self._duration(item.get('duration')),
                'vod_year': self._year(item.get('createdAt')),
                'vod_area': ' / '.join(self._text(x) for x in tags[:3] if self._text(x)),
                'vod_actor': self._text(item.get('vid')),
                'vod_content': self._text(item.get('description')) or title,
                'vod_play_from': '肉视频原画',
                'vod_play_url': '播放$' + video_id,
            }
            return {'list': [vod]}
        except Exception as error:
            self.log('RouVideo 详情加载失败: %s' % error)
            return {'list': []}

    def searchContent(self, key, quick, pg='1'):
        page = max(1, self._int(pg, 1))
        keyword = str(key or '').strip()
        if not keyword:
            return {
                'list': [], 'page': page, 'pagecount': page,
                'limit': self.PAGE_SIZE, 'total': 0,
            }
        try:
            data = self._page('/search', {'q': keyword, 'page': page})
            videos = [self._video(item) for item in data.get('videos') or []]
            page_count = max(page, self._int(data.get('totalPage'), page))
            total = max(len(videos), self._int(data.get('totalVideoNum'), len(videos)))
            return {
                'list': videos,
                'page': page,
                'pagecount': page_count,
                'limit': len(videos) or self.PAGE_SIZE,
                'total': total,
            }
        except Exception as error:
            self.log('RouVideo 搜索失败: %s' % error)
            return {
                'list': [], 'page': page, 'pagecount': page,
                'limit': self.PAGE_SIZE, 'total': 0,
            }

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        video_id = str(id or '').strip()
        if not video_id:
            return {'parse': 1, 'playUrl': '', 'url': ''}
        try:
            data = self._page('/v/' + quote(video_id, safe=''))
            media = self._decrypt_media(data.get('ev'))
            media_url = str(media.get('videoUrl') or '').strip()
            if not media_url:
                raise ValueError('详情没有返回播放地址')
            proxy_url = (
                self.getProxyUrl() + '&type=rou_m3u8&url=' + quote(media_url, safe='')
            )
            return {
                'parse': 0,
                'playUrl': '',
                'url': proxy_url,
                'type': 'm3u8',
                'format': 'application/x-mpegURL',
                'contentType': 'application/x-mpegURL',
                'header': {},
            }
        except Exception as error:
            self.log('RouVideo 播放解析失败: %s' % error)
            return {'parse': 1, 'playUrl': '', 'url': self.host + '/v/' + quote(video_id, safe='')}

    def localProxy(self, param):
        if str(param.get('type') or '') != 'rou_m3u8':
            return [404, 'text/plain; charset=utf-8', b'not found']
        media_url = str(param.get('url') or '').strip()
        if not media_url.startswith(('http://', 'https://')):
            return [500, 'text/plain; charset=utf-8', b'invalid url']
        try:
            response = self.session.get(
                media_url,
                headers=self._media_headers(),
                timeout=(10, 30),
                verify=False,
                allow_redirects=True,
            )
            response.raise_for_status()
            content = response.content
            if not content.lstrip().startswith(b'#EXTM3U'):
                return [500, 'text/plain; charset=utf-8', b'invalid hls manifest']
            text = content.decode('utf-8-sig', errors='replace')
            lines = []
            for line in text.splitlines():
                value = line.strip()
                if value and not value.startswith('#'):
                    lines.append(urljoin(response.url, value))
                else:
                    lines.append(line)
            body = ('\n'.join(lines) + '\n').encode('utf-8')
            return [200, 'application/vnd.apple.mpegurl', body, {
                'Content-Type': 'application/vnd.apple.mpegurl',
                'Cache-Control': 'no-cache',
                'Access-Control-Allow-Origin': '*',
            }]
        except Exception as error:
            self.log('RouVideo HLS 代理失败: %s' % error)
            return [500, 'text/plain; charset=utf-8', b'hls proxy failed']

    def _filters(self):
        if self.filters and time.time() - self._filter_time < 1800:
            return self.filters
        sorts = {
            'key': 'order',
            'name': '排序',
            'value': [
                {'n': '最新上传', 'v': 'createdAt'},
                {'n': '最多播放', 'v': 'viewCount'},
                {'n': '最多点赞', 'v': 'likeCount'},
            ],
        }
        filters = {item['type_id']: [sorts] for item in self.classes}
        try:
            data = self._page('/cat')
            groups = {
                '國產AV': data.get('gcAV') or [],
                '麻豆傳媒': data.get('madouAV') or [],
                '探花': data.get('v91') or [],
                'OnlyFans': data.get('onlyfans') or [],
            }
            for type_id, rows in groups.items():
                values = [{'n': '全部', 'v': ''}]
                seen = set()
                for row in rows:
                    tag = self._text(row.get('id')) if isinstance(row, dict) else ''
                    if not tag or tag in seen:
                        continue
                    seen.add(tag)
                    count = self._int(row.get('count'), 0)
                    values.append({'n': '%s(%d)' % (tag, count) if count else tag, 'v': tag})
                filters[type_id] = [
                    {'key': 'tag', 'name': '分类', 'value': values},
                    sorts,
                ]
        except Exception as error:
            self.log('RouVideo 筛选加载失败: %s' % error)
        self.filters = filters
        self._filter_time = time.time()
        return filters

    def _page(self, path, params=None):
        url = self.host.rstrip('/') + '/' + str(path or '').lstrip('/')
        last_error = None
        for attempt in range(2):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=self.headers,
                    timeout=(10, 25),
                    verify=False,
                    allow_redirects=True,
                )
                response.raise_for_status()
                match = re.search(
                    r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
                    response.text,
                    re.I | re.S,
                )
                if not match:
                    raise ValueError('页面缺少 __NEXT_DATA__')
                payload = json.loads(match.group(1))
                props = payload.get('props', {}).get('pageProps', {})
                if not isinstance(props, dict):
                    raise ValueError('pageProps 格式错误')
                if self._int(props.get('statusCode'), 200) >= 400:
                    raise ValueError('网站返回状态 %s' % props.get('statusCode'))
                return props
            except Exception as error:
                last_error = error
                if attempt == 0:
                    time.sleep(0.25)
        raise last_error or RuntimeError('页面请求失败')

    def _decrypt_media(self, ev):
        if not isinstance(ev, dict):
            raise ValueError('详情缺少 ev')
        encoded = str(ev.get('d') or '').strip()
        key = self._int(ev.get('k'), -1)
        if not encoded or key < 0:
            raise ValueError('ev 参数不完整')
        raw = base64.b64decode(encoded)
        decoded = bytes((byte - key) % 256 for byte in raw).decode('utf-8')
        result = json.loads(decoded)
        if not isinstance(result, dict):
            raise ValueError('ev 解密结果格式错误')
        return result

    def _video(self, item):
        if not isinstance(item, dict):
            return {}
        video_id = self._text(item.get('id'))
        title = self._text(item.get('nameZh') or item.get('name')) or video_id
        sources = item.get('sources') or []
        resolutions = []
        for source in sources if isinstance(sources, list) else []:
            if isinstance(source, dict):
                resolution = self._int(source.get('resolution'), 0)
                if resolution > 0:
                    resolutions.append(resolution)
        remarks = []
        if resolutions:
            remarks.append('%dP' % max(resolutions))
        duration = self._duration(item.get('duration'))
        if duration:
            remarks.append(duration)
        return {
            'vod_id': video_id,
            'vod_name': title,
            'vod_pic': str(item.get('coverImageUrl') or ''),
            'vod_remarks': ' · '.join(remarks),
            'style': {'type': 'rect', 'ratio': 1.78},
        }

    def _media_headers(self):
        return {
            'User-Agent': self.headers['User-Agent'],
            'Accept': '*/*',
            'Referer': self.host + '/',
            'Origin': self.host,
        }

    def _parse_config(self, value):
        if isinstance(value, dict):
            return value
        text = str(value or '').strip()
        if not text:
            return {}
        if text.startswith(('http://', 'https://')):
            return {'host': text}
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _set_proxy(self, value):
        proxy = str(value or '').strip()
        self.proxies = {}
        self.session.proxies.clear()
        if not proxy:
            return
        if '://' not in proxy:
            proxy = 'http://' + proxy
        self.proxies = {'http': proxy, 'https': proxy}
        self.session.proxies.update(self.proxies)

    @staticmethod
    def _text(value):
        return re.sub(r'\s+', ' ', str(value or '')).strip()

    @staticmethod
    def _int(value, default=0):
        try:
            return int(float(value))
        except Exception:
            return default

    def _duration(self, value):
        seconds = max(0, self._int(value, 0))
        if not seconds:
            return ''
        hours, remain = divmod(seconds, 3600)
        minutes, secs = divmod(remain, 60)
        if hours:
            return '%d小时%d分' % (hours, minutes)
        if minutes:
            return '%d分%d秒' % (minutes, secs)
        return '%d秒' % secs

    @staticmethod
    def _year(value):
        match = re.match(r'(\d{4})', str(value or ''))
        return match.group(1) if match else ''
