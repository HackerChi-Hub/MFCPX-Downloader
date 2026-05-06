#!/usr/bin/env python3
"""
Download FCPX plugins via Alist + aria2c.
Supports AliyundriveShare and BaiduShare drivers.
"""
import json
import os
import subprocess
import sys
import time
import argparse
import urllib.request
import urllib.error
import random

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CRAWLED_FILE = os.path.join(PROJECT_DIR, "mfcpx_crawled.json")
DOWNLOAD_DIR = "/Volumes/BigDisk/Download/FCPX-Plugins"

ALIST_URL = "http://localhost:5244"
ALIST_USER = "admin"
ALIST_PASS = "alist123"


def alist_api(endpoint, token, method="GET", data=None):
    url = f"{ALIST_URL}{endpoint}"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def get_token():
    d = alist_api("/api/auth/login", "", "POST", {"username": ALIST_USER, "password": ALIST_PASS})
    if d.get("code") != 200:
        print(f"Login failed: {d.get('message')}")
        sys.exit(1)
    return d["data"]["token"]


def get_existing_auth(token):
    """Extract BDUSS from existing working BaiduShare mount."""
    d = alist_api("/api/admin/storage/list", token)
    auth = {}
    for s in d.get("data", {}).get("content", []):
        if s.get("status") == "work":
            add = json.loads(s.get("addition", "{}"))
            if s["driver"] == "BaiduShare" and add.get("BDUSS"):
                auth["BDUSS"] = add["BDUSS"]
    return auth


def create_mount(token, driver, share_url, password, mount_path, auth=None):
    """Create a share mount in Alist with auth tokens."""
    if driver == "BaiduShare":
        surl = share_url.split("/s/")[-1] if "/s/" in share_url else share_url.split("/")[-1]
        bduss = (auth or {}).get("BDUSS", "")
        # Addition must be JSON string for Alist API
        addition = json.dumps({
            "root_folder_path": "/",
            "surl": surl,
            "pwd": password or "",
            "BDUSS": bduss,
        })
        print(f"    [DEBUG] BDUSS length: {len(bduss)}")
    else:
        addition = json.dumps({"root_url": share_url, "password": password or ""})

    data = {
        "mount_path": mount_path,
        "order": 0,
        "remark": "",
        "cache_expiration": 0,
        "enable_sign": False,
        "order_by": "name",
        "order_dir": "asc",
        "extract_folder": "",
        "web_proxy": False,
        "webdav_policy": "native_proxy",
        "down_proxy_url": "",
        "driver": driver,
        "order_by_nav": "",
        "reverse_order_nav": False,
        "addition": addition,  # JSON string
    }

    # Use urllib.request for proper JSON encoding
    req = urllib.request.Request(
        f"{ALIST_URL}/api/admin/storage/create",
        data=json.dumps(data).encode(),
        headers={"Authorization": token, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())
        if result.get("code") != 200:
            print(f"    [DEBUG] Create failed: {result.get('message')}")
        else:
            print(f"    [DEBUG] Created mount id={result.get('data',{}).get('id','?')}")
        return result
    except urllib.error.HTTPError as e:
        print(f"    [DEBUG] HTTP error: {e.code}")
        return {"code": e.code, "message": str(e)}
    except Exception as e:
        print(f"    [DEBUG] Error: {e}")
        return {"code": 500, "message": str(e)}


def delete_mount(token, mount_path):
    """Delete mount by path using urllib.request."""
    # List all mounts
    req = urllib.request.Request(
        f"{ALIST_URL}/api/admin/storage/list",
        headers={"Authorization": token}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    d = json.loads(resp.read())

    for s in d.get("data", {}).get("content", []):
        if s["mount_path"] == mount_path:
            # Delete by ID
            req = urllib.request.Request(
                f"{ALIST_URL}/api/admin/storage/delete",
                data=json.dumps({"id": s["id"]}).encode(),
                headers={"Authorization": token, "Content-Type": "application/json"},
                method="POST"
            )
            urllib.request.urlopen(req, timeout=30)
            return
    # Not found, that's OK


def list_files(token, path):
    d = alist_api("/api/fs/list", token, "POST", {"path": path, "page": 1, "per_page": 200, "refresh": True})
    if d.get("code") != 200:
        return []
    return d.get("data", {}).get("content", [])


def get_download_url(token, path):
    d = alist_api("/api/fs/get", token, "POST", {"path": path})
    if d.get("code") != 200:
        return None, 0
    info = d.get("data", {})
    return info.get("raw_url") or info.get("url"), info.get("size", 0)


def curl_download(url, output_path):
    cmd = ["curl", "-L", "--fail", "--continue-at", "-",
           "--max-time", "600", "--retry", "3", "--retry-delay", "5",
           "-H", "User-Agent: Mozilla/5.0",
           "-o", output_path, url]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=700)


def try_mount(token, driver, share_url, passwords, mount_path, auth=None):
    """Try mounting with each password. Returns True if files found."""
    tried = list(set(passwords)) if passwords else [""]
    for pwd in tried:
        delete_mount(token, mount_path)
        time.sleep(1)
        create_mount(token, driver, share_url, pwd, mount_path, auth)
        time.sleep(10)  # BaiduShare needs more time to initialize
        files = list_files(token, mount_path)
        if files:
            return True
        print(f"    pwd={pwd or '(none)'} -> no files")
    return False


def collect_all_files(token, path, prefix=""):
    """Recursively collect all files from a mount."""
    items = list_files(token, path)
    files = []
    for item in (items or []):
        item_path = f"{path}/{item['name']}"
        if item.get("is_dir"):
            files.extend(collect_all_files(token, item_path, f"{prefix}{item['name']}/"))
        else:
            item["rel_path"] = f"{prefix}{item['name']}"
            item["full_path"] = item_path
            files.append(item)
    return files


def main():
    parser = argparse.ArgumentParser(description="Download FCPX plugins via Alist")
    parser.add_argument("--limit", type=int, default=0, help="Limit plugins")
    parser.add_argument("--start", type=int, default=0, help="Start from index")
    parser.add_argument("--driver", choices=["ali", "baidu", "auto"], default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not os.path.exists(CRAWLED_FILE):
        print(f"No crawled data: {CRAWLED_FILE}")
        sys.exit(1)

    with open(CRAWLED_FILE) as f:
        plugins = json.load(f)

    token = get_token()
    auth = get_existing_auth(token)
    print(f"Loaded {len(plugins)} plugins, logged in to Alist")
    if auth.get("BDUSS"):
        print(f"Found BDUSS ({len(auth['BDUSS'])} chars)")
    else:
        print("WARNING: No BDUSS found, BaiduShare will likely fail")

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    results_file = os.path.join(PROJECT_DIR, "download_results.json")
    if os.path.exists(results_file):
        with open(results_file) as f:
            results = json.load(f)
        done_titles = {r["title"] for r in results if r.get("status") in ("downloaded", "skipped")}
        print(f"Resume: {len(done_titles)} already done")
    else:
        results = []
        done_titles = set()

    downloaded = skipped = failed = 0
    plugins = plugins[args.start:]
    if args.limit:
        plugins = plugins[:args.limit]

    for i, plugin in enumerate(plugins, 1):
        title = plugin["title"]
        if title in done_titles:
            continue

        ali_links = plugin.get("ali_links", [])
        baidu_links = plugin.get("baidu_links", [])
        passwords = plugin.get("passwords", [])
        category = plugin.get("category", "other")

        # Pick driver: prefer ali, fallback baidu
        if args.driver == "ali" and not ali_links:
            print(f"\n[{i}/{len(plugins)}] SKIP (no ali link): {title[:60]}")
            continue
        if args.driver == "baidu" and not baidu_links:
            print(f"\n[{i}/{len(plugins)}] SKIP (no baidu link): {title[:60]}")
            continue

        use_ali = ali_links and args.driver in ("ali", "auto")
        use_baidu = baidu_links and not use_ali

        mount_path = f"/fcpx_dl_{i}_{random.randint(10000, 99999)}"
        cat_dir = os.path.join(DOWNLOAD_DIR, category)
        os.makedirs(cat_dir, exist_ok=True)

        print(f"\n[{i}/{len(plugins)}] {title[:60]}")

        if args.dry_run:
            driver = "AliyundriveShare" if use_ali else "BaiduShare"
            url = ali_links[0] if use_ali else baidu_links[0]
            print(f"  Driver: {driver}  URL: {url}")
            continue

        mount_ok = False

        # Try Ali first
        if use_ali:
            print(f"  Trying AliyundriveShare: {ali_links[0]}")
            mount_ok = try_mount(token, "AliyundriveShare", ali_links[0], [""], mount_path, auth)
            if not mount_ok:
                print(f"  Ali failed")

        # Fallback to Baidu
        if not mount_ok and baidu_links:
            share_url = baidu_links[0].split("?")[0]
            print(f"  Trying BaiduShare: {share_url}")
            mount_ok = try_mount(token, "BaiduShare", share_url, passwords, mount_path, auth)
            if not mount_ok:
                print(f"  Baidu failed")

        if not mount_ok:
            print(f"  ALL FAILED")
            delete_mount(token, mount_path)
            failed += 1
            results.append({"title": title, "status": "failed", "error": "mount failed", "category": category})
            continue

        # Collect all files recursively
        all_files = collect_all_files(token, mount_path)
        print(f"  Found {len(all_files)} file(s)")

        if not all_files:
            delete_mount(token, mount_path)
            failed += 1
            results.append({"title": title, "status": "failed", "error": "no files", "category": category})
            continue

        for f in all_files:
            fname = f["name"]
            fsize = f.get("size", 0)
            out_path = os.path.join(cat_dir, f["rel_path"])

            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                print(f"    SKIP (exists): {f['rel_path']}")
                skipped += 1
                continue

            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            print(f"    GET: {f['rel_path']} ({fsize/1024/1024:.1f}MB)")

            dl_url, _ = get_download_url(token, f["full_path"])
            if not dl_url:
                print(f"    NO URL")
                failed += 1
                continue

            cr = curl_download(dl_url, out_path)
            if cr.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                downloaded += 1
                print(f"    OK")
            else:
                err = cr.stderr[:80] if cr.stderr else "unknown"
                print(f"    FAILED: {err}")
                failed += 1

            time.sleep(1)

        delete_mount(token, mount_path)
        results.append({"title": title, "status": "downloaded", "category": category})
        time.sleep(2)

        if i % 5 == 0:
            with open(results_file, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open(results_file, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Done! Downloaded: {downloaded} | Skipped: {skipped} | Failed: {failed}")
    print(f"Files in: {DOWNLOAD_DIR}")


if __name__ == "__main__":
    main()
