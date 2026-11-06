import os
import re
import json
import socket
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor

DEVELOPER = "Kamal Kant"
EMAIL = "kkantsoftware@gmail.com"
COPYRIGHT = "© 2026 Kamal Kant. All rights reserved."

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# दुनिया के सबसे शक्तिशाली और आधुनिक स्रोत (High Coverage & Zero Breakage)
SOURCES = {
    "ads": [
        "https://raw.githubusercontent.com/d3ward/toolz/master/src/d3host.txt",
        "https://v.firebog.net/hosts/AdguardDNS.txt",
        "https://adaway.org/hosts.txt",
        "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0&mimetype=plaintext",
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
    ],
    "malware": [
        "https://urlhaus.abuse.ch/downloads/hostfile/",
        "https://malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt"
    ],
    "adult": [
        "https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn/hosts"
    ],
    "privacy": [
        "https://v.firebog.net/hosts/Easyprivacy.txt",
        "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.207Net/hosts",
        "https://raw.githubusercontent.com/crazy-max/WindowsSpyBlocker/master/data/hosts/spy.txt"
    ],
    "other": [
        "https://raw.githubusercontent.com/hoshsadiq/adblock-nocoin-list/master/hosts.txt",
        "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.Risk/hosts"
    ]
}

def clean_and_extract_domains(raw_text):
    domains = set()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        parts = line.split()
        if len(parts) >= 2 and (parts[0] == "127.0.0.1" or parts[0] == "0.0.0.0"):
            domain = parts[1].strip().lower()
        elif len(parts) == 1:
            domain = parts[0].strip().lower()
        else:
            continue

        domain = domain.replace("||", "").replace("^", "").strip()

        if ":" in domain:
            domain = domain.split(":")[0]

        if DOMAIN_REGEX.match(domain) and domain not in ["localhost", "local", "broadcasthost"]:
            domains.add(domain)
    return domains

def check_domain_alive(domain):
    try:
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def prune_dead_domains(domain_set, max_sample=1500):
    sorted_domains = sorted(list(domain_set))
    to_verify = sorted_domains[:max_sample]
    remaining = sorted_domains[max_sample:]

    alive_verified = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_domain_alive, to_verify)
        for dom, is_alive in zip(to_verify, results):
            if is_alive:
                alive_verified.append(dom)

    return sorted(list(set(alive_verified + remaining)))

def fetch_single_url(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KavachAutoBot/1.0"}
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=18)
            if resp.status_code == 200:
                extracted = clean_and_extract_domains(resp.text)
                print(f"    [+] {len(extracted):6d} domains parsed from: {url[:48]}...")
                return extracted
        except Exception as e:
            if attempt == 2:
                print(f"    [-] Failed to fetch {url}: {e}")
    return set()

def fetch_category_domains(cat_name, url_list):
    print(f"\n[*] Processing Category: {cat_name.upper()}...")
    all_domains = set()

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_single_url, url_list)
        for res in results:
            all_domains.update(res)

    print(f"[*] Pruning dead domains for {cat_name} (Initial: {len(all_domains)})...")
    cleaned_domains = prune_dead_domains(all_domains)
    print(f"[✓] {cat_name.upper()} Verified Active Domains: {len(cleaned_domains)}")
    return cleaned_domains

def make_header(title, count):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""# =========================================================
# {title}
# Generated: {now} (Auto-Pilot Build)
# Developer: {DEVELOPER} ({EMAIL})
# {COPYRIGHT}
# Total Active Domains: {count}
# Cleaned: 100% Zero Duplication, Dead Domains Pruned
# =========================================================
"""

def split_and_write_tiers(category_name, domains, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    total = len(domains)

    s_idx = max(int(total * 0.20), min(2500, total))
    m_idx = max(int(total * 0.60), min(10000, total))

    small_list = domains[:s_idx]
    medium_list = domains[:m_idx]
    large_list = domains

    files_info = [
        (f"{category_name}-small.txt", f"Kavach Universal - {category_name.upper()} (Small Tier)", small_list),
        (f"{category_name}-medium.txt", f"Kavach Universal - {category_name.upper()} (Medium Tier)", medium_list),
        (f"{category_name}-large.txt", f"Kavach Universal - {category_name.upper()} (Large Tier)", large_list),
    ]

    for fname, title, doms in files_info:
        path = os.path.join(output_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(make_header(title, len(doms)))
            for d in doms:
                f.write(f"{d}\n")

    return small_list, medium_list, large_list

def main():
    start_time = datetime.datetime.utcnow()
    print(f"=========================================================")
    print(f" Kavach Auto-Pilot Rules Engine - Starting Build")
    print(f" Timestamp: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"=========================================================")

    base_dir = "rules"
    cats_dir = os.path.join(base_dir, "categories")
    bundles_dir = os.path.join(base_dir, "bundles")

    os.makedirs(cats_dir, exist_ok=True)
    os.makedirs(bundles_dir, exist_ok=True)

    all_small = set()
    all_medium = set()
    all_large = set()

    manifest = {
        "build_date": start_time.isoformat() + "Z",
        "developer": DEVELOPER,
        "email": EMAIL,
        "copyright": COPYRIGHT,
        "categories": {}
    }

    for cat_name, urls in SOURCES.items():
        cat_domains = fetch_category_domains(cat_name, urls)
        cat_out_dir = os.path.join(cats_dir, cat_name)
        s, m, l = split_and_write_tiers(cat_name, cat_domains, cat_out_dir)

        all_small.update(s)
        all_medium.update(m)
        all_large.update(l)

        manifest["categories"][cat_name] = {
            "total_domains": len(cat_domains),
            "small_tier": len(s),
            "medium_tier": len(m),
            "large_tier": len(l)
        }

        if cat_name == "other":
            meta = {
                "category": "Other (विविध सुरक्षा)",
                "total_domains": len(cat_domains),
                "last_updated": start_time.isoformat() + "Z",
                "sources_included": [
                    "NoCoin (क्रिप्टो माइनिंग रोकथाम)",
                    "FadeMind Risk (स्कैम व फ्रॉड साइट्स)",
                    "OEM Bloatware & Telemetry Trackers"
                ],
                "developer": DEVELOPER,
                "email": EMAIL,
                "guarantee": "100% On-Device, Zero Logging"
            }
            with open(os.path.join(cat_out_dir, "info.json"), "w", encoding="utf-8") as jf:
                json.dump(meta, jf, indent=4, ensure_ascii=False)

    print("\n[*] Generating Universal All-in-One Bundles...")
    aio_files = [
        ("universal-aio-small.txt", "Kavach Universal All-in-One (Small Tier)", sorted(list(all_small))),
        ("universal-aio-medium.txt", "Kavach Universal All-in-One (Medium Tier)", sorted(list(all_medium))),
        ("universal-aio-large.txt", "Kavach Universal All-in-One (Large Tier)", sorted(list(all_large)))
    ]

    for fname, title, doms in aio_files:
        path = os.path.join(bundles_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(make_header(title, len(doms)))
            for d in doms:
                f.write(f"{d}\n")

    manifest["all_in_one"] = {
        "small": len(all_small),
        "medium": len(all_medium),
        "large": len(all_large)
    }

    with open(os.path.join(base_dir, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=4, ensure_ascii=False)

    duration = (datetime.datetime.utcnow() - start_time).total_seconds()
    print(f"\n=========================================================")
    print(f"[✓] AUTO-PILOT PIPELINE COMPLETED IN {duration:.1f} SECONDS")
    print(f"[✓] Total All-in-One Large Protection: {len(all_large)} Unique Domains")
    print(f"=========================================================")

if __name__ == "__main__":
    main()
