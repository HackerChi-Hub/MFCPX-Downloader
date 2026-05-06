#!/usr/bin/env python3
"""
百度网盘批量转存 - 直接 API 版
==============================
原理：从已登录的 Chrome Profile 7 提取真实 Cookie，
直接调用百度网盘 HTTP 转存 API，完全不需要打开浏览器。

使用方法：
  python3 baidu_transfer_api.py               # 正常运行
  python3 baidu_transfer_api.py --test        # 只处理第一条链接，验证可行性
  python3 baidu_transfer_api.py --dest /FCP插件  # 指定目标目录（默认 /FCP插件）
  python3 baidu_transfer_api.py --delay 5    # 自定义每条间隔秒数（默认 4）

依赖：
  pip install requests browser-cookie3 --break-system-packages
"""

import os
import sys
import json
import re
import time
import subprocess
import argparse
from pathlib import Path

# ─── 自动安装依赖 ────────────────────────────────────────────────────────────

def ensure_deps():
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import browser_cookie3  # noqa: F401
    except ImportError:
        missing.append("browser-cookie3")
    if missing:
        print(f"📦 安装依赖: {', '.join(missing)}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", "-q"] + missing,
            check=True,
        )

ensure_deps()

import requests  # noqa: E402
import browser_cookie3  # noqa: E402

# ─── 配置 ────────────────────────────────────────────────────────────────────

SCRIPT_DIR    = Path(__file__).parent
LINKS_FILE    = SCRIPT_DIR / "baidu_share_links.txt"
PROGRESS_FILE = SCRIPT_DIR / "transfer_api_progress.json"

CHROME_PROFILE = Path.home() / "Library/Application Support/Google/Chrome/Profile 7"

APP_ID    = "250528"
BASE_HDRS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding":  "identity",   # 全局禁用压缩，避免 gzip 解码异常
    "Origin":           "https://pan.baidu.com",
    "Referer":          "https://pan.baidu.com/",
}

# ─── Cookie 提取 ─────────────────────────────────────────────────────────────

def get_cookies_from_chrome() -> dict:
    """从 Chrome Profile 7 自动提取百度 Cookie（支持 macOS Keychain 解密）"""
    cookie_db = CHROME_PROFILE / "Cookies"
    if not cookie_db.exists():
        print(f"  ⚠️  找不到 Cookie 文件: {cookie_db}")
        return {}

    try:
        cj = browser_cookie3.chrome(
            domain_name=".baidu.com",
            cookie_file=str(cookie_db),
        )
        cookies = {c.name: c.value for c in cj if "baidu" in (c.domain or "")}
        print(f"  ✅ 提取到 {len(cookies)} 个 Cookie: {', '.join(cookies.keys())}")
        return cookies
    except Exception as e:
        print(f"  ❌ browser_cookie3 失败: {e}")
        return {}


def ask_manual_cookies() -> dict:
    """引导用户手动粘贴关键 Cookie"""
    print("\n  手动输入方式：")
    print("  1. Chrome 打开 https://pan.baidu.com")
    print("  2. F12 → Application → Cookies → pan.baidu.com")
    print("  3. 分别复制 BDUSS 和 STOKEN 的值\n")
    bduss  = input("  BDUSS  = ").strip()
    stoken = input("  STOKEN = ").strip()
    baiduid = input("  BAIDUID (可留空) = ").strip()
    cookies: dict = {"BDUSS": bduss}
    if stoken:
        cookies["STOKEN"] = stoken
    if baiduid:
        cookies["BAIDUID"] = baiduid
    return cookies

# ─── 百度网盘 API ──────────────────────────────────────────────────────────────

def get_cookie(jar, name: str, default: str = "") -> str:
    """
    安全地从 CookieJar 里取值。
    当同名 cookie 有多个（来自不同 domain）时，优先返回最后设置的那个
    （通常是刚刚 verify 设下的，而不是 Chrome 里的旧值）。
    """
    values = [c.value for c in jar if c.name == name]
    return values[-1] if values else default


def make_session(cookies: dict) -> requests.Session:
    s = requests.Session()
    s.cookies.update(cookies)
    s.headers.update(BASE_HDRS)
    return s


def check_login(s: requests.Session) -> tuple[bool, str, str]:
    """返回 (is_logged_in, bdstoken, uk)"""
    try:
        r = s.get(
            "https://pan.baidu.com/api/gettemplatevariable",
            params={
                "clienttype": 0, "app_id": APP_ID, "web": 1,
                "fields": '["bdstoken","token","uk","isdocuser","servertime"]',
            },
            timeout=15,
        )
        result = r.json().get("result", {})
        bdstoken = result.get("bdstoken", "")
        uk       = str(result.get("uk", ""))
        return bool(bdstoken), bdstoken, uk
    except Exception as e:
        print(f"  登录检查异常: {e}")
        return False, "", ""


def purge_and_set_bdclnd(s: requests.Session, new_value: str) -> None:
    """
    彻底清除 session 里所有 BDCLND cookie（不同 domain/path 可能有多个），
    然后只留一个正确的新值。多个 BDCLND 同时发给百度会导致 errno=2。
    """
    # 收集所有非 BDCLND 的 Cookie 对象
    other_cookies = [c for c in s.cookies if c.name != "BDCLND"]
    # 清空整个 jar
    s.cookies.clear()
    # 重新写回非 BDCLND 的 cookie
    for c in other_cookies:
        s.cookies.set_cookie(c)
    # 设置唯一的新 BDCLND
    if new_value:
        s.cookies.set("BDCLND", new_value, domain="pan.baidu.com", path="/")


def verify_pwd(s: requests.Session, surl: str, pwd: str) -> bool:
    """
    提交提取码，并确保 session 里只有一个正确的 BDCLND。
    """
    if not pwd:
        # 无密码的公开分享：也清掉旧 BDCLND 避免干扰
        purge_and_set_bdclnd(s, "")
        return True
    try:
        # 先把所有旧 BDCLND 清掉（包括 Chrome 带来的多个）
        purge_and_set_bdclnd(s, "")

        r = s.post(
            "https://pan.baidu.com/share/verify",
            params={
                "surl": surl, "t": int(time.time() * 1000),
                "channel": "chunlei", "web": 1,
                "app_id": APP_ID, "clienttype": 0,
            },
            data={"pwd": pwd, "vcode": "", "vcode_str": ""},
            headers={"Referer": f"https://pan.baidu.com/s/1{surl}"},
            timeout=15,
        )
        data = r.json()
        errno = data.get("errno", -1)
        print(f"         verify 完整响应: {data}")   # 关键调试行

        if errno != 0:
            return False

        # 优先从响应 JSON body 里提取 sekey（randsk / sekey 字段）
        body_sekey = data.get("randsk") or data.get("sekey") or ""

        # 从响应 Set-Cookie 里拿 BDCLND
        new_bdclnd = get_cookie(r.cookies, "BDCLND") or get_cookie(s.cookies, "BDCLND")
        purge_and_set_bdclnd(s, new_bdclnd)

        # 把 body_sekey 存到 session 上以便 share/list 使用
        s._share_sekey = body_sekey  # type: ignore[attr-defined]

        if body_sekey:
            print(f"         sekey(body)={body_sekey[:12]}…")
        if new_bdclnd:
            print(f"         BDCLND(cookie)={new_bdclnd[:12]}… (唯一)")
        else:
            print(f"         ⚠️  verify 未收到 BDCLND cookie")
        return True
    except Exception as e:
        print(f"    密码验证异常: {e}")
        return False




def _extract_fsids_from_html(html: str) -> tuple[str, str, list[int]]:
    """
    直接从分享页 HTML 里提取 shareid、share_uk、和 fs_id 列表。
    百度把文件列表以 JSON 形式嵌入页面，无需调 share/list API。
    返回 (shareid, uk, fsids)；任一缺失则返回 ("", "", [])
    """
    # ── 1. 提取 yunData（含 shareid / share_uk）─────────────────────
    shareid = uk = ""
    m = re.search(r'window\.yunData\s*=\s*\{([^}]+)\}', html)
    if m:
        block = m.group(1)
        ms = re.search(r'\bshareid\s*:\s*["\']?(\d+)["\']?', block)
        mu = re.search(r'\bshare_uk\s*:\s*["\'](\d+)["\']', block)
        if ms:
            shareid = ms.group(1)
        if mu:
            uk = mu.group(1)

    # ── 2. 提取嵌入 HTML 的文件列表 JSON（含 fs_id）───────────────────
    # 百度把文件对象数组直接写进页面脚本，格式为 [...{fs_id:xxx,...},...]
    fsids: list[int] = []
    idx = html.find('"fs_id"')
    if idx != -1:
        # 往前找最近的 [
        start = -1
        for i in range(idx, max(idx - 50000, 0), -1):
            if html[i] == '[':
                start = i
                break
        if start != -1:
            # 往后找配对的 ]
            depth = 0
            end = start
            for i in range(start, min(start + 500000, len(html))):
                if html[i] == '[':
                    depth += 1
                elif html[i] == ']':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                lst = json.loads(html[start:end])
                if isinstance(lst, list):
                    fsids = [int(item["fs_id"]) for item in lst if "fs_id" in item]
            except Exception:
                pass

    return shareid, uk, fsids


def get_share_info_and_files(
    s: requests.Session, surl: str,
    dump_html_path: Path | None = None,
) -> tuple[str | None, str | None, list[int]]:
    """
    从分享页 HTML 直接提取 shareid、uk、fs_id 列表。
    无需调用 share/list API（百度已把文件列表嵌入页面）。
    必须在 verify_pwd 之后调用（session 里带有 BDCLND cookie）。
    返回 (shareid, uk, fsids)
    """
    # ── 获取分享页 HTML ───────────────────────────────────────────────
    html = ""
    try:
        r2 = s.get(
            f"https://pan.baidu.com/s/1{surl}",
            headers={"Referer": "https://pan.baidu.com/", "Accept-Encoding": "identity"},
            timeout=20,
        )
        html = r2.content.decode("utf-8", errors="replace")
        print(f"    分享页: status={r2.status_code} len={len(html)}")

        if dump_html_path:
            dump_html_path.write_text(html, encoding="utf-8")
            print(f"    💾 HTML 已保存至 {dump_html_path}")
    except Exception as e:
        print(f"    HTML 获取异常: {e}")
        return None, None, []

    # ── 从 HTML 提取所有信息 ──────────────────────────────────────────
    shareid, uk, fsids = _extract_fsids_from_html(html)

    if shareid and uk and fsids:
        return shareid, uk, fsids

    # 诊断输出
    if not shareid or not uk:
        print(f"    ⚠️  yunData 提取失败: shareid={shareid!r} uk={uk!r}")
        m = re.search(r'window\.yunData\s*=\s*\{[^}]+\}', html)
        if m:
            print(f"    yunData 原文: {m.group()[:300]}")
        else:
            print(f"    HTML 前300字: {html[:300]}")
    if not fsids:
        print(f"    ⚠️  页面未找到 fs_id（分享链接可能已失效，或密码未生效）")

    return (shareid or None), (uk or None), fsids


def do_transfer(
    s: requests.Session,
    shareid: str, uk: str,
    fsids: list[int],
    bdstoken: str,
    dest: str,
    surl: str,
) -> tuple[bool, str]:
    """
    执行转存。
    返回 (success, message)
    errno 含义：
      0  → 成功
      12 → 已有同名文件（视为成功）
      -6 → 未登录 / token 过期
      4  → 目标文件夹不存在
    """
    try:
        r = s.post(
            "https://pan.baidu.com/share/transfer",
            params={
                "shareid": shareid, "from": uk,
                "bdstoken": bdstoken,
                "channel": "chunlei", "web": 1,
                "app_id": APP_ID, "clienttype": 0,
                "ondup": "newcopy",
            },
            data={
                "fsidlist": json.dumps(fsids),
                "path": dest,
            },
            headers={"Referer": "https://pan.baidu.com/"},
            timeout=30,
        )
        data = r.json()
        errno = data.get("errno", -1)

        if errno == 0:
            return True, "转存成功"
        elif errno == 12:
            return True, "文件已存在（跳过）"
        elif errno == -6:
            return False, "登录过期，需要重新登录"
        elif errno == 4:
            return False, f"目标目录不存在: {dest}"
        elif errno == 130:
            return False, "触发频率限制，需要等待"
        else:
            return False, f"errno={errno} | {data}"
    except Exception as e:
        return False, f"请求异常: {e}"

# ─── 链接解析 ────────────────────────────────────────────────────────────────

def parse_links(filepath: Path) -> list[dict]:
    """
    支持两种格式：
      https://pan.baidu.com/s/1xxxxx  pwd
      https://pan.baidu.com/s/1xxxxx?pwd=xxxx
    """
    links = []
    with open(filepath, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # 行内 ?pwd= 格式
            url_part = line.split()[0] if line.split() else ""
            pwd_part  = line.split()[1] if len(line.split()) > 1 else ""

            # URL 本身带了 ?pwd=
            m_inline = re.search(r"[?&]pwd=([a-zA-Z0-9]+)", url_part)
            if m_inline:
                pwd_part = pwd_part or m_inline.group(1)
                url_part = url_part.split("?")[0]

            # 提取 surl（去掉开头的 1）
            m_surl = re.search(r"/s/1([a-zA-Z0-9_\-]+)", url_part)
            if not m_surl:
                continue

            links.append({
                "url":  url_part,
                "surl": m_surl.group(1),   # 不含开头的 '1'
                "pwd":  pwd_part.strip(),
            })
    return links

# ─── 主流程 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="百度网盘批量转存（直接 API 版）")
    parser.add_argument("--dest",      default="/FCP插件", help="目标目录，默认 /FCP插件")
    parser.add_argument("--delay",     type=float, default=4.0, help="每条链接间隔秒数（默认 4）")
    parser.add_argument("--test",      action="store_true", help="只处理第一条，验证可行性")
    parser.add_argument("--index",     type=int, default=0, help="只处理第 N 条（1-based），配合调试用")
    parser.add_argument("--dump-html", type=int, default=0,
                        metavar="N", dest="dump_html",
                        help="把第 N 条链接的分享页 HTML 保存到文件（供调试用），不执行转存")
    args = parser.parse_args()

    print("=" * 62)
    print("   百度网盘批量转存（直接 API 版）")
    print("=" * 62)

    # ── 1. 提取 Cookie ──────────────────────────────────────────────
    print("\n🔑 正在从 Chrome Profile 7 提取百度 Cookie…")
    cookies = get_cookies_from_chrome()

    if "BDUSS" not in cookies:
        print("  ⚠️  自动提取失败，切换到手动输入模式")
        cookies = ask_manual_cookies()

    if not cookies.get("BDUSS"):
        print("❌ 无法获取 BDUSS，退出")
        sys.exit(1)

    # ── 2. 建立 Session & 验证登录 ──────────────────────────────────
    print("\n🔐 验证登录状态…")
    s = make_session(cookies)
    logged_in, bdstoken, my_uk = check_login(s)

    if not logged_in:
        print("❌ 未登录或 Cookie 已过期。请先在 Chrome 中登录百度网盘，再运行本脚本。")
        sys.exit(1)
    print(f"  ✅ 已登录  bdstoken={bdstoken[:8]}…  uk={my_uk}")

    # ── 3. 加载链接 ──────────────────────────────────────────────────
    if not LINKS_FILE.exists():
        print(f"❌ 找不到链接文件: {LINKS_FILE}")
        sys.exit(1)

    all_links = parse_links(LINKS_FILE)
    if args.index:
        idx0 = args.index - 1
        if 0 <= idx0 < len(all_links):
            all_links = [all_links[idx0]]
            print(f"\n🧪 单条测试：第 {args.index} 条链接")
        else:
            print(f"❌ --index {args.index} 超出范围（共 {len(all_links)} 条）")
            sys.exit(1)
    elif args.test:
        all_links = all_links[:1]
        print(f"\n🧪 测试模式：只处理第 1 条链接")
    else:
        print(f"\n📋 共找到 {len(all_links)} 条分享链接")

    # ── dump-html 模式：只保存 HTML，不执行转存 ───────────────────────
    if args.dump_html:
        idx0 = args.dump_html - 1
        if not (0 <= idx0 < len(all_links)):
            print(f"❌ --dump-html {args.dump_html} 超出范围（共 {len(all_links)} 条）")
            sys.exit(1)
        link = all_links[idx0]
        surl = link["surl"]
        print(f"\n💾 dump-html 模式：第 {args.dump_html} 条 {link['url']}")
        if link["pwd"]:
            verify_pwd(s, surl, link["pwd"])
        out_path = SCRIPT_DIR / f"dump_share_{args.dump_html}.html"
        r_html = s.get(
            f"https://pan.baidu.com/s/1{surl}",
            headers={"Referer": "https://pan.baidu.com/", "Accept-Encoding": "identity"},
            timeout=20,
        )
        html_content = r_html.content.decode("utf-8", errors="replace")
        out_path.write_text(html_content, encoding="utf-8")
        print(f"✅ 已保存 {len(html_content)} 字节 → {out_path}")
        # 同时打印关键诊断
        for kw in ["SHARE_ID", "SHARE_UK", "yunData", "__NEXT_DATA__", "shareid"]:
            for m in re.finditer(rf'.{{0,80}}{re.escape(kw)}.{{0,80}}', html_content):
                print(f"  [{kw}]: {m.group().strip()[:180]}")
                break
        sys.exit(0)

    # ── 4. 加载已有进度 ──────────────────────────────────────────────
    progress: dict = {}
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            progress = json.load(f)
        done = sum(1 for v in progress.values() if v.get("ok"))
        print(f"📊 历史进度：已完成 {done} / {len(all_links)}")

    # ── 5. 批量处理 ──────────────────────────────────────────────────
    print(f"\n🚀 开始转存 → 目标目录: {args.dest}\n")
    saved = skipped = failed = 0

    for idx, link in enumerate(all_links, 1):
        surl = link["surl"]
        full_surl = "1" + surl   # 完整路径用 1+surl

        # 已成功则跳过
        if progress.get(surl, {}).get("ok"):
            skipped += 1
            print(f"[{idx:>3}/{len(all_links)}] ⏭  已完成，跳过")
            continue

        print(f"[{idx:>3}/{len(all_links)}] {link['url']}")
        if link["pwd"]:
            print(f"         pwd={link['pwd']}")

        step_ok = True

        # 5-a. 密码验证
        if link["pwd"]:
            ok = verify_pwd(s, surl, link["pwd"])
            if ok:
                print(f"         ✅ 密码通过")
            else:
                print(f"         ❌ 密码错误")
                progress[surl] = {"ok": False, "reason": "wrong_password", "url": link["url"]}
                failed += 1
                step_ok = False

        # 5-b. 获取 shareid / uk / fsids（合并一步）
        shareid = uk = None
        fsids: list[int] = []
        if step_ok:
            shareid, uk, fsids = get_share_info_and_files(s, surl, dump_html_path=None)
            if not shareid or not uk or not fsids:
                print(f"         ❌ 无法获取分享信息或文件列表（链接可能已失效或密码未生效）")
                progress[surl] = {"ok": False, "reason": "no_meta_or_files", "url": link["url"]}
                failed += 1
                step_ok = False
            else:
                print(f"         📌 shareid={shareid}  uk={uk}  文件数={len(fsids)}")

        # 5-c. 执行转存
        if step_ok:
            ok, msg = do_transfer(s, shareid, uk, fsids, bdstoken, args.dest, surl)
            if ok:
                print(f"         ✅ {msg}")
                progress[surl] = {"ok": True, "msg": msg, "url": link["url"]}
                saved += 1
            else:
                print(f"         ❌ {msg}")
                progress[surl] = {"ok": False, "reason": msg, "url": link["url"]}
                failed += 1
                # 登录过期 → 立即停止
                if "登录过期" in msg:
                    print("\n⛔ 登录已过期，保存进度后退出。")
                    break
                # 频率限制 → 多等一会儿
                if "频率限制" in msg:
                    print("         ⏳ 等待 30 秒后继续…")
                    time.sleep(30)

        # 保存进度
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

        # 礼貌等待
        if idx < len(all_links):
            time.sleep(args.delay)

    # ── 6. 汇总 ────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    total_done = saved + skipped
    print(f"  ✅ 新转存: {saved}  |  ⏭  已跳过: {skipped}  |  ❌ 失败: {failed}")
    print(f"  进度文件: {PROGRESS_FILE}")
    print("=" * 62)


if __name__ == "__main__":
    main()
