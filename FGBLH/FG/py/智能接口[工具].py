# -*- coding: utf-8 -*-
"""
TVBox 本地 Py/Js 爬虫聚合源（精简版）
========================================
仅保留扫描与配置生成功能。
包含：子文件夹后缀、增量合并、锁定站点、分页浏览。
"""
import os
import json
import base64
import hashlib
import time
from base.spider import Spider


class Spider(Spider):
    # ==========================================================================
    # 📂 【配置区】
    # ==========================================================================
    PY_DIR    = "/storage/emulated/0/peekpro/py"
    JS_DIR    = "/storage/emulated/0/peekpro/js"
    JAR_DIR   = "/storage/emulated/0/peekpro/jar"
    SAVE_PATH = "/storage/emulated/0/peekpro/智能接口.json"
    LOGO_PATH = "/storage/emulated/0/peekpro/jar/头像.gif"

    _LOCKED_SITES = [

    ]
    _LOCKED_KEYS = {""}

    GENERATED_KEY_PREFIX = "local_auto_"
    PAGE_SIZE = 60
    # ==========================================================================

    def __init__(self):
        super().__init__()
        self.inited = False

        self.cache = {
            "categories": [],
            "file_index": {},
            "sources": [],
            "source_index": {},
            "type_counts": {},
        }

        self.status = {
            "scan_time": "-",
            "included": 0,
            "manual_sites": 0,
            "generated_sites": 0,
            "added": 0,
            "removed": 0,
            "unchanged": 0,
            "write_state": "尚未扫描",
            "written": False,
        }

    def getName(self):
        return "本地Py/Js聚合源（精简版）"

    def init(self, extend):
        if self.inited:
            return
        self._scan_all()
        self._save_config_json()
        self.inited = True

    # ==========================================================================
    # 🔍 【扫描核心】手动递归
    # ==========================================================================
    def _scan_dir(self, base_dir, ext_list):
        results = []
        if not base_dir:
            return results
        if not os.path.exists(base_dir):
            try:
                os.makedirs(base_dir, exist_ok=True)
            except Exception:
                return results
        if not os.path.isdir(base_dir):
            return results
        try:
            entries = os.listdir(base_dir)
        except Exception:
            return results
        for entry in sorted(entries):
            full_path = os.path.join(base_dir, entry)
            if entry.startswith("."):
                continue
            if os.path.isdir(full_path):
                results.extend(self._scan_dir(full_path, ext_list))
            elif os.path.isfile(full_path):
                lower_name = entry.lower()
                for ext in ext_list:
                    if lower_name.endswith(ext):
                        name_no_ext = entry[: -len(ext)]
                        results.append((full_path, name_no_ext, ext))
                        break
        return results

    def _get_sub_sfx(self, full_path, base_dir):
        try:
            rel = os.path.relpath(full_path, base_dir)
            rel_parts = rel.split(os.sep)
            subfolder = rel_parts[0] if len(rel_parts) > 1 else ""
        except (ValueError, IndexError):
            subfolder = ""
        if not subfolder:
            return ""
        if subfolder.startswith("[") and subfolder.endswith("]"):
            return subfolder
        return f"[{subfolder}]"

    def _scan_all(self):
        sources = []
        self_path = os.path.abspath(__file__) if hasattr(__file__, '__file__') else ""

        scan_specs = [
            (self.PY_DIR, [".py"], "PY", 0),
            (self.JS_DIR, [".js"], "JS", 1),
        ]

        for dir_path, ext_list, type_tag, order in scan_specs:
            files = self._scan_dir(dir_path, ext_list)
            for full_path, name, ext in files:
                if self_path and os.path.abspath(full_path) == self_path:
                    continue

                identity = type_tag + "|" + full_path
                tid = base64.b64encode(identity.encode("utf-8")).decode("utf-8")
                sub_sfx = self._get_sub_sfx(full_path, dir_path)
                display_name = f"【{type_tag}】{name}{sub_sfx}"

                source = {
                    "type_id": tid,
                    "type_name": display_name,
                    "identity": identity,
                    "_path": full_path,
                    "_ext": ext.lstrip("."),
                    "_dir": dir_path,
                    "_type_tag": type_tag,
                    "_sk": (order, name),
                    "_sub_sfx": sub_sfx,
                }
                sources.append(source)

                self.cache["file_index"][tid] = {
                    "path": full_path,
                    "ext": source["_ext"],
                    "dir": dir_path,
                    "type_tag": type_tag,
                    "sub_sfx": sub_sfx,
                }

        sources.sort(key=lambda x: x["_sk"])

        self.cache["sources"] = sources
        self.cache["source_index"] = {}
        self.cache["type_counts"] = {}
        for s in sources:
            self.cache["source_index"][s["type_id"]] = s
            tag = s["_type_tag"]
            self.cache["type_counts"][tag] = self.cache["type_counts"].get(tag, 0) + 1

        self.cache["categories"] = [
            {"type_id": s["type_id"], "type_name": s["type_name"]}
            for s in sources
        ]
        self.status["included"] = len(sources)

    # ==========================================================================
    # 【增量合并配置生成】
    # ==========================================================================
    def _build_api(self, file_info):
        f_path = file_info["path"]
        base_dir = file_info["dir"]
        try:
            rel = os.path.relpath(f_path, base_dir)
        except ValueError:
            rel = os.path.basename(f_path)
        dir_name = os.path.basename(base_dir)
        return "./" + dir_name + "/" + rel

    def _build_spider_value(self):
        jar_dir = self.JAR_DIR
        if not jar_dir or not os.path.isdir(jar_dir):
            return ""
        jar_files = []
        save_dir = os.path.dirname(self.SAVE_PATH)
        try:
            entries = sorted(os.listdir(jar_dir))
        except Exception:
            return ""
        for entry in entries:
            if entry.startswith("."):
                continue
            if entry.lower().endswith(".jar") and os.path.isfile(os.path.join(jar_dir, entry)):
                abs_jar = os.path.join(jar_dir, entry)
                try:
                    rel = os.path.relpath(abs_jar, save_dir)
                except ValueError:
                    rel = "jar/" + entry
                rel = "./" + rel.replace("\\", "/")
                if not rel.startswith("./"):
                    rel = "./" + rel.lstrip("./")
                jar_files.append(rel)
        return ";".join(jar_files)

    def _get_locked_api_set(self):
        locked = set()
        for site in self._LOCKED_SITES:
            for field in ("api", "homePage", "ext"):
                val = str(site.get(field, "")).strip()
                if val.startswith("./"):
                    locked.add(val)
        return locked

    def _is_generated_key(self, key):
        return str(key).startswith(self.GENERATED_KEY_PREFIX)

    def _load_existing_config(self):
        if not os.path.isfile(self.SAVE_PATH):
            return None
        try:
            with open(self.SAVE_PATH, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _generate_auto_sites(self):
        locked_paths = self._get_locked_api_set()
        sites = []
        for source in self.cache["sources"]:
            file_info = self.cache["file_index"].get(source["type_id"])
            if not file_info:
                continue
            f_path = file_info["path"]
            type_tag = file_info.get("type_tag", "PY")
            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]

            api_path = self._build_api(file_info)
            sub_sfx = file_info.get("sub_sfx", "")

            if api_path in locked_paths:
                continue

            if not os.path.isfile(f_path):
                continue

            key = self.GENERATED_KEY_PREFIX + type_tag.lower() + "_" + hashlib.sha256(
                (type_tag + "|" + f_path).encode("utf-8")
            ).hexdigest()[:14]

            sites.append({
                "key": key,
                "name": f"{f_base}{sub_sfx}",
                "type": 3,
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1,
                "api": api_path,
            })
        return sites

    def _save_config_json(self):
        self.status["scan_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

        new_auto_sites = self._generate_auto_sites()

        existing = self._load_existing_config()
        manual_sites = []
        old_auto_keys = set()
        if existing and isinstance(existing.get("sites"), list):
            for site in existing["sites"]:
                if not isinstance(site, dict):
                    continue
                k = site.get("key", "")
                if k in self._LOCKED_KEYS:
                    continue
                if self._is_generated_key(k):
                    old_auto_keys.add(k)
                else:
                    manual_sites.append(site)

        new_auto_keys = {s.get("key") for s in new_auto_sites}
        self.status["added"] = len(new_auto_keys - old_auto_keys)
        self.status["removed"] = len(old_auto_keys - new_auto_keys)
        self.status["unchanged"] = len(old_auto_keys & new_auto_keys)
        self.status["manual_sites"] = len(manual_sites)
        self.status["generated_sites"] = len(new_auto_sites)

        config = {
            "logo": self.LOGO_PATH,
            "spider": self._build_spider_value(),
            "sites": list(self._LOCKED_SITES) + manual_sites + new_auto_sites,
        }

        new_content = json.dumps(config, ensure_ascii=False, indent=2)
        if existing:
            old_content = json.dumps(existing, ensure_ascii=False, indent=2)
            if new_content == old_content:
                self.status["write_state"] = "配置未变化"
                self.status["written"] = True
                return

        save_dir = os.path.dirname(self.SAVE_PATH)
        if save_dir and not os.path.exists(save_dir):
            try:
                os.makedirs(save_dir, exist_ok=True)
            except Exception:
                pass

        try:
            tmp = self.SAVE_PATH + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fp:
                fp.write(new_content)
                fp.flush()
                os.fsync(fp.fileno())
            os.replace(tmp, self.SAVE_PATH)
            self.status["write_state"] = "已写入配置"
            self.status["written"] = True
        except Exception as e:
            self.status["write_state"] = "写入失败: {}".format(e)
            self.status["written"] = False

    # ==========================================================================
    # 🔧 辅助方法
    # ==========================================================================
    def _get_file_info(self, tid):
        return self.cache["file_index"].get(tid)

    def _count_str(self):
        c = self.cache["type_counts"]
        return f"共扫描到 {c.get('PY', 0)} 个PY文件, {c.get('JS', 0)} 个JS文件"

    def _count_jar_str(self):
        if not os.path.isdir(self.JAR_DIR):
            return "jar 目录不存在"
        count = sum(
            1 for f in os.listdir(self.JAR_DIR)
            if f.lower().endswith(".jar") and os.path.isfile(os.path.join(self.JAR_DIR, f))
        )
        return f"共扫描到 {count} 个JAR文件"

    def _page_number(self, value):
        try:
            return max(1, int(value))
        except Exception:
            return 1

    def _paged_result(self, items, page, make_vod):
        total = len(items)
        page_size = max(1, self.PAGE_SIZE)
        page_count = max(1, (total + page_size - 1) // page_size)
        page = max(1, min(page, page_count))
        start = (page - 1) * page_size
        page_items = items[start: start + page_size]
        return {
            "page": page,
            "pagecount": page_count,
            "limit": page_size,
            "total": total,
            "list": [make_vod(item) for item in page_items],
        }

    def _source_to_vod(self, source):
        return {
            "vod_id": source["type_id"],
            "vod_name": source["type_name"],
            "vod_pic": "",
            "vod_remarks": source["_type_tag"],
        }

    # ==========================================================================
    # 📺 【TVBox 标准接口】
    # ==========================================================================
    def homeContent(self, filter):
        classes = [
            {"type_id": "all", "type_name": f"全部 ({len(self.cache['sources'])})"}
        ]
        for tag in ("PY", "JS"):
            count = self.cache["type_counts"].get(tag, 0)
            if count:
                classes.append({"type_id": "type:" + tag, "type_name": f"{tag} ({count})"})
        return {"class": classes, "list": []}

    def homeVod(self):
        info = self._count_str() + " | " + self._count_jar_str()
        return {"list": [{
            "vod_id": "__debug__",
            "vod_name": info,
            "vod_pic": "",
            "vod_remarks": "统计",
        }]}

    def categoryContent(self, tid, pg, filter, ext):
        page = self._page_number(pg)

        if tid == "all":
            return self._paged_result(self.cache["sources"], page, self._source_to_vod)

        if str(tid).startswith("type:"):
            source_type = str(tid).split(":", 1)[1].upper()
            items = [s for s in self.cache["sources"] if s["_type_tag"] == source_type]
            return self._paged_result(items, page, self._source_to_vod)

        return self._category_content_single(tid)

    def _category_content_single(self, tid):
        file_info = self._get_file_info(tid)
        if not file_info:
            return {"list": []}
        f_path = file_info["path"]
        if not os.path.exists(f_path):
            return {"list": []}

        f_base = os.path.basename(f_path)
        if "." in f_base:
            f_base = f_base.rsplit(".", 1)[0]
        ext_name = file_info["ext"]
        type_tag = file_info.get("type_tag", "PY")
        sub_sfx = file_info.get("sub_sfx", "")

        v_id = base64.b64encode(
            (type_tag + "|" + f_path).encode("utf-8")
        ).decode("utf-8")

        vod_name = f"{f_base}{sub_sfx}"
        vod_remarks = "[" + ext_name.upper() + "]"

        return {
            "page": 1, "pagecount": 1, "limit": 1, "total": 1,
            "list": [{
                "vod_id": v_id,
                "vod_name": vod_name,
                "vod_pic": "",
                "vod_remarks": vod_remarks,
            }]
        }

    def detailContent(self, array):
        try:
            v_id_raw = str(array[0]) if isinstance(array, (list, tuple)) and array else str(array or "")

            if v_id_raw == "__debug__":
                return {"list": [self._status_detail()]}

            v_id_padded = v_id_raw + "=" * ((4 - len(v_id_raw) % 4) % 4)
            raw = base64.b64decode(v_id_padded).decode("utf-8", errors="ignore")

            if "|" in raw:
                type_tag, f_path = raw.split("|", 1)
            else:
                type_tag, f_path = "PY", raw

            if not os.path.exists(f_path):
                return {"list": [{"vod_name": "文件不存在", "vod_content": "路径: " + f_path}]}

            f_base = os.path.basename(f_path)
            if "." in f_base:
                f_base = f_base.rsplit(".", 1)[0]
            ext_name = f_path.rsplit(".", 1)[-1] if "." in f_path else "unknown"

            file_info = self.cache["file_index"].get(v_id_raw)
            api_path = self._build_api(file_info) if file_info else f_path
            sub_sfx = file_info.get("sub_sfx", "") if file_info else ""

            site_info = {
                "key": f_base + "_" + ext_name,
                "name": f"{f_base}{sub_sfx}",
                "type": 3,
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1,
                "api": api_path,
            }
            info_text = json.dumps(site_info, ensure_ascii=False, indent=2)

            return {"list": [{
                "vod_name": "[" + ext_name.upper() + "] " + f_base + sub_sfx,
                "vod_pic": "",
                "vod_play_from": "配置信息",
                "vod_play_url": "查看配置$" + f_path,
                "vod_content": (
                    "配置文件: " + self.SAVE_PATH + "\n\n"
                    "站点类型: " + type_tag + " | 后缀: ." + ext_name + "\n\n"
                    "站点配置:\n" + info_text + "\n\n"
                    "文件路径: " + f_path
                ),
            }]}
        except Exception as e:
            return {"list": [{"vod_name": "解析错误", "vod_content": str(e)}]}

    def _status_detail(self):
        c = self.cache["type_counts"]
        content = (
            "扫描时间: {scan_time}\n"
            "有效源: {included}\n"
            "分类统计: PY={py} JS={js}\n\n"
            "保留手工站点: {manual}\n"
            "自动注入站点: {generated}\n"
            "变更预览: +{added} -{removed} ={unchanged}\n"
            "写入状态: {state}\n\n"
            "{py_info}\n"
            "{jar_info}\n\n"
            "配置文件: {save}\n\n"
            "已扫描文件列表:\n"
            "{file_list}"
        ).format(
            scan_time=self.status["scan_time"],
            included=self.status["included"],
            py=c.get("PY", 0), js=c.get("JS", 0),
            manual=self.status["manual_sites"],
            generated=self.status["generated_sites"],
            added=self.status["added"],
            removed=self.status["removed"],
            unchanged=self.status["unchanged"],
            state=self.status["write_state"],
            py_info=self._count_str(),
            jar_info=self._count_jar_str(),
            save=self.SAVE_PATH,
            file_list="\n".join(
                f"  [{fin.get('type_tag', fin['ext'].upper())}] {fin['path']}"
                for fin in self.cache["file_index"].values()
            ) or "  无",
        )
        return {
            "vod_id": "__debug__",
            "vod_name": "扫描状态详情",
            "vod_pic": "",
            "vod_remarks": self.status["write_state"],
            "vod_content": content,
        }

    def searchContent(self, key, quick, pg="1"):
        page = self._page_number(pg)
        keyword = str(key or "").strip().lower()
        if not keyword:
            return {"list": []}
        items = [
            s for s in self.cache["sources"]
            if keyword in s["type_name"].lower()
            or keyword in s["_type_tag"].lower()
            or keyword in os.path.basename(s["_path"]).lower()
        ]
        return self._paged_result(items, page, self._source_to_vod)

    def playerContent(self, flag, id, vipFlags):
        url = id.split("$")[-1] if "$" in id else id
        return {"url": url, "header": {}, "parse": 0}

    def destroy(self):
        return "destroy"