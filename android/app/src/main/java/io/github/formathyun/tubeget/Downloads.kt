package io.github.formathyun.tubeget

import android.content.Context
import android.media.MediaScannerConnection
import android.util.Log
import androidx.core.content.ContextCompat
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.UUID

enum class Status { QUEUED, RUNNING, POSTPROCESS, DONE, FAILED, CANCELED }

data class DownloadItem(
    val id: String,
    val url: String,
    val title: String,
    val thumbnail: String?,
    val options: DownloadOptions,
    val status: Status = Status.QUEUED,
    val progress: Float? = null,
    val speed: Double? = null,
    val eta: Long? = null,
    val filePath: String? = null,
    val error: String? = null,
    val log: String = "",
    val createdAt: Long = System.currentTimeMillis(),
    val finishedAt: Long? = null,
) {
    val active get() = status == Status.QUEUED || status == Status.RUNNING || status == Status.POSTPROCESS

    fun toJson(): JSONObject = JSONObject().apply {
        put("id", id); put("url", url); put("title", title); put("thumbnail", thumbnail ?: "")
        put("options", options.toJson()); put("status", status.name)
        put("filePath", filePath ?: ""); put("error", error ?: "")
        put("createdAt", createdAt); put("finishedAt", finishedAt ?: 0L)
    }

    companion object {
        fun fromJson(o: JSONObject): DownloadItem {
            var st = runCatching { Status.valueOf(o.optString("status")) }.getOrDefault(Status.QUEUED)
            // 앱이 꺼질 때 받던 것은 다시 대기 (조각 파일이 남아 있어서 이어받는다)
            if (st == Status.RUNNING || st == Status.POSTPROCESS) st = Status.QUEUED
            return DownloadItem(
                id = o.getString("id"),
                url = o.getString("url"),
                title = o.optString("title"),
                thumbnail = o.optString("thumbnail").ifBlank { null },
                options = DownloadOptions.fromJson(o.optJSONObject("options")),
                status = st,
                filePath = o.optString("filePath").ifBlank { null },
                error = o.optString("error").ifBlank { null },
                createdAt = o.optLong("createdAt"),
                finishedAt = o.optLong("finishedAt").takeIf { it > 0 },
            )
        }
    }
}

/** 다운로드 목록과 동시 실행 관리. 화면과 알림 서비스가 items 를 함께 본다. */
object Downloads {
    private const val TAG = "TubeGet"
    private const val MAX_KEEP = 300

    private val _items = MutableStateFlow<List<DownloadItem>>(emptyList())
    val items: StateFlow<List<DownloadItem>> get() = _items

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val running = mutableSetOf<String>()
    private lateinit var app: Context
    private val storeFile by lazy { File(app.filesDir, "downloads.json") }

    fun init(context: Context) {
        app = context.applicationContext
        _items.value = load()
    }

    /** 앱 화면이 열릴 때: 지난번에 남은 대기 항목을 이어서 받는다. */
    fun resume() {
        if (_items.value.any { it.active }) {
            startService()
            scope.launch { pump() }
        }
    }

    // ---- 목록 바꾸기 ---------------------------------------------------------

    private fun edit(id: String, persist: Boolean = false, change: (DownloadItem) -> DownloadItem) {
        _items.update { list -> list.map { if (it.id == id) change(it) else it } }
        if (persist) save()
    }

    fun get(id: String): DownloadItem? = _items.value.firstOrNull { it.id == id }

    fun add(url: String, title: String, thumbnail: String?, options: DownloadOptions) {
        val item = DownloadItem(UUID.randomUUID().toString(), url, title, thumbnail, options)
        _items.update { listOf(item) + it }
        save()
        startService()
        scope.launch { pump() }
    }

    fun cancel(id: String) {
        val item = get(id) ?: return
        if (item.status == Status.QUEUED) {
            edit(id, persist = true) { it.copy(status = Status.CANCELED) }
        } else if (item.status == Status.RUNNING || item.status == Status.POSTPROCESS) {
            edit(id, persist = true) { it.copy(status = Status.CANCELED) }
            YoutubeDL.getInstance().destroyProcessById(id)
        }
    }

    fun retry(id: String) {
        edit(id, persist = true) {
            it.copy(status = Status.QUEUED, error = null, progress = null, log = "", finishedAt = null)
        }
        startService()
        scope.launch { pump() }
    }

    /** 목록에서 지우기. 다 받지 못한 항목은 조각 파일도 함께 지운다. */
    fun remove(id: String, deleteFile: Boolean = false) {
        val item = get(id) ?: return
        if (item.status == Status.RUNNING || item.status == Status.POSTPROCESS) {
            YoutubeDL.getInstance().destroyProcessById(id)
        }
        _items.update { list -> list.filterNot { it.id == id } }
        save()
        scope.launch {
            tempDir(id).deleteRecursively()
            if (deleteFile) item.filePath?.let { p ->
                val f = File(p)
                if (f.delete()) MediaScannerConnection.scanFile(app, arrayOf(p), null, null)
            }
        }
    }

    fun clearFinished() {
        val gone = _items.value.filter { it.status == Status.DONE }
        _items.update { list -> list.filterNot { it.status == Status.DONE } }
        save()
        scope.launch { gone.forEach { tempDir(it.id).deleteRecursively() } }
    }

    // ---- 실행 ----------------------------------------------------------------

    private fun startService() {
        try {
            ContextCompat.startForegroundService(app, android.content.Intent(app, DownloadService::class.java))
        } catch (e: Exception) {
            // 백그라운드에서 서비스를 시작할 수 없는 경우: 다운로드는 앱이 켜져 있는 동안 계속된다
            Log.w(TAG, "service start failed", e)
        }
    }

    @Synchronized
    private fun nextToRun(): DownloadItem? {
        val limit = Settings.prefs.value.maxConcurrent
        if (running.size >= limit) return null
        val next = _items.value.lastOrNull { it.status == Status.QUEUED && it.id !in running } ?: return null
        running += next.id
        return next
    }

    private suspend fun pump() {
        try {
            Engine.awaitReady()
        } catch (e: Exception) {
            _items.value.filter { it.status == Status.QUEUED }.forEach { item ->
                edit(item.id, persist = true) {
                    it.copy(status = Status.FAILED, error = app.getString(R.string.engine_failed))
                }
            }
            return
        }
        while (true) {
            val item = nextToRun() ?: return
            scope.launch {
                try {
                    run(item)
                } finally {
                    synchronized(this@Downloads) { running -= item.id }
                    pump()
                }
            }
        }
    }

    private fun tempDir(id: String) = File(app.cacheDir, "dl/$id")

    private fun run(item: DownloadItem) {
        val out = Settings.outputDir()
        val tmp = tempDir(item.id)
        out.mkdirs(); tmp.mkdirs()
        edit(item.id, persist = true) { it.copy(status = Status.RUNNING, progress = null, error = null) }

        val req = YoutubeDLRequest(item.url)
        req.addOption("--cache-dir", Engine.ytdlpCacheDir())
        req.addCommands(Args.download(item.options, out.absolutePath, tmp.absolutePath))

        val tracker = ProgressTracker()
        val log = StringBuilder()
        var lastUi = 0L
        try {
            val resp = YoutubeDL.getInstance().execute(req, item.id, false) { _, _, line ->
                synchronized(log) { if (log.length < 200_000) log.append(line).append('\n') }
                if (tracker.feed(line)) {
                    val now = System.currentTimeMillis()
                    if (now - lastUi > 250 || tracker.postprocessing) {
                        lastUi = now
                        edit(item.id) {
                            if (it.status == Status.CANCELED) it else it.copy(
                                status = if (tracker.postprocessing) Status.POSTPROCESS else Status.RUNNING,
                                progress = tracker.fraction,
                                speed = tracker.speed,
                                eta = tracker.eta,
                            )
                        }
                    }
                }
            }
            // 콜백이 못 받은 줄(마지막 줄 등)에서 최종 파일 경로를 다시 찾는다
            resp.out.lines().forEach { tracker.feed(it) }
            val path = tracker.finalPath
            if (path != null) {
                MediaScannerConnection.scanFile(app, arrayOf(path), null, null)
            }
            tmp.deleteRecursively()
            edit(item.id, persist = true) {
                it.copy(
                    status = Status.DONE, progress = 1f, speed = null, eta = null,
                    filePath = path, finishedAt = System.currentTimeMillis(), log = "",
                )
            }
            Notifier.finished(app, get(item.id) ?: item)
        } catch (e: YoutubeDL.CanceledException) {
            edit(item.id, persist = true) { it.copy(status = Status.CANCELED, speed = null, eta = null) }
        } catch (e: Exception) {
            if (get(item.id)?.status == Status.CANCELED) return
            val full = synchronized(log) { log.toString() } + "\n" + (e.message ?: "")
            Log.w(TAG, "download failed: ${e.message}")
            edit(item.id, persist = true) {
                it.copy(
                    status = Status.FAILED, speed = null, eta = null,
                    error = Errors.explain(app, full), log = full.takeLast(20_000),
                )
            }
            Notifier.failed(app, get(item.id) ?: item)
        }
    }

    // ---- 저장 ----------------------------------------------------------------

    private fun load(): List<DownloadItem> = try {
        if (!storeFile.exists()) emptyList() else {
            val arr = JSONArray(storeFile.readText())
            (0 until arr.length()).mapNotNull { i ->
                runCatching { DownloadItem.fromJson(arr.getJSONObject(i)) }.getOrNull()
            }
        }
    } catch (e: Exception) {
        Log.w(TAG, "load failed", e); emptyList()
    }

    @Synchronized
    private fun save() {
        try {
            val list = _items.value.take(MAX_KEEP)
            val arr = JSONArray()
            list.forEach { arr.put(it.toJson()) }
            val tmp = File(storeFile.parentFile, storeFile.name + ".tmp")
            tmp.writeText(arr.toString())
            if (!tmp.renameTo(storeFile)) {
                storeFile.writeText(arr.toString()); tmp.delete()
            }
        } catch (e: Exception) {
            Log.w(TAG, "save failed", e)
        }
    }
}
