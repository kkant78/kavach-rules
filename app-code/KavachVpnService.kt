package com.kavach.app

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

                        output.toString().split("\n").forEach { line ->
                            val trimmed = line.trim().lowercase()
                            if (trimmed.isNotEmpty() && !trimmed.startsWith("#") && !trimmed.startsWith("!")) {
                                val parts = trimmed.split(Regex("\\s+"))
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
                    file.writeText(allDownloadedDomains.joinToString("\n"))
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
