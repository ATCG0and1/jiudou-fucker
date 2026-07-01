#!/usr/bin/env python3
"""
九斗平台 (jiudou123.com) 自动答题脚本
=========================================
用法:
  python jiudou_fucker.py                    # 交互式输入 token
  python jiudou_fucker.py --token xxx --uid xxx  # 命令行模式
"""

import sys
import os
import json
import re
import time
import html as html_mod
import requests

# Fix Windows GBK encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE = "https://api.guangyiedu.com/v3"
CLIENT = "4"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jiudou_config.json")


def strip_html(text):
    """去除 HTML 标签"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    return text.strip()


def clean_answer(answer):
    """剥HTML → 去 Reference answer 前缀 → 取 ^* 第一个 → 纯单行文本"""
    if not answer:
        return ""
    t = html_mod.unescape(answer)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = t.replace('\xa0', ' ').replace('&nbsp;', ' ')
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'^Reference\s+answer\s*:?\s*', '', t, flags=re.IGNORECASE).strip()
    t = re.sub(r'^参考答案\s*:?\s*', '', t).strip()
    return t.split('^*')[0].strip()


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(token, uid):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"token": token, "uid": uid}, f, indent=2)


class JiudouFucker:
    def __init__(self, token, uid):
        self.token = token
        self.uid = int(uid)
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/149.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://www.jiudou123.com",
            "Referer": "https://www.jiudou123.com/",
        })
        self.stats = {"total": 0, "success": 0, "failed": 0, "skipped": 0}

    def _post(self, path, data, ok_codes=(200,)):
        """POST 请求，ok_codes 为允许的 code 列表"""
        data.setdefault("client", CLIENT)
        data.setdefault("token", self.token)
        data.setdefault("uid", self.uid)
        r = self.s.post(f"{API_BASE}{path}", data=data, timeout=30)
        j = r.json()
        if j["code"] not in ok_codes:
            raise Exception(j.get("msg", "未知错误"))
        return j

    def fetch_exercise_list(self):
        """获取单元列表"""
        j = self._post("/clazz/exercise/stu/exercisesPage",
                       {"page": 1, "pagesize": 50})
        return j["data"]["data"]

    def fetch_exercise_info(self, exercises_id):
        """获取习题详情（含题目+答案）"""
        j = self._post("/tiku/exerciseStu/exercisesInfo",
                       {"exerciseId": exercises_id})
        return j["data"]

    def submit(self, exercises_id, answers_json, auto_withdraw=False):
        """提交答案。auto_withdraw=True 时自动处理"已提交过"的情况"""
        last_err = None
        for attempt in range(5):
            try:
                j = self._post("/tiku/exerciseStu/commitAnswer", {
                    "exerciseId": exercises_id,
                    "answers": answers_json,
                }, ok_codes=(200,))
                return j["msg"]
            except Exception as e:
                last_err = e
                msg = str(e)
                if "已经提交" in msg and auto_withdraw:
                    self.withdraw(exercises_id)
                    time.sleep(1)
                    auto_withdraw = False  # 只撤回一次
                    continue
                if "正在处理" in msg or "请稍后" in msg:
                    wait = 2 * (attempt + 1)
                    print(f"    服务器忙，{wait}秒后重试...")
                    time.sleep(wait)
                    continue
                raise
        raise last_err

    def withdraw(self, exercises_id):
        """撤回"""
        self._post("/tiku/v4/exerciseStu/withdraw",
                   {"exercisesId": exercises_id})

    def build_answers(self, data):
        """从 API 数据构建 answers 数组"""
        entries = []
        for subj in data.get("subjects", []):
            sid = str(subj["subjectId"])
            ttype = subj.get("tSubject", 0)
            sons = subj.get("sonSubList", [])

            if sons:
                # 组合题/复合题：父题无 stuAnswer
                entries.append({"lang": "", "subjectId": sid})
                for son in sons:
                    entries.append({
                        "lang": "",
                        "subjectId": str(son["subjectId"]),
                        "stuAnswer": clean_answer(son.get("answer", "")),
                    })
            else:
                # 普通题：直接取 answer
                entries.append({
                    "lang": "",
                    "subjectId": sid,
                    "stuAnswer": clean_answer(subj.get("answer", "")),
                })
        return json.dumps(entries, ensure_ascii=False)

    def do_one(self, exercises_id, force=False):
        """处理一个单元"""
        info = self.fetch_exercise_info(exercises_id)
        name = info["exerciseName"]
        status = info["status"]
        subjects = info.get("subjects", [])

        # 检查是否已完成
        if status != 0 and not force:
            print(f"  [{name}] 已完成，跳过")
            self.stats["skipped"] += 1
            return

        # 统计题目
        total_q = len(subjects)
        total_blanks = sum(len(s.get("sonSubList", [])) for s in subjects)
        print(f"  [{name}] {total_q}题 {total_blanks}空")

        # 构建答案并提交
        answers_json = self.build_answers(info)

        try:
            msg = self.submit(exercises_id, answers_json, auto_withdraw=True)
            if msg == "提交成功":
                print(f"    -> 提交成功！")
                self.stats["success"] += 1
            else:
                print(f"    -> 失败: {msg}")
                self.stats["failed"] += 1
        except Exception as e:
            print(f"    -> 错误: {e}")
            self.stats["failed"] += 1

    def do_all(self, force=False):
        """处理所有单元"""
        exercises = self.fetch_exercise_list()
        self.stats["total"] = len(exercises)

        # 过滤：只做状态为 0 的（未完成）
        todo = [e for e in exercises if force or e["status"] == 0]
        skip = len(exercises) - len(todo)

        print(f"\n共 {len(exercises)} 个单元，需处理 {len(todo)} 个，已完成 {skip} 个\n")
        print("=" * 50)

        for i, ex in enumerate(todo, 1):
            print(f"\n[{i}/{len(todo)}]", end="")
            self.do_one(ex["exercisesId"], force=force)
            time.sleep(2)  # 避免请求过快被限流

        print(f"\n{'=' * 50}")
        print(f"完成! 总计:{self.stats['total']} "
              f"成功:{self.stats['success']} "
              f"失败:{self.stats['failed']} "
              f"跳过:{self.stats['skipped']}")


def get_token_from_user():
    """交互式获取 token 和 uid"""
    print("=" * 50)
    print("  九斗平台自动答题脚本")
    print("=" * 50)
    print()
    print("请按以下步骤获取 token 和 uid：")
    print("  1. 浏览器打开 https://www.jiudou123.com 并登录")
    print("  2. F12 -> Application -> Cookies -> www.jiudou123.com")
    print("  3. 找到 token 这一行，复制它的 Value")
    print()

    token = input("粘贴 token: ").strip()
    if not token:
        print("token 不能为空！")
        sys.exit(1)

    # 尝试从 stu_info cookie 中获取 uid
    print()
    print("  4. 在同个 Cookies 列表中，找到 stu_info")
    print("     复制它的 Value (一串 % 编码的字符)")
    print()
    stu_info = input("粘贴 stu_info: ").strip()

    uid = None
    if stu_info:
        import urllib.parse
        try:
            decoded = urllib.parse.unquote(stu_info)
            info = json.loads(decoded)
            uid = info.get("uid")
            print(f"    -> 解析到 uid={uid}, 姓名={info.get('realName', '?')}")
        except Exception:
            pass

    if not uid:
        uid = input("手动输入 uid (数字): ").strip()

    return token, uid


def main():
    config = load_config()
    token = config.get("token", "")
    uid = config.get("uid", "")

    # 命令行参数优先
    import argparse
    parser = argparse.ArgumentParser(description="九斗平台自动答题")
    parser.add_argument("--token", type=str, help="你的 token")
    parser.add_argument("--uid", type=int, help="你的 uid")
    parser.add_argument("--force", action="store_true", help="强制重做已完成单元")
    parser.add_argument("--save", action="store_true", help="保存 token 到本地文件")
    args = parser.parse_args()

    if args.token:
        token = args.token
    if args.uid:
        uid = args.uid

    # 没有 token 则交互式输入
    if not token:
        token, uid = get_token_from_user()
        if not uid:
            print("uid 不能为空！")
            sys.exit(1)

    save = args.save or (not config.get("token"))
    if save and token:
        save_config(token, uid)
        print(f"token 已保存到 {CONFIG_FILE}")

    fucker = JiudouFucker(token, uid)
    fucker.do_all(force=args.force)


if __name__ == "__main__":
    main()
