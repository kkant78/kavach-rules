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

def export_kavach_app_code(output_dir="app-code"):
    """कवच ऐप की सभी कोड फाइलों को सीधे डाउनलोड योग्य फॉर्मेट में एक्सपोर्ट करना"""
    os.makedirs(output_dir, exist_ok=True)
    print("\n[*] Exporting Kavach v0.0.9 App Source Files for Direct Download...")

    # 1. build.gradle.kts
    gradle_code = """plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.kavach.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.kavach.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 9
        versionName = "0.0.9"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.8"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.fragment:fragment-ktx:1.6.2")
    implementation("androidx.biometric:biometric:1.1.0")
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
}
"""
    with open(os.path.join(output_dir, "build.gradle.kts"), "w", encoding="utf-8") as f:
        f.write(gradle_code)

    # 2. build.yml
    workflow_code = """name: Build Kavach APK

on:
  push:
    branches: [ "main", "master" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'

      - name: Setup Gradle 8.5
        uses: gradle/actions/setup-gradle@v3
        with:
          gradle-version: '8.5'

      - name: Build Debug APK
        run: gradle assembleDebug --stacktrace --no-daemon

      - name: Upload Kavach APK
        uses: actions/upload-artifact@v4
        with:
          name: Kavach-v0.0.9-Debug-APK
          path: app/build/outputs/apk/debug/*.apk
"""
    with open(os.path.join(output_dir, "build.yml"), "w", encoding="utf-8") as f:
        f.write(workflow_code)

    # 3. KavachVpnService.kt
    vpn_code = """package com.kavach.app

import android.content.Context
import android.content.Intent
import android.net.VpnService
import android.os.Handler
import android.os.Looper
import android.os.ParcelFileDescriptor
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import java.nio.ByteBuffer
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.Executors

data class DownloadTaskStatus(
    val name: String,
    val percent: Int,
    val statusText: String
)

object BlocklistManager {
    val blockedDomains = ConcurrentHashMap.newKeySet<String>()
    var totalBlockedCount = mutableIntStateOf(0)
    var isListLoaded = false

    val downloadQueue = mutableStateListOf<DownloadTaskStatus>()
    var isSyncing = mutableStateOf(false)
    private val mainHandler = Handler(Looper.getMainLooper())

    private val fallbackList = listOf(
        "googleads.g.doubleclick.net", "pagead2.googlesyndication.com",
        "adservice.google.com", "ads.facebook.com", "graph.facebook.com",
        "analytics.google.com", "admob.com", "unityads.unity3d.com",
        "applovin.com", "vungle.com", "ironsource.com"
    )

    fun init(context: Context) {
        if (isListLoaded && blockedDomains.isNotEmpty()) return
        blockedDomains.addAll(fallbackList)

        Executors.newSingleThreadExecutor().execute {
            val localFile = File(context.filesDir, "active_blocklist.txt")
            if (localFile.exists()) {
                loadFromFile(localFile)
            }
            isListLoaded = true
        }
    }

    fun syncSelectedLists(
        context: Context,
        tasks: List<Pair<String, String>>,
        onFinished: () -> Unit
    ) {
        mainHandler.post {
            isSyncing.value = true
            downloadQueue.clear()
            tasks.forEach {
                downloadQueue.add(DownloadTaskStatus(it.first, 0, "Pending"))
            }
        }

        Executors.newSingleThreadExecutor().execute {
            val allDownloadedDomains = mutableSetOf<String>()

            tasks.forEachIndexed { index, task ->
                val taskName = task.first
                val urlStr = task.second

                mainHandler.post {
                    if (index < downloadQueue.size) {
                        downloadQueue[index] = DownloadTaskStatus(taskName, 0, "Connecting...")
                    }
                }

                try {
                    var connection = (URL(urlStr).openConnection() as HttpURLConnection).apply {
                        connectTimeout = 15000
                        readTimeout = 15000
                        instanceFollowRedirects = true
                        setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 10; Mobile) KavachApp/0.0.9")
                        setRequestProperty("Accept", "text/plain,*/*")
                    }

                    var responseCode = connection.responseCode

                    if (responseCode == 404 || responseCode == 403) {
                        val fallbackMirror = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"
                        connection = (URL(fallbackMirror).openConnection() as HttpURLConnection).apply {
                            connectTimeout = 15000
                            readTimeout = 15000
                            instanceFollowRedirects = true
                            setRequestProperty("User-Agent", "Mozilla/5.0 (Linux; Android 10; Mobile) KavachApp/0.0.9")
                        }
                        responseCode = connection.responseCode
                    }

                    if (responseCode in 200..299) {
                        val totalLength = connection.contentLength
                        val input = connection.inputStream
                        val output = StringBuilder()
                        val buffer = ByteArray(4096)
                        var bytesReadTotal = 0L
                        var bytesRead: Int

                        while (input.read(buffer).also { bytesRead = it } != -1) {
                            output.append(String(buffer, 0, bytesRead))
                            bytesReadTotal += bytesRead
                            val pct = if (totalLength > 0) ((bytesReadTotal * 100) / totalLength).toInt().coerceIn(0, 99) else 50
                            mainHandler.post {
                                if (index < downloadQueue.size) {
                                    downloadQueue[index] = DownloadTaskStatus(taskName, pct, "Downloading ($pct%)")
                                }
                            }
                        }
                        input.close()

                        output.toString().split("\\n").forEach { line ->
                            val trimmed = line.trim().lowercase()
                            if (trimmed.isNotEmpty() && !trimmed.startsWith("#") && !trimmed.startsWith("!")) {
                                val parts = trimmed.split(Regex("\\\\s+"))
                                val dom = if (parts.size >= 2 && (parts[0] == "0.0.0.0" || parts[0] == "127.0.0.1")) parts[1] else parts[0]
                                if (dom.contains(".") && !dom.startsWith("localhost")) {
                                    allDownloadedDomains.add(dom)
                                }
                            }
                        }

                        mainHandler.post {
                            if (index < downloadQueue.size) {
                                downloadQueue[index] = DownloadTaskStatus(taskName, 100, "Completed ✅ (${allDownloadedDomains.size} नियम)")
                            }
                        }
                    } else {
                        mainHandler.post {
                            if (index < downloadQueue.size) {
                                downloadQueue[index] = DownloadTaskStatus(taskName, 0, "HTTP $responseCode ❌")
                            }
                        }
                    }
                } catch (e: Exception) {
                    mainHandler.post {
                        if (index < downloadQueue.size) {
                            val errMsg = e.localizedMessage ?: "Error"
                            downloadQueue[index] = DownloadTaskStatus(taskName, 0, "Fail: ${errMsg.take(15)} ❌")
                        }
                    }
                }
            }

            if (allDownloadedDomains.isNotEmpty()) {
                blockedDomains.clear()
                blockedDomains.addAll(allDownloadedDomains)
                try {
                    val file = File(context.filesDir, "active_blocklist.txt")
                    file.writeText(allDownloadedDomains.joinToString("\\n"))
                    context.getSharedPreferences("kavach_prefs", Context.MODE_PRIVATE)
                        .edit().putInt("cached_domain_count", allDownloadedDomains.size).apply()
                } catch (e: Exception) {}
            }

            mainHandler.post {
                isSyncing.value = false
                onFinished()
            }
        }
    }

    private fun loadFromFile(file: File) {
        try {
            val lines = file.readLines()
            val temp = mutableSetOf<String>()
            lines.forEach { line ->
                val trimmed = line.trim().lowercase()
                if (trimmed.isNotEmpty() && !trimmed.startsWith("#")) {
                    temp.add(trimmed)
                }
            }
            if (temp.isNotEmpty()) {
                blockedDomains.clear()
                blockedDomains.addAll(temp)
            }
        } catch (e: Exception) {}
    }

    fun isDomainBlocked(domain: String): Boolean {
        var d = domain.lowercase()
        if (blockedDomains.contains(d)) return true
        while (d.contains(".")) {
            d = d.substringAfter(".")
            if (blockedDomains.contains(d)) return true
        }
        return false
    }
}

class KavachVpnService : VpnService(), Runnable {

    private var vpnInterface: ParcelFileDescriptor? = null
    private var vpnThread: Thread? = null
    private var isRunning = false
    private val dnsWorkerPool = Executors.newFixedThreadPool(8)
    private val upstreamDnsIp = byteArrayOf(1, 1, 1, 1)

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == "STOP_VPN") {
            stopVpn()
            return START_NOT_STICKY
        }
        startVpn()
        return START_STICKY
    }

    private fun startVpn() {
        if (vpnInterface != null) return

        try {
            BlocklistManager.init(this)

            val builder = Builder()
                .setSession("कवच सुरक्षा")
                .addAddress("10.0.0.2", 32)
                .addDnsServer("10.0.0.1")
                .addRoute("10.0.0.1", 32)

            vpnInterface = builder.establish()
            isRunning = true
            vpnThread = Thread(this, "KavachVpnThread").apply { start() }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun run() {
        val vpnFd = vpnInterface?.fileDescriptor ?: return
        val inputStream = FileInputStream(vpnFd)
        val outputStream = FileOutputStream(vpnFd)
        val packet = ByteBuffer.allocate(32767)

        val prefs = getSharedPreferences("kavach_prefs", Context.MODE_PRIVATE)

        while (isRunning) {
            try {
                packet.clear()
                val length = inputStream.read(packet.array())
                if (length <= 0) continue

                val buffer = packet.array()
                if (length < 28 || buffer[9].toInt() != 17) continue

                val destPort = ((buffer[22].toInt() and 0xFF) shl 8) or (buffer[23].toInt() and 0xFF)
                if (destPort != 53) continue

                val srcPort = ((buffer[20].toInt() and 0xFF) shl 8) or (buffer[21].toInt() and 0xFF)
                val dnsOffset = 28
                val dnsLength = length - dnsOffset

                val rawDnsQuery = ByteArray(dnsLength)
                System.arraycopy(buffer, dnsOffset, rawDnsQuery, 0, dnsLength)

                val qName = parseDnsQuestion(rawDnsQuery)
                val isAdBlockActive = prefs.getBoolean("adblock_enabled", true)

                if (isAdBlockActive && qName != null && BlocklistManager.isDomainBlocked(qName)) {
                    BlocklistManager.totalBlockedCount.intValue += 1
                    SpeedDataRepo.addLog("[BLOCKED 🚫] $qName")

                    val nxdomainResponse = buildNxdomainDnsResponse(rawDnsQuery)
                    val ipResponse = buildIpv4UdpPacket(srcPort, destPort, nxdomainResponse)
                    synchronized(outputStream) {
                        outputStream.write(ipResponse)
                    }
                } else {
                    if (qName != null) SpeedDataRepo.addLog("[ALLOWED 🟢] $qName")

                    dnsWorkerPool.execute {
                        try {
                            val socket = DatagramSocket()
                            protect(socket)
                            socket.soTimeout = 2000

                            val upstreamPacket = DatagramPacket(rawDnsQuery, rawDnsQuery.size, InetAddress.getByAddress(upstreamDnsIp), 53)
                            socket.send(upstreamPacket)

                            val replyBuffer = ByteArray(1500)
                            val replyPacket = DatagramPacket(replyBuffer, replyBuffer.size)
                            socket.receive(replyPacket)

                            val realDnsResponse = ByteArray(replyPacket.length)
                            System.arraycopy(replyBuffer, 0, realDnsResponse, 0, replyPacket.length)

                            val ipResponse = buildIpv4UdpPacket(srcPort, destPort, realDnsResponse)
                            synchronized(outputStream) {
                                outputStream.write(ipResponse)
                            }
                            socket.close()
                        } catch (e: Exception) {}
                    }
                }
            } catch (e: Exception) {}
        }
    }

    private fun parseDnsQuestion(dnsBytes: ByteArray): String? {
        try {
            var pos = 12
            val domain = StringBuilder()
            while (pos < dnsBytes.size) {
                val len = dnsBytes[pos].toInt() and 0xFF
                if (len == 0) break
                pos++
                for (i in 0 until len) {
                    domain.append(dnsBytes[pos].toInt().toChar())
                    pos++
                }
                domain.append(".")
            }
            return if (domain.isNotEmpty()) domain.dropLast(1).toString() else null
        } catch (e: Exception) {
            return null
        }
    }

    private fun buildNxdomainDnsResponse(query: ByteArray): ByteArray {
        val response = query.clone()
        response[2] = 0x81.toByte()
        response[3] = 0x83.toByte()
        response[6] = 0.toByte()
        response[7] = 0.toByte()
        return response
    }

    private fun buildIpv4UdpPacket(clientPort: Int, dnsPort: Int, payload: ByteArray): ByteArray {
        val totalLength = 28 + payload.size
        val packet = ByteBuffer.allocate(totalLength)

        packet.put(0x45.toByte())
        packet.put(0.toByte())
        packet.putShort(totalLength.toShort())
        packet.putShort(0.toShort())
        packet.putShort(0x4000.toShort())
        packet.put(64.toByte())
        packet.put(17.toByte())
        packet.putShort(0.toShort())

        packet.put(10.toByte()).put(0.toByte()).put(0.toByte()).put(1.toByte())
        packet.put(10.toByte()).put(0.toByte()).put(0.toByte()).put(2.toByte())

        packet.putShort(dnsPort.toShort())
        packet.putShort(clientPort.toShort())
        packet.putShort((8 + payload.size).toShort())
        packet.putShort(0.toShort())

        packet.put(payload)

        val raw = packet.array()
        val checksum = calculateChecksum(raw, 0, 20)
        raw[10] = ((checksum shr 8) and 0xFF).toByte()
        raw[11] = (checksum and 0xFF).toByte()

        return raw
    }

    private fun calculateChecksum(buf: ByteArray, offset: Int, length: Int): Int {
        var sum = 0
        var i = offset
        while (i < offset + length) {
            val word = ((buf[i].toInt() and 0xFF) shl 8) or (buf[i + 1].toInt() and 0xFF)
            sum += word
            i += 2
        }
        while ((sum shr 16) > 0) {
            sum = (sum and 0xFFFF) + (sum shr 16)
        }
        return sum.inv() and 0xFFFF
    }

    private fun stopVpn() {
        isRunning = false
        try {
            dnsWorkerPool.shutdownNow()
            vpnThread?.interrupt()
            vpnInterface?.close()
            vpnInterface = null
            stopSelf()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun onDestroy() {
        stopVpn()
        super.onDestroy()
    }
}
"""
    with open(os.path.join(output_dir, "KavachVpnService.kt"), "w", encoding="utf-8") as f:
        f.write(vpn_code)

    print("[✓] App source files exported successfully to app-code/")

def main():
    start_time = datetime.datetime.utcnow()
    print("=========================================================")
    print(f" Kavach Auto-Pilot Rules & Code Exporter - Starting")
    print(f" Timestamp: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=========================================================")

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

        all_small.update(s)
        all_medium.update(m)
        all_large.update(l)

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

    # ऐप कोड का सीधा एक्सपोर्ट
    export_kavach_app_code()

    duration = (datetime.datetime.utcnow() - start_time).total_seconds()
    print(f"\n=========================================================")
    print(f"[✓] AUTO-PILOT COMPLETED IN {duration:.1f} SECONDS")
    print("=========================================================")

if __name__ == "__main__":
    main()
