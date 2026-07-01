#!/usr/bin/env python3
"""
九斗平台全自动答题脚本（傻瓜版）
================================
用法:
  python jiudou_auto.py              # 默认：登录后 Enter，全自动满分
  python jiudou_auto.py --menu       # 交互式菜单（查看单元/选择操作）
  python jiudou_auto.py --force      # 强制重做所有单元

流程:
  1. 自动打开浏览器 → 九斗登录页
  2. 用户扫码/账号登录
  3. 登录成功后按 Enter → 全自动完成全部单元
  4. 满分提交！
"""

import sys
import os
import json
import re
import time
import html as html_mod
import requests
from urllib.parse import unquote

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE = "https://api.guangyiedu.com/v3"
LOGIN_URL = "https://www.jiudou123.com"


def strip_html(text):
    if not text: return ""
    return html_mod.unescape(re.sub(r"<[^>]+>", "", text))

def clean_answer(answer):
    """剥HTML → 去 Reference answer 前缀 → 取 ^* 第一个 → 纯单行文本"""
    if not answer: return ""
    t = html_mod.unescape(answer)
    # 剥所有 HTML 标签
    t = re.sub(r'<[^>]+>', ' ', t)
    t = t.replace('\xa0', ' ').replace('&nbsp;', ' ')
    # 合并空白
    t = re.sub(r'\s+', ' ', t).strip()
    # 去 Reference answer / 参考答案 前缀
    t = re.sub(r'^Reference\s+answer\s*:?\s*', '', t, flags=re.IGNORECASE).strip()
    t = re.sub(r'^参考答案\s*:?\s*', '', t).strip()
    # 取 ^* 分隔的第一个
    return t.split('^*')[0].strip()


class JiudouAPI:
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

    def _post(self, path, data, ok_codes=(200,)):
        data.setdefault("client", "4")
        data.setdefault("token", self.token)
        data.setdefault("uid", self.uid)
        r = self.s.post(f"{API_BASE}{path}", data=data, timeout=30)
        j = r.json()
        if j["code"] not in ok_codes:
            raise Exception(j.get("msg", "未知错误"))
        return j

    def get_exercises(self):
        return self._post("/clazz/exercise/stu/exercisesPage",
                          {"page": 1, "pagesize": 50})["data"]["data"]

    def get_exercise_info(self, exercises_id):
        return self._post("/tiku/exerciseStu/exercisesInfo",
                          {"exerciseId": exercises_id})["data"]

    def withdraw(self, exercises_id):
        self._post("/tiku/v4/exerciseStu/withdraw", {"exercisesId": exercises_id})

    def commit(self, exercises_id, answers_json):
        last_err = None
        for attempt in range(5):
            try:
                j = self._post("/tiku/exerciseStu/commitAnswer", {
                    "exerciseId": exercises_id, "answers": answers_json,
                }, ok_codes=(200,))
                return j["msg"]
            except Exception as e:
                last_err = e
                msg = str(e)
                if "已经提交" in msg:
                    self.withdraw(exercises_id)
                    time.sleep(1)
                    continue
                if "正在处理" in msg or "请稍后" in msg:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise
        raise last_err

    def build_answers(self, info):
        entries = []
        for subj in info.get("subjects", []):
            sid = str(subj["subjectId"])
            sons = subj.get("sonSubList", [])
            if sons:
                entries.append({"lang": "", "subjectId": sid})
                for son in sons:
                    entries.append({
                        "lang": "", "subjectId": str(son["subjectId"]),
                        "stuAnswer": clean_answer(son.get("answer", "")),
                    })
            else:
                entries.append({
                    "lang": "", "subjectId": sid,
                    "stuAnswer": clean_answer(subj.get("answer", "")),
                })
        return json.dumps(entries, ensure_ascii=False)


# ============================================================
# 浏览器登录
# ============================================================

def login():
    """打开浏览器登录，自动获取 token"""
    print("启动浏览器...")
    print()

    try:
        from playwright.sync_api import sync_playwright
        return _login_playwright(sync_playwright)
    except ImportError:
        return _login_manual("Playwright 未安装")


def _login_playwright(p):
    user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser_data")
    with p() as pw:
        # 优先用系统已安装的浏览器（Chrome/Edge），避免下载 150MB Chromium
        context = None
        for channel in ["chrome", "msedge", None]:
            try:
                opts = {"headless": False, "viewport": {"width": 1280, "height": 800}}
                if channel:
                    context = pw.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir, channel=channel, **opts)
                else:
                    context = pw.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir, **opts)
                break
            except Exception:
                continue

        if not context:
            raise Exception("未找到可用浏览器，请安装 Chrome 或 Edge")

        page = context.pages[0] if context.pages else context.new_page()
        page.goto(LOGIN_URL, wait_until="domcontentloaded")

        print("=" * 50)
        print("  请在浏览器中登录九斗平台")
        print("  登录成功后回到此处按 Enter 继续")
        print("=" * 50)
        input()

        cookies = context.cookies()
        context.close()

        return _extract_token(cookies)


def _login_manual(reason=""):
    if reason:
        print(f"  [{reason}]")
    print("=" * 50)
    print("  手动获取 token：")
    print("  浏览器 F12 → Application → Cookies")
    print("  → www.jiudou123.com → 复制 token 的 Value")
    print("=" * 50)
    token = input("\ntoken: ").strip()
    uid = input("uid (数字): ").strip()
    return token, uid


def _extract_token(cookies):
    token = uid = None
    for c in cookies:
        if c["name"] == "token": token = c["value"]
        if c["name"] == "stu_info":
            try:
                info = json.loads(unquote(c["value"]))
                uid = info.get("uid")
            except: pass
    if not token: raise Exception("未找到 token，请确认已登录")
    if not uid: raise Exception("未找到 uid")
    return token, uid


# ============================================================
# 主流程
# ============================================================

def run_quick(api, force=False):
    """快速模式：自动完成所有单元"""
    exercises = api.get_exercises()
    todo = [e for e in exercises if force or e["status"] == 0]
    skip = len(exercises) - len(todo)

    print(f"\n共 {len(exercises)} 个单元，需处理 {len(todo)} 个")
    if skip:
        print(f"已完成 {skip} 个（跳过）")
    print()

    success = failed = 0
    for i, ex in enumerate(todo, 1):
        name = ex["exercisesName"]
        eid = ex["exercisesId"]
        print(f"[{i}/{len(todo)}] {name}", end=" ", flush=True)

        try:
            info = api.get_exercise_info(eid)
            answers_json = api.build_answers(info)
            api.commit(eid, answers_json)
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAIL: {e}")
            failed += 1

        time.sleep(2)

    print(f"\n{'=' * 50}")
    print(f"  [完成] 成功: {success}  失败: {failed}")
    if skip: print(f"  [跳过] 已完成: {skip}")
    print(f"{'=' * 50}")
    print(f"\n  可以关闭此窗口了")


def run_menu(api):
    """交互式菜单模式"""
    while True:
        print()
        print("=" * 40)
        print("  九斗自动答题 - 菜单")
        print("=" * 40)
        print("  1. 查看单元列表")
        print("  2. 全部自动答题")
        print("  3. 退出")
        c = input("\n选择: ").strip()
        if c == "1":
            exs = api.get_exercises()
            for i, e in enumerate(exs, 1):
                s = "完成" if e["status"] != 0 else "未答"
                print(f"  {i:2d}. [{s}] {e['exercisesName']}")
        elif c == "2":
            force = input("  强制重做已完成的? (y/N): ").strip().lower() == "y"
            run_quick(api, force=force)
        elif c == "3":
            print("再见!")
            break


def main():
    import argparse
    parser = argparse.ArgumentParser(description="九斗全自动答题")
    parser.add_argument("--menu", action="store_true", help="交互式菜单")
    parser.add_argument("--force", action="store_true", help="强制重做全部")
    parser.add_argument("--token", type=str, help="手动指定 token")
    parser.add_argument("--uid", type=int, help="手动指定 uid")
    args = parser.parse_args()

    print()
    print("=" * 50)
    print("  九斗平台全自动答题 v2.1")
    print("=" * 50)
    print()

    if args.token and args.uid:
        token, uid = args.token, args.uid
    else:
        token, uid = login()

    api = JiudouAPI(token, uid)

    if args.menu:
        run_menu(api)
    else:
        run_quick(api, force=args.force)

    print()
    input("按 Enter 退出...")


if __name__ == "__main__":
    main()
