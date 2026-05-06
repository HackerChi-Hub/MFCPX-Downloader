#!/usr/bin/env python3
"""
mfcpx.com FCPX Resource Pipeline
Crawl → Save to Baidu Pan → Download locally

Usage:
  python3 mfcpx_pipeline.py all                  # Full pipeline
  python3 mfcpx_pipeline.py crawl [--limit N]    # Crawl resource links
  python3 mfcpx_pipeline.py save [--headful]     # Save to Baidu Pan
  python3 mfcpx_pipeline.py download             # Download from Baidu Pan
"""
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.request
import urllib.parse
import random
import argparse

# ── Config ──────────────────────────────────────────────────────────
BASE_URL = "https://www.mfcpx.com"
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = PROJECT_DIR
CRAWLED_FILE = os.path.join(DATA_DIR, "mfcpx_crawled.json")
SAVE_RESULTS_FILE = os.path.join(DATA_DIR, "save_results.json")
TOKEN_FILE = os.path.join(DATA_DIR, "baidu_tokens.json")
DOWNLOAD_DIR = "/Volumes/BigDisk/Download/FCPX-Plugins"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PROFILE_SRC = os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 7")
PROFILE_TMP = "/tmp/chrome_bduss_profile"
CDP_PORT = 9222

CATEGORIES = [
    # (name, path) — tutorials/software/presets excluded
    ("transitions", "/chajian/transitions/"),
    ("titles", "/chajian/titles/"),
    ("effects", "/chajian/effects/"),
    ("color", "/chajian/color/"),
    ("generators", "/chajian/generators/"),
    ("logo", "/chajian/logo/"),
    ("mg", "/chajian/mg/"),
    ("templates", "/chajian/fcpxmoban/"),
    ("audio_plugins", "/chajian/ypcj/"),
    ("other_plugins", "/chajian/other-chajian/"),
    # ("tutorials", "/jiaocheng/"),       # excluded: all tutorials
    # ("software", "/ruanjian/"),         # excluded: app downloads
    # ("presets", "/yushe/"),             # excluded: mostly LUTs/presets
    ("motion_plugins", "/motion/chajian-motion/"),
    # ("motion_tutorials", "/motion/jiaocheng-motion/"),  # excluded
    ("motion_templates", "/motion/muban/"),
    ("video_assets", "/other/video/"),
    ("audio_assets", "/other/audio/"),
]

POSTS_PER_CATEGORY = 30
POSTS_PER_PAGE = 20  # approximate

# Title patterns to EXCLUDE (software, tutorials — not directly usable plugins/templates)
EXCLUDE_PATTERNS = [
    # ── App/software downloads ──
    r'Final Cut Pro X?\s*\d',           # FCPX itself (10.4.x, 10.5, etc.)
    r'FCPX?[\s\-]*(?:破解|激活|直装)',   # Cracked/activated FCPX
    r'免费下载FCPX?',                     # FCPX free download
    r'苹果视频剪辑.*软件',                 # FCPX software download
    r'Compressor\s*[Vv]?\d',            # Compressor app
    r'Motion\s*[Vv]?\d',                # Motion app (not Motion templates)
    r'Logic\s*Pro\s*[XxVv]?\s*\d?',     # Logic Pro app
    r'FxFactory\s*Pro\s*\d',            # FxFactory app
    r'DaVinci\s*Resolve',               # DaVinci Resolve app
    r'Premiere\s*Pro',                   # Premiere Pro app (not for FCPX)
    r'After\s*Effects',                  # AE app (not for FCPX)
    r'iMovie',                           # iMovie
    r'macOS',                            # macOS system
    r'^Mac\s',                           # Mac system stuff
    r'苹果.*(?:系统|安装)',               # Apple system/install
    r'安装包',                           # Installation packages
    # ── Tutorials/courses ──
    r'教程',                             # Any tutorial
    r'课程',                             # Course
    r'培训',                             # Training
    r'入门',                             # Beginner/intro guide
    r'大师班',                           # Masterclass
    r'学习',                             # Learning
    r'实战',                             # Practical exercise (often tutorial)
    r'Skillshare',                       # Skillshare courses
    r'Udemy',                            # Udemy courses
    r'MotionArray',                      # MotionArray subscription
    r'中文系列',                         # Chinese series (usually tutorials)
    r'系列教程',                         # Tutorial series
    r'摄影(?:技术|技巧|大师|课程)',       # Photography tutorials
    r'剪辑(?:技巧|技术|入门|教程|大师)',  # Editing tutorials
    r'调色(?:技巧|技术|入门|教程)',       # Color grading tutorials
    r'后期制作',                         # Post-production (usually tutorials)
    r'视频制作',                         # Video production tutorials
    r'影视后期',                         # Film post-production
    r'商业.*摄影',                       # Commercial photography
    r'电影.*摄影',                       # Cinematography
    r'短片制作',                         # Short film making
    r'PR教程',                           # Premiere tutorials
    r'AE教程',                           # AE tutorials
]

# Bypass TUN proxy for direct connections
os.environ['all_proxy'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['no_proxy'] = '*'
os.environ['NO_PROXY'] = '*'
# ────────────────────────────────────────────────────────────────────


# ════════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════════

def make_ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def fetch(url, timeout=20):
    """Fetch URL content. Uses curl subprocess to bypass TUN SSL issues."""
    env = os.environ.copy()
    env['all_proxy'] = ''
    env['ALL_PROXY'] = ''
    env['no_proxy'] = '*'
    env['NO_PROXY'] = '*'
    try:
        result = subprocess.run(
            ["curl", "-s", "-k", "--max-time", str(timeout),
             "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
             "-H", "Accept: text/html,application/xhtml+xml,application/xml",
             url],
            capture_output=True, timeout=timeout + 5, env=env
        )
        if result.returncode == 0:
            html = result.stdout.decode('utf-8', errors='replace')
            # Return a file-like object compatible with callers
            return _FakeResponse(html)
        raise Exception(f"curl exit {result.returncode}: {result.stderr.decode()[:200]}")
    except subprocess.TimeoutExpired:
        raise Exception("curl timeout")


class _FakeResponse:
    """Minimal file-like wrapper for HTML string (from curl)."""
    def __init__(self, html):
        self.html = html
        self.status = 200
    def read(self):
        return self.html.encode('utf-8')


def extract_post_urls(html):
    """Extract article URLs from a category listing page."""
    urls = re.findall(r'href="(https://www\.mfcpx\.com/[a-z0-9_-]+/)"', html)
    # Filter out structural/category links
    skip = {'/chajian/', '/jiaocheng/', '/ruanjian/', '/yushe/', '/motion/', '/other/',
            '/page/', '/wp-', '/tag/', '/author/', '/category/', '/feed/', '/comments/'}
    return list(dict.fromkeys(u for u in urls if not any(s in u for s in skip)))


def extract_download_links(html):
    """Extract Baidu Pan links and passwords from a post page."""
    baidu_links = set()
    passwords = set()
    ali_links = set()

    # Baidu Pan links
    for m in re.finditer(r'(https?://(?:pan|yun)\.baidu\.com/s/[A-Za-z0-9_-]+)', html):
        link = m.group(1).rstrip('，。、！')
        baidu_links.add(link)

    # Also check href attributes
    for m in re.finditer(r'href="(https?://(?:pan|yun)\.baidu\.com/s/[^"]+)"', html):
        link = m.group(1).rstrip('，。、！')
        baidu_links.add(link)

    # Aliyun links
    for m in re.finditer(r'(https?://(?:www\.)?(?:aliyundrive|alipan)\.com/s/[A-Za-z0-9]+)', html):
        ali_links.add(m.group(1))

    # Passwords - various patterns
    for m in re.finditer(r'(?:提取码|pwd|密码|关注|口令)[：:\s]*([A-Za-z0-9]{4})', html):
        passwords.add(m.group(1))
    for m in re.finditer(r'\?pwd=([A-Za-z0-9]{4})', html):
        passwords.add(m.group(1))

    # Title
    title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
    title = title_match.group(1).strip() if title_match else ""

    return {
        "title": title,
        "baidu_links": sorted(baidu_links),
        "passwords": sorted(passwords),
        "ali_links": sorted(ali_links),
    }


# ════════════════════════════════════════════════════════════════════
# CRAWL
# ════════════════════════════════════════════════════════════════════

def cmd_crawl(args):
    categories = CATEGORIES
    if args.limit:
        categories = categories[:args.limit]

    if args.dry_run:
        for name, path in categories:
            print(f"  {name:>20}  {BASE_URL}{path}")
        print(f"\nTotal: {len(categories)} categories × {POSTS_PER_CATEGORY} posts")
        return

    # Load existing results for resume
    results = []
    processed_urls = set()
    if args.resume and os.path.exists(CRAWLED_FILE):
        with open(CRAWLED_FILE, 'r') as f:
            results = json.load(f)
            processed_urls = {r['url'] for r in results}
        print(f"Resume: {len(results)} existing results")

    consecutive_failures = 0
    total_new = 0

    for cat_idx, (cat_name, cat_path) in enumerate(categories):
        print(f"\n{'='*60}")
        print(f"[{cat_idx+1}/{len(categories)}] {cat_name} — {BASE_URL}{cat_path}")
        print(f"{'='*60}")

        cat_urls = []

        # Collect post URLs from category pages
        pages_needed = (POSTS_PER_CATEGORY + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        for page in range(1, pages_needed + 1):
            page_url = f"{BASE_URL}{cat_path}page/{page}/" if page > 1 else f"{BASE_URL}{cat_path}"
            try:
                print(f"  Page {page}: {page_url}")
                resp = fetch(page_url)
                html = resp.read().decode('utf-8', errors='replace')
                post_urls = extract_post_urls(html)
                cat_urls.extend(post_urls)
                print(f"    Found {len(post_urls)} posts")
                consecutive_failures = 0
            except Exception as e:
                print(f"    Failed: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 10:
                    print("  Too many failures, pausing 60s...")
                    time.sleep(60)
                    consecutive_failures = 0
                break

            if len(cat_urls) >= POSTS_PER_CATEGORY:
                break

            time.sleep(random.uniform(3, 6))

        cat_urls = cat_urls[:POSTS_PER_CATEGORY]
        print(f"  Total post URLs to crawl: {len(cat_urls)}")

        # Crawl each post for download links
        cat_new = 0
        for post_idx, post_url in enumerate(cat_urls):
            if post_url in processed_urls:
                continue

            try:
                resp = fetch(post_url)
                html = resp.read().decode('utf-8', errors='replace')
                data = extract_download_links(html)
                data['url'] = post_url
                data['category'] = cat_name

                # Filter out software, tutorials, non-usable content
                skip = False
                for pat in EXCLUDE_PATTERNS:
                    if re.search(pat, data['title']):
                        skip = True
                        break

                if skip:
                    print(f"    [{post_idx+1}/{len(cat_urls)}] ⊘ {data['title'][:45]} (filtered)")
                    processed_urls.add(post_url)
                    continue

                if data['baidu_links'] or data['ali_links']:
                    results.append(data)
                    cat_new += 1
                    total_new += 1
                    pwd_str = ','.join(data['passwords']) if data['passwords'] else 'none'
                    print(f"    [{post_idx+1}/{len(cat_urls)}] ✓ {data['title'][:45]} (pwd={pwd_str})")

                processed_urls.add(post_url)
                consecutive_failures = 0
            except Exception as e:
                print(f"    [{post_idx+1}/{len(cat_urls)}] ✗ {post_url}: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 10:
                    print("  Too many failures, pausing 60s...")
                    time.sleep(60)
                    consecutive_failures = 0

            # Save progress every 10 posts
            if (post_idx + 1) % 10 == 0:
                _save_crawl_results(results)

            time.sleep(random.uniform(5, 8))

        print(f"  Category done: {cat_new} new resources with download links")

    _save_crawl_results(results)
    print(f"\n{'='*60}")
    print(f"Crawl complete! {total_new} new resources found")
    print(f"Total: {len(results)} resources in {CRAWLED_FILE}")


def _save_crawl_results(results):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CRAWLED_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


# ════════════════════════════════════════════════════════════════════
# SAVE (Chrome CDP)
# ════════════════════════════════════════════════════════════════════

_cdp_id = 0

def _cdp_eval(ws, js, await_promise=False, timeout=30):
    global _cdp_id
    _cdp_id += 1
    ws.send(json.dumps({"id": _cdp_id, "method": "Runtime.evaluate", "params": {
        "expression": js, "awaitPromise": await_promise, "returnByValue": True}}))
    ws.settimeout(timeout)
    resp = json.loads(ws.recv())
    return resp.get("result", {}).get("result", {}).get("value")


def _cdp_navigate(ws, url, wait=4):
    global _cdp_id
    _cdp_id += 1
    ws.send(json.dumps({"id": _cdp_id, "method": "Page.navigate", "params": {"url": url}}))
    ws.recv()
    time.sleep(wait)


def _cdp_type(ws, text):
    global _cdp_id
    for char in text:
        _cdp_id += 1
        ws.send(json.dumps({"id": _cdp_id, "method": "Input.dispatchKeyEvent",
                            "params": {"type": "char", "text": char}}))
        ws.recv()
        time.sleep(0.03)


def _setup_chrome():
    os.makedirs(f"{PROFILE_TMP}/Profile 7", exist_ok=True)
    for f in ["Cookies", "Login Data", "Preferences", "Secure Preferences", "Web Data"]:
        src = os.path.join(PROFILE_SRC, f)
        if os.path.exists(src):
            subprocess.run(["cp", "-c", src, f"{PROFILE_TMP}/Profile 7/{f}"], capture_output=True)
    local_state = os.path.expanduser("~/Library/Application Support/Google/Chrome/Local State")
    if os.path.exists(local_state):
        subprocess.run(["cp", "-c", local_state, f"{PROFILE_TMP}/Local State"], capture_output=True)


def _start_chrome(headful=False):
    import websocket as _ws  # ensure available
    cmd = [CHROME, f"--remote-debugging-port={CDP_PORT}", '--remote-allow-origins=*',
           f'--user-data-dir={PROFILE_TMP}', '--profile-directory=Profile 7',
           '--no-first-run', '--no-default-browser-check', '--disable-gpu', '--disable-extensions']
    if not headful:
        cmd.append('--headless=new')
    cmd.append('about:blank')
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(4)
    try:
        urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json/version", timeout=5)
        print(f"Chrome started ({'headful' if headful else 'headless'})")
        return proc
    except Exception:
        print("ERROR: Chrome CDP not accessible")
        proc.terminate()
        return None


def _get_page_ws():
    import websocket
    resp = urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json")
    targets = json.loads(resp.read())
    page = [t for t in targets if t.get("type") == "page"]
    if not page:
        return None
    return websocket.create_connection(page[0]["webSocketDebuggerUrl"], timeout=60)


def _save_one(ws, url, pwd):
    """Save a single share link. Returns (status, message)."""
    try:
        _cdp_navigate(ws, url, wait=4)
        current = _cdp_eval(ws, "document.location.href") or ""

        if "/share/init" in current:
            if not pwd:
                return ('failed', 'No password')
            input_ok = _cdp_eval(ws, """
                (() => {
                    const input = document.querySelector('input.QKKaIE, input[placeholder*="提取码"]');
                    if (!input) return 'no_input';
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, '');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    input.focus();
                    return 'ok';
                })()
            """)
            if input_ok != 'ok':
                return ('failed', 'No password input')

            _cdp_type(ws, pwd)
            time.sleep(0.3)
            _cdp_eval(ws, """
                (() => {
                    const btn = document.querySelector('.submit-btn-text');
                    if (btn) { btn.click(); return 'ok'; }
                    return 'no_btn';
                })()
            """)
            time.sleep(5)

            current = _cdp_eval(ws, "document.location.href") or ""
            if "/share/init" in current:
                body = _cdp_eval(ws, "document.body.innerText.substring(0, 300)") or ""
                if '错误' in body:
                    return ('failed', f'Wrong password: {pwd}')
                if '失效' in body or '删除' in body:
                    return ('failed', 'Link expired')
                return ('failed', 'Stuck on init page')

        # Click save
        click = _cdp_eval(ws, """
            (() => {
                if (typeof $ === 'undefined') return 'no_jquery';
                const $btn = $('[node-type="bottomShareSave"]');
                if ($btn.length) { $btn.click(); return 'clicked'; }
                return 'no_btn';
            })()
        """)
        if click != 'clicked':
            return ('failed', f'Save button: {click}')

        time.sleep(3)

        # Check result
        tips_text = _cdp_eval(ws, """
            (() => {
                const tips = [...document.querySelectorAll('[class*="tip-inner"], [class*="tip-msg"]')]
                    .map(t => t.textContent.trim()).filter(t => t.length > 0);
                return JSON.stringify(tips);
            })()
        """)
        if tips_text:
            try:
                for tip in json.loads(tips_text):
                    if '已有相同文件' in tip:
                        return ('skipped', 'Already exists')
                    if '保存成功' in tip or '成功' in tip:
                        return ('saved', tip)
            except json.JSONDecodeError:
                pass

        return ('saved', 'Save triggered')

    except Exception as e:
        return ('failed', str(e))


def cmd_save(args):
    import websocket  # ensure available

    # Load links
    links_file = CRAWLED_FILE if os.path.exists(CRAWLED_FILE) else os.path.join(DATA_DIR, "mfcpx_all_links.json")
    if not os.path.exists(links_file):
        print(f"No links file found. Run 'crawl' first.")
        return

    with open(links_file, 'r') as f:
        data = json.load(f)

    links = []
    seen = set()
    for item in data:
        bd = item.get('baidu_links', [])
        if not bd:
            continue
        url = bd[0].split('?')[0]
        if not url.startswith('http'):
            url = 'https://' + url
        if url in seen:
            continue
        seen.add(url)

        pwds = item.get('passwords', [])
        pwd = next((p for p in pwds if p), '')
        links.append({'title': item.get('title', ''), 'url': url, 'pwd': pwd})

    print(f"Loaded {len(links)} share links from {links_file}")

    if args.limit:
        links = links[:args.limit]
        print(f"Processing first {args.limit}")

    # Resume support
    prev = {}
    if args.resume and os.path.exists(SAVE_RESULTS_FILE):
        with open(SAVE_RESULTS_FILE, 'r') as f:
            for r in json.load(f):
                prev[r['url'] + r['pwd']] = r
        print(f"Resume: {len(prev)} previous results")

    # Start Chrome
    _setup_chrome()
    proc = _start_chrome(headful=args.headful)
    if not proc:
        return

    ws = _get_page_ws()
    if not ws:
        print("ERROR: Cannot connect to Chrome")
        proc.terminate()
        return

    # Check login
    quota_text = _cdp_eval(ws, """
        (async () => { const r = await fetch('/api/quota'); return r.text(); })()
    """, await_promise=True)
    if quota_text:
        qd = json.loads(quota_text) if isinstance(quota_text, str) else quota_text
        if qd.get('errno') != 0:
            print(f"Not logged in (errno={qd.get('errno')})")
            ws.close(); proc.terminate(); return
        used = qd['used'] / 1024**3
        total = qd['total'] / 1024**3
        print(f"Logged in: {used:.1f}GB / {total:.1f}GB")

    _cdp_navigate(ws, "https://pan.baidu.com/disk/main", wait=3)

    all_results = list(prev.values()) if args.resume else []
    saved = skipped = failed = 0

    for i, link in enumerate(links, 1):
        key = link['url'] + link['pwd']
        if args.resume and key in prev and prev[key].get('status') in ('saved', 'skipped'):
            continue

        print(f"\n[{i}/{len(links)}] {link['title'][:55]}")
        print(f"  {link['url']}  pwd={link['pwd'] or '(none)'}")

        status, msg = _save_one(ws, link['url'], link['pwd'])
        all_results.append({
            'title': link['title'], 'url': link['url'], 'pwd': link['pwd'],
            'status': status, 'message': msg, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })

        if status == 'saved': saved += 1
        elif status == 'skipped': skipped += 1
        else: failed += 1
        print(f"  -> {status.upper()}: {msg}")

        if i % 5 == 0:
            with open(SAVE_RESULTS_FILE, 'w') as f:
                json.dump(all_results, f, ensure_ascii=False, indent=2)
        time.sleep(2)

    with open(SAVE_RESULTS_FILE, 'w') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    ws.close()
    proc.terminate()
    proc.wait(timeout=10)
    print(f"\n{'='*60}")
    print(f"Save complete! Saved: {saved} | Skipped: {skipped} | Failed: {failed}")


# ════════════════════════════════════════════════════════════════════
# DOWNLOAD
# ════════════════════════════════════════════════════════════════════

def _get_token():
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)['access_token']


def _pcs_api(endpoint, token, params=None):
    url = f"https://pan.baidu.com{endpoint}?access_token={token}"
    if params:
        url += "&" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def _format_size(n):
    for u in ['B', 'KB', 'MB', 'GB']:
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def cmd_download(args):
    if not os.path.exists(TOKEN_FILE):
        print("No token file. Run OAuth flow first.")
        return

    token = _get_token()

    # Verify token
    qd = _pcs_api("/api/quota", token)
    if qd.get('errno') != 0:
        print(f"Token expired (errno={qd.get('errno')})")
        return
    used = qd['used'] / 1024**3
    total = qd['total'] / 1024**3
    print(f"Account: {used:.1f}GB / {total:.1f}GB used")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Load save results
    if not os.path.exists(SAVE_RESULTS_FILE):
        print("No save results. Run 'save' first.")
        return

    with open(SAVE_RESULTS_FILE, 'r') as f:
        results = json.load(f)

    saved_titles = [r['title'] for r in results if r.get('status') in ('saved', 'skipped')]
    if not saved_titles:
        print("No saved resources found in results.")
        return

    print(f"Looking for {len(saved_titles)} resources...")

    downloaded = 0
    failed = 0

    for title in saved_titles:
        # Extract search keyword
        keywords = re.findall(r'[A-Za-z][A-Za-z0-9_ ]{3,}', title)
        keyword = keywords[0].strip() if keywords else title[:15]

        print(f"\nSearching: {keyword}")
        try:
            data = _pcs_api("/rest/2.0/xpan/file", token, {
                "method": "search", "dir": "/", "key": keyword,
                "rec": 1, "num": 5, "page": 1, "order": "time"
            })
        except Exception as e:
            print(f"  Search failed: {e}")
            continue

        files = [f for f in data.get('list', []) if f.get('isdir') != 1]
        if not files:
            print(f"  No files found")
            failed += 1
            continue

        for f in files[:1]:
            name = f['server_filename']
            size = _format_size(f['size'])
            path = f['path']
            fs_id = f.get('fs_id', 0)

            print(f"  Found: {name} ({size})")

            # Get download link
            try:
                meta = _pcs_api("/api/filemetas", token, {
                    "fsids": json.dumps([fs_id]), "dlink": 1
                })
                dlink = None
                for item in meta.get('info', [] if 'info' in meta else meta.get('list', [])):
                    if item.get('dlink'):
                        dlink = item['dlink']
                        break

                if not dlink:
                    # Try alternative method
                    meta2 = _pcs_api("/rest/2.0/pcs/file", token, {
                        "method": "filemetas", "fsids": json.dumps([fs_id]), "dlink": 1
                    })
                    for item in meta2.get('response', []):
                        if item.get('download'):
                            dlink = item['download']
                            break
            except Exception as e:
                print(f"  Get download URL failed: {e}")
                failed += 1
                continue

            if not dlink:
                print(f"  No download URL available")
                failed += 1
                continue

            dl_url = f"{dlink}&access_token={token}"
            out_path = os.path.join(DOWNLOAD_DIR, os.path.basename(name))

            if os.path.exists(out_path):
                print(f"  Already downloaded, skipping")
                downloaded += 1
                continue

            # Download with aria2c or curl
            if os.path.exists("/opt/homebrew/bin/aria2c"):
                cmd = ["aria2c", "--max-connection-per-server=16", "--split=16",
                       "--continue=true", f"--dir={DOWNLOAD_DIR}",
                       f"--out={os.path.basename(name)}",
                       "-H", "User-Agent: Mozilla/5.0", dl_url]
            else:
                cmd = ["curl", "-L", "-o", out_path, "-H", "User-Agent: Mozilla/5.0", dl_url]

            print(f"  Downloading to {out_path}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                downloaded += 1
                print(f"  ✓ Downloaded")
            else:
                failed += 1
                print(f"  ✗ Download failed: {result.stderr[:100] if result.stderr else 'unknown'}")

        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"Download complete! Downloaded: {downloaded} | Failed: {failed}")
    print(f"Files saved to: {DOWNLOAD_DIR}")


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='mfcpx.com FCPX Resource Pipeline')
    sub = parser.add_subparsers(dest='command')

    # crawl
    p_crawl = sub.add_parser('crawl', help='Crawl resource links from mfcpx.com')
    p_crawl.add_argument('--limit', type=int, default=0, help='Limit categories to crawl')
    p_crawl.add_argument('--dry-run', action='store_true', help='Preview categories')
    p_crawl.add_argument('--resume', action='store_true', help='Skip already crawled URLs')

    # save
    p_save = sub.add_parser('save', help='Save shared files to Baidu Pan')
    p_save.add_argument('--headful', action='store_true', help='Run Chrome visible')
    p_save.add_argument('--limit', type=int, default=0, help='Limit links to process')
    p_save.add_argument('--resume', action='store_true', help='Skip completed links')

    # download
    p_dl = sub.add_parser('download', help='Download files from Baidu Pan')

    # all
    p_all = sub.add_parser('all', help='Run full pipeline (crawl + save)')
    p_all.add_argument('--headful', action='store_true', help='Run Chrome visible')
    p_all.add_argument('--limit-categories', type=int, default=0, help='Limit categories')
    p_all.add_argument('--limit-save', type=int, default=0, help='Limit links to save')

    args = parser.parse_args()

    if args.command == 'crawl':
        cmd_crawl(args)
    elif args.command == 'save':
        cmd_save(args)
    elif args.command == 'download':
        cmd_download(args)
    elif args.command == 'all':
        print("=" * 60)
        print("  mfcpx.com FCPX Resource Pipeline")
        print("=" * 60)
        print("\n[1/3] Crawling resource links...")
        cmd_crawl(argparse.Namespace(limit=args.limit_categories, dry_run=False, resume=True))
        print("\n[2/3] Saving to Baidu Pan...")
        cmd_save(argparse.Namespace(headful=args.headful, limit=args.limit_save, resume=True))
        print("\n[3/3] To download files, run:")
        print(f"  python3 {__file__} download")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
