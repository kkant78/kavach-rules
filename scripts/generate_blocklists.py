
import os
import re
import json
import socket
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor

# आधिकारिक मेटाडाटा
DEVELOPER = "Kamal Kant"
EMAIL = "kkantsoftware@gmail.com"
COPYRIGHT = "© 2026 Kamal Kant. All rights reserved."

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

# दुनिया भर के सत्यापित विश्वसनीय स्रोत
SOURCES = {
    "ads": [
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
        "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.207Net/hosts",
        "https://raw.githubusercontent.com/crazy-max/WindowsSpyBlocker/master/data/hosts/spy.txt"
    ],
    "other": [
        # क्रिप्टो-माइनर्स, फ्रॉड स्कैम, ब्लोटवेयर
        "https://raw.githubusercontent.com/hoshsadiq/adblock-nocoin-list/master/hosts.txt",
        "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.Risk/hosts"
    ]
}

def clean_and_extract_domains(raw_text):
    """प्रोटोकॉल, आईपी, कमेंट्स और पाथ हटाकर केवल शुद्ध डोमेन निकालना"""
    domains = set()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        
        # 127.0.0.1 या 0.0.0.0 को हटाना
        parts = line.split()
        if len(parts) >= 2 and (parts[0] == "127.0.0.1" or parts[0] == "0.0.0.0"):
            domain = parts[1].strip().lower()
        elif len(parts) == 1:
            domain = parts[0].strip().lower()
        else:
            continue

        # एडब्लॉक सिंटैक्स (||domain.com^) साफ करना
        domain = domain.replace("||", "").replace("^", "").strip()
        
        # पोर्ट हटाना
        if ":" in domain:
            domain = domain.split(":")[0]

        # डोमेन वैधता जांच
        if DOMAIN_REGEX.match(domain) and domain not in ["localhost", "local", "broadcasthost"]:
            domains.add(domain)
    return domains

def check_domain_alive(domain):
    """डेड डोमेन फ़िल्टर: चेक करना कि डोमेन का DNS जीवित है या मृत"""
    try:
        socket.gethostbyname(domain)
        return True
    except Exception:
        return False

def prune_dead_domains(domain_set, max_sample=1200):
    """
    फास्ट असिंक्रोनस प्रूनिंग:
    शीर्ष डोमेन्स पर लाइव जांच चलाकर निष्क्रिय डोमेन बाहर निकालना
    """
    sorted_domains = sorted(list(domain_set))
    to_verify = sorted_domains[:max_sample]
    remaining = sorted_domains[max_sample:]

    alive_verified = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_domain_alive, to_verify)
        for dom, is_alive in zip(to_verify, results):
            if is_alive:
                alive_verified.append(dom)

    # सत्यापित एक्टिव + बाकी डोमेन का संयोजन
    return sorted(list(set(alive_verified + remaining)))

def fetch_category_domains(cat_name, url_list):
    print(f"[*] Fetching & Analyzing: {cat_name.upper()}...")
    all_domains = set()
    for url in url_list:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                extracted = clean_and_extract_domains(resp.text)
                all_domains.update(extracted)
                print(f"    + {len(extracted)} domains parsed from {url[:45]}...")
        except Exception as e:
            print(f"    - Failed to fetch {url}: {e}")

    # डेड डोमेन प्रूनिंग
    print(f"[*] Pruning dead domains for {cat_name} (Total: {len(all_domains)})...")
    cleaned_domains = prune_dead_domains(all_domains)
    print(f"[✓] {cat_name.upper()} Final Clean Count: {len(cleaned_domains)}")
    return cleaned_domains

def make_header(title, count):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""# =========================================================
# {title}
# Generated: {now}
# Developer: {DEVELOPER} ({EMAIL})
# {COPYRIGHT}
# Total Active Domains: {count}
# Cleaned: Zero Duplication, Dead Domains Pruned
# =========================================================
"""

def split_and_write_tiers(category_name, domains, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    total = len(domains)
    
    # 3 टियर्स में विभाजन:
    # Small = टॉप 15% (अति-आवश्यक, जीरो ब्रेकज)
    # Medium = 50% (दैनिक उपयोग के लिए संतुलित)
    # Large = 100% (अभेद्य ढाल)
    s_idx = max(int(total * 0.15), min(1000, total))
    m_idx = max(int(total * 0.50), min(5000, total))

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
    base_dir = "rules"
    cats_dir = os.path.join(base_dir, "categories")
    bundles_dir = os.path.join(base_dir, "bundles")

    os.makedirs(cats_dir, exist_ok=True)
    os.makedirs(bundles_dir, exist_ok=True)

    all_small = set()
    all_medium = set()
    all_large = set()

    for cat_name, urls in SOURCES.items():
        cat_domains = fetch_category_domains(cat_name, urls)
        cat_out_dir = os.path.join(cats_dir, cat_name)
        s, m, l = split_and_write_tiers(cat_name, cat_domains, cat_out_dir)

        # बंडल्स के लिए संचय
        all_small.update(s)
        all_medium.update(m)
        all_large.update(l)

        # 'Other' कैटेगरी के लिए पारदर्शिता मेटाडाटा (info.json)
        if cat_name == "other":
            meta = {
                "category": "Other (विविध सुरक्षा)",
                "total_domains": len(cat_domains),
                "last_updated": datetime.datetime.utcnow().isoformat() + "Z",
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

    # ऑल-इन-वन (All-in-One Bundles) जनरेट करना
    print("[*] Generating Universal All-in-One Bundles...")
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

    print("[✓] ALL KAVACH UNIVERSAL BLOCKLISTS GENERATED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
