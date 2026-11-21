package io.github.formathyun.tubeget

import android.content.Context
import android.util.Log
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/** yt-dlp(파이썬)·ffmpeg 준비, 업데이트, 정보 조회. */
object Engine {
    private const val TAG = "TubeGet"
    private const val DAY_MS = 24L * 60 * 60 * 1000

    sealed interface State {
        data object Starting : State
        data object Ready : State
        data class Failed(val message: String) : State
    }

    private val _state = MutableStateFlow<State>(State.Starting)
    val state: StateFlow<State> get() = _state

    private val _version = MutableStateFlow("")
    val version: StateFlow<String> get() = _version

    private val _updating = MutableStateFlow(false)
    val updating: StateFlow<Boolean> get() = _updating

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private lateinit var app: Context

    fun start(context: Context) {
        app = context.applicationContext
        scope.launch {
            try {
                YoutubeDL.getInstance().init(app)
                FFmpeg.getInstance().init(app)
                _version.value = YoutubeDL.getInstance().version(app).orEmpty()
                _state.value = State.Ready
            } catch (e: Throwable) {
                Log.e(TAG, "init failed", e)
                _state.value = State.Failed(e.message ?: e.toString())
                return@launch
            }
            // 유튜브가 자주 바뀌어서 yt-dlp 는 하루 한 번 새 버전을 확인한다
            if (Settings.prefs.value.autoUpdate &&
                System.currentTimeMillis() - Settings.lastUpdateCheck > DAY_MS
            ) {
                update()
            }
        }
    }

    suspend fun awaitReady() {
        state.first { it !is State.Starting }
        val s = state.value
        if (s is State.Failed) throw IllegalStateException(s.message)
    }

    /** yt-dlp 업데이트. 결과: true = 새 버전 설치, false = 이미 최신, null = 실패 */
    suspend fun update(): Boolean? = withContext(Dispatchers.IO) {
        if (_updating.value) return@withContext null
        _updating.value = true
        try {
            awaitReady()
            val status = YoutubeDL.getInstance().updateYoutubeDL(app, YoutubeDL.UpdateChannel.STABLE)
            Settings.lastUpdateCheck = System.currentTimeMillis()
            _version.value = YoutubeDL.getInstance().version(app).orEmpty()
            status == YoutubeDL.UpdateStatus.DONE
        } catch (e: Throwable) {
            Log.w(TAG, "update failed", e)
            null
        } finally {
            _updating.value = false
        }
    }

    private fun cacheDir(): File = File(app.cacheDir, "yt-dlp-cache").apply { mkdirs() }

    /** 링크 정보 불러오기. 실패하면 알기 쉬운 안내가 담긴 예외 */
    suspend fun fetch(url: String): MediaInfo = withContext(Dispatchers.IO) {
        awaitReady()
        val req = YoutubeDLRequest(url)
        req.addOption("--cache-dir", cacheDir().absolutePath)
        req.addCommands(Args.info())
        try {
            val resp = YoutubeDL.getInstance().execute(req, null, null)
            InfoParser.parse(resp.out, url)
        } catch (e: org.json.JSONException) {
            throw FriendlyException(app.getString(R.string.err_unknown))
        } catch (e: Exception) {
            throw FriendlyException(Errors.explain(app, e.message))
        }
    }

    fun ytdlpCacheDir(): String = cacheDir().absolutePath
}

class FriendlyException(message: String) : Exception(message)
