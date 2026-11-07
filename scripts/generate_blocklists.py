#!/usr/bin/env python3
"""Kavach Rules Engine v2 - श्रेणी (group) -> उप-श्रेणी (sub) आधारित ब्लॉकलिस्ट जनरेटर.

आउटपुट:  rules/<group>/<sub>.txt.gz            (छोटी सूची: एक ही फ़ाइल)
          rules/<group>/<sub>-small|medium|large.txt.gz   (बड़ी सूची: तीन टियर)
          rules/manifest.json                    (ऐप इसी से श्रेणियाँ/लेबल/फ़ाइलें/sha256 पढ़ेगा)
नई श्रेणी जोड़ने के लिए सिर्फ़ नीचे GROUPS में एक एंट्री जोड़ें - ऐप अपडेट की ज़रूरत नहीं।
"""
import os, re, json, gzip, shutil, hashlib, time, datetime
import requests
from concurrent.futures import ThreadPoolExecutor

DEVELOPER = "Kamal Kant"
EMAIL = "kkantsoftware@gmail.com"
COPYRIGHT = "© 2026 Kamal Kant. All rights reserved."

RULES_DIR = "rules"
DEFAULT_TIER = "medium"
TIER_THRESHOLD = 20000      # इससे छोटी सूची के टियर नहीं बनते (एक ही फ़ाइल)
DEFAULT_CAP = 250000        # एक उप-श्रेणी में अधिकतम डोमेन (फ़ोन की मेमोरी व रिपॉज़िटरी का आकार)
WRITE_PLAIN = os.environ.get("WRITE_PLAIN") == "1"   # .txt भी चाहिए तो WRITE_PLAIN=1

BLP = "https://blocklistproject.github.io/Lists/alt-version/{}-nl.txt"
SB = "https://raw.githubusercontent.com/StevenBlack/hosts/master/"

def blp(name): return BLP.format(name)

# default=True -> ऐप पहली बार में इसे चालू रखे; बाकी यूज़र खुद चुनेगा
GROUPS = [
 {"id": "ads", "hi": "विज्ञापन", "en": "Ads", "subs": [
   {"id": "general", "hi": "सामान्य विज्ञापन", "en": "General ads", "default": True, "urls": [
     "https://raw.githubusercontent.com/d3ward/toolz/master/src/d3host.txt",
     "https://v.firebog.net/hosts/AdguardDNS.txt",
     "https://adaway.org/hosts.txt",
     "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=0&mimetype=plaintext",
     SB + "hosts", blp("ads")],
    "seeds": ["googleads.g.doubleclick.net", "pagead2.googlesyndication.com", "adservice.google.com",
              "ads.facebook.com", "an.facebook.com", "unityads.unity3d.com", "applovin.com", "vungle.com",
              "ironsource.com", "admob.com", "ads.google.com", "ads.yahoo.com", "ads.twitter.com",
              "ads.tiktok.com", "adcolony.com", "chartboost.com", "inmobi.com"]},
   {"id": "redirect", "hi": "रीडायरेक्ट/ट्रैकिंग लिंक", "en": "Redirect links", "default": False, "urls": [blp("redirect")]},
 ]},
 {"id": "malware", "hi": "मैलवेयर व ख़तरे", "en": "Malware & threats", "subs": [
   {"id": "malware", "hi": "मैलवेयर", "en": "Malware", "default": True,
    "urls": ["https://urlhaus.abuse.ch/downloads/hostfile/"]},
   {"id": "phishing", "hi": "फ़िशिंग (नकली साइट)", "en": "Phishing", "default": True, "urls": [
     "https://malware-filter.gitlab.io/malware-filter/phishing-filter-hosts.txt", blp("phishing")]},
   {"id": "ransomware", "hi": "रैनसमवेयर", "en": "Ransomware", "default": True, "urls": [blp("ransomware")]},
   {"id": "scam", "hi": "स्कैम / ठगी", "en": "Scams", "default": True, "urls": [
     blp("scam"), "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.Risk/hosts"]},
   {"id": "fraud", "hi": "फ्रॉड साइट्स", "en": "Fraud sites", "default": False, "urls": [blp("fraud")]},
 ]},
 {"id": "privacy", "hi": "प्राइवेसी", "en": "Privacy", "subs": [
   {"id": "trackers", "hi": "ट्रैकर / एनालिटिक्स", "en": "Trackers", "default": True, "urls": [
     "https://v.firebog.net/hosts/Easyprivacy.txt",
     "https://raw.githubusercontent.com/FadeMind/hosts.extras/master/add.207Net/hosts", blp("tracking")],
    "seeds": ["analytics.google.com", "app-measurement.com", "graph.facebook.com", "crashlytics.com"]},
   {"id": "telemetry", "hi": "विंडोज़/स्मार्ट-टीवी टेलीमेट्री", "en": "OS & Smart-TV telemetry", "default": False, "urls": [
     "https://raw.githubusercontent.com/crazy-max/WindowsSpyBlocker/master/data/hosts/spy.txt", blp("smart-tv")]},
 ]},
 {"id": "crypto", "hi": "क्रिप्टो", "en": "Crypto", "subs": [
   {"id": "cryptojacking", "hi": "क्रिप्टो-माइनिंग (चोरी से)", "en": "Cryptojacking", "default": True, "urls": [
     "https://raw.githubusercontent.com/hoshsadiq/adblock-nocoin-list/master/hosts.txt"]},
   {"id": "crypto-sites", "hi": "क्रिप्टो साइट्स (एक्सचेंज आदि)", "en": "Crypto sites", "default": False, "urls": [blp("crypto")]},
 ]},
 {"id": "adult", "hi": "वयस्क सामग्री", "en": "Adult", "subs": [
   {"id": "porn", "hi": "पोर्न साइट्स", "en": "Adult sites", "default": False, "cap": 300000, "urls": [
     SB + "alternates/porn/hosts", blp("porn")]},
 ]},
 {"id": "gambling", "hi": "जुआ / सट्टा", "en": "Gambling", "subs": [
   {"id": "gambling", "hi": "जुआ व सट्टेबाज़ी साइट्स", "en": "Gambling & betting", "default": False, "urls": [
     SB + "alternates/gambling/hosts", blp("gambling")]},
 ]},
 {"id": "social", "hi": "सोशल मीडिया", "en": "Social media", "subs": [
   {"id": "facebook", "hi": "फ़ेसबुक / मेटा", "en": "Facebook / Meta", "default": False, "urls": [blp("facebook")]},
   {"id": "tiktok", "hi": "टिकटॉक", "en": "TikTok", "default": False, "urls": [blp("tiktok")]},
   {"id": "twitter", "hi": "ट्विटर / X", "en": "Twitter / X", "default": False, "urls": [blp("twitter")]},
   {"id": "whatsapp", "hi": "व्हाट्सऐप", "en": "WhatsApp", "default": False, "urls": [blp("whatsapp")]},
   {"id": "youtube", "hi": "यूट्यूब", "en": "YouTube", "default": False, "urls": [blp("youtube")]},
 ]},
 {"id": "drugs", "hi": "नशा", "en": "Drugs", "subs": [
   {"id": "drugs", "hi": "नशीले पदार्थ बेचने वाली साइट्स", "en": "Illegal drug sites", "default": False, "urls": [blp("drugs")]},
   {"id": "vaping", "hi": "वेपिंग / ई-सिगरेट", "en": "Vaping", "default": False, "urls": [blp("vaping")]},
 ]},
 {"id": "piracy", "hi": "पाइरेसी", "en": "Piracy", "subs": [
   {"id": "piracy", "hi": "पाइरेटेड डाउनलोड", "en": "Piracy", "default": False, "urls": [blp("piracy")]},
   {"id": "torrent", "hi": "टोरेंट", "en": "Torrent", "default": False, "urls": [blp("torrent")]},
 ]},
 {"id": "fakenews", "hi": "फ़र्ज़ी ख़बरें", "en": "Fake news", "subs": [
   {"id": "fakenews", "hi": "फ़र्ज़ी ख़बरों वाली साइट्स", "en": "Fake-news sites", "default": False, "urls": [
     SB + "alternates/fakenews/hosts"]},
 ]},
]

DOMAIN_REGEX = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")
SKIP = {"localhost", "local", "broadcasthost"}

def clean_and_extract_domains(raw_text):
    domains = set()
    for line in raw_text.splitlines():
        line = line.strip()
        if not line or line[0] in "#!":
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("127.0.0.1", "0.0.0.0"):
            domain = parts[1]
        elif len(parts) == 1:
            domain = parts[0]
        else:
            continue
        domain = domain.strip().lower().replace("||", "").replace("^", "")
        if ":" in domain:
            domain = domain.split(":")[0]
        if domain.startswith(("0.0.0.0.", "127.0.0.1.")):
            continue
        if DOMAIN_REGEX.match(domain) and domain not in SKIP:
            domains.add(domain)
    return domains

_cache = {}
def fetch_single_url(url):
    if url in _cache:
        return _cache[url]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KavachAutoBot/2.0"}
    result = set()
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=90)
            if resp.status_code == 200:
                result = clean_and_extract_domains(resp.text)
                print(f"    [+] {len(result):7d} domains: {url[:70]}")
                break
            print(f"    [-] HTTP {resp.status_code}: {url[:70]}")
        except Exception as e:
            print(f"    [-] fetch error ({attempt + 1}/3) {url[:60]}: {e}")
        time.sleep(2 * (attempt + 1))
    _cache[url] = result
    return result

def rank_sub(sub):
    """ज़्यादा स्रोतों में मौजूद + छोटा डोमेन = ज़्यादा ज़रूरी। फिर cap तक काटो।"""
    score = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for res in ex.map(fetch_single_url, sub["urls"]):
            for d in res:
                score[d] = score.get(d, 0) + 1
    if not score:
        return []
    for d in sub.get("seeds", []):
        score[d] = score.get(d, 0) + 100
    ranked = sorted(score, key=lambda d: (-score[d], d.count("."), len(d), d))
    cap = sub.get("cap", DEFAULT_CAP)
    if len(ranked) > cap:
        print(f"    [i] {sub['id']}: {len(ranked)} -> capped at {cap}")
        ranked = ranked[:cap]
    return ranked

def header(title, n):
    # जानबूझकर कोई timestamp नहीं: डोमेन न बदलें तो फ़ाइल भी न बदले
    return (f"# =========================================================\n# {title}\n"
            f"# Developer: {DEVELOPER} ({EMAIL})\n# {COPYRIGHT}\n# Total Active Domains: {n}\n"
            f"# Format: one domain per line, sorted A-Z, duplicates removed\n"
            f"# =========================================================\n")

def write_list(rel_path, title, domains):
    data = (header(title, len(domains)) + "".join(f"{d}\n" for d in sorted(domains))).encode("utf-8")
    full = os.path.join(RULES_DIR, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    if WRITE_PLAIN:
        with open(full, "wb") as f:
            f.write(data)
    gz_path = full + ".gz"
    with open(gz_path, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            gz.write(data)
    with open(gz_path, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()
    return {"path": rel_path + ".gz", "count": len(domains), "sha256": sha}

def write_sub(group, sub, ranked):
    total = len(ranked)
    base = f"{group['id']}/{sub['id']}"
    title = f"Kavach - {group['en']} / {sub['en']}"
    if total <= TIER_THRESHOLD:
        return {"full": write_list(f"{base}.txt", title, ranked)}
    cuts = {"small": int(total * 0.20), "medium": int(total * 0.60), "large": total}
    return {t: write_list(f"{base}-{t}.txt", f"{title} ({t.capitalize()} Tier)", ranked[:n])
            for t, n in cuts.items()}

def content_hash(all_ranked):
    h = hashlib.sha256()
    for key in sorted(all_ranked):
        h.update(key.encode())
        for d in sorted(all_ranked[key]):
            h.update(d.encode()); h.update(b"\n")
    return h.hexdigest()

def old_sub_entries(old):
    out = {}
    for g in old.get("groups", []):
        for s in g.get("subs", []):
            out[f"{g['id']}/{s['id']}"] = s
    return out

def main():
    start = datetime.datetime.utcnow()
    print("=== Kavach Rules Engine v2 - Build start ===")
    manifest_path = os.path.join(RULES_DIR, "manifest.json")
    old = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            old = json.load(f)
    old_subs = old_sub_entries(old)

    ranked_all, reused = {}, set()
    for g in GROUPS:
        for s in g["subs"]:
            key = f"{g['id']}/{s['id']}"
            print(f"\n[*] {key}")
            ranked = rank_sub(s)
            prev = old_subs.get(key)
            prev_total = prev["total"] if prev else 0
            if prev and len(ranked) < prev_total * 0.5:
                print(f"    [!] {key}: {len(ranked)} vs previous {prev_total} -> keeping previous files")
                reused.add(key)
            elif ranked:
                ranked_all[key] = ranked
            else:
                print(f"    [!] {key}: no data and no previous version -> skipped")

    new_hash = content_hash(ranked_all)
    if old.get("content_hash") == new_hash and not reused and old.get("schema") == 2:
        print("[=] No domain changes. Nothing written.")
        return

    keep, groups_out = set(), []
    for g in GROUPS:
        subs_out = []
        for s in g["subs"]:
            key = f"{g['id']}/{s['id']}"
            if key in reused:
                entry = old_subs[key]
            elif key in ranked_all:
                files = write_sub(g, s, ranked_all[key])
                entry = {"id": s["id"], "hi": s["hi"], "en": s["en"], "default": s["default"],
                         "total": len(ranked_all[key]), "files": files}
            else:
                continue
            for fi in entry["files"].values():
                keep.add(os.path.normpath(os.path.join(RULES_DIR, fi["path"])))
            subs_out.append(entry)
        if subs_out:
            groups_out.append({"id": g["id"], "hi": g["hi"], "en": g["en"], "subs": subs_out})

    # पुरानी/हटाई गई फ़ाइलें और फ़ोल्डर साफ़ करो (जैसे categories/, bundles/, other/)
    for root, dirs, files in os.walk(RULES_DIR, topdown=False):
        for fn in files:
            p = os.path.normpath(os.path.join(root, fn))
            if p != os.path.normpath(manifest_path) and p not in keep:
                os.remove(p)
        if root != RULES_DIR and not os.listdir(root):
            os.rmdir(root)

    manifest = {
        "schema": 2,
        "version": start.strftime("%Y%m%d%H%M"),
        "build_date": start.isoformat() + "Z",
        "content_hash": new_hash,
        "default_tier": DEFAULT_TIER,
        "tier_threshold": TIER_THRESHOLD,
        "developer": DEVELOPER, "email": EMAIL, "copyright": COPYRIGHT,
        "groups": groups_out,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    n_sub = sum(len(g["subs"]) for g in groups_out)
    print(f"\n[✓] Done: {len(groups_out)} groups, {n_sub} sub-categories")

if __name__ == "__main__":
    main()
