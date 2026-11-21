package io.github.formathyun.tubeget

import android.content.Context
import android.content.SharedPreferences
import android.os.Environment
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File

/** 받기 화면(영상 카드)에서 고른 값과 설정. PC 판 위쪽 툴바와 같은 항목. */
data class Prefs(
    val instant: Boolean = false,        // 바로 받기
    val mode: String = "video",
    val maxHeight: Int = 1080,
    val container: String = "mp4",
    val audioFormat: String = "mp3",
    val audioQuality: String = "0",
    val outDir: String = DEFAULT_OUT_DIR,
    val subLangs: String = "",           // 자막 언어 (비면 없음)
    val autoSubs: Boolean = true,
    val subMode: String = "embed",
    val dubLang: String = "",            // 더빙 (비면 원본 음성)
    val tags: Boolean = true,            // 태그 넣기
    val compatH264: Boolean = true,
    val maxConcurrent: Int = 2,
    val autoUpdate: Boolean = true,
    val playlistFolder: Boolean = true,
) {
    fun toOptions(): DownloadOptions = DownloadOptions(
        mode = mode,
        maxHeight = maxHeight,
        container = container,
        audioFormat = audioFormat,
        audioQuality = audioQuality,
        compatH264 = compatH264,
        subLangs = subLangs,
        autoSubs = autoSubs,
        subMode = subMode,
        dubLang = dubLang,
        embedThumbnail = true,
        embedMetadata = tags,
        outDir = outDir,
    )
}

object Settings {
    private lateinit var sp: SharedPreferences
    private val _prefs = MutableStateFlow(Prefs())
    val prefs: StateFlow<Prefs> get() = _prefs

    fun init(context: Context) {
        sp = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
        val d = Prefs()
        _prefs.value = Prefs(
            instant = sp.getBoolean("instant", d.instant),
            mode = sp.getString("mode", d.mode)!!,
            maxHeight = sp.getInt("maxHeight", d.maxHeight),
            container = sp.getString("container", d.container)!!,
            audioFormat = sp.getString("audioFormat", d.audioFormat)!!,
            audioQuality = sp.getString("audioQuality", d.audioQuality)!!,
            outDir = sp.getString("outDir", d.outDir)!!,
            subLangs = sp.getString("subLangs2", d.subLangs)!!,
            autoSubs = sp.getBoolean("autoSubs", d.autoSubs),
            subMode = sp.getString("subMode", d.subMode)!!,
            dubLang = sp.getString("dubLang", d.dubLang)!!,
            tags = sp.getBoolean("embedMetadata", d.tags),
            compatH264 = sp.getBoolean("compatH264", d.compatH264),
            maxConcurrent = sp.getInt("maxConcurrent", d.maxConcurrent).coerceIn(1, 3),
            autoUpdate = sp.getBoolean("autoUpdate", d.autoUpdate),
            playlistFolder = sp.getBoolean("playlistFolder", d.playlistFolder),
        )
    }

    fun update(change: (Prefs) -> Prefs) {
        val p = change(_prefs.value)
        _prefs.value = p
        sp.edit()
            .putBoolean("instant", p.instant)
            .putString("mode", p.mode)
            .putInt("maxHeight", p.maxHeight)
            .putString("container", p.container)
            .putString("audioFormat", p.audioFormat)
            .putString("audioQuality", p.audioQuality)
            .putString("outDir", p.outDir)
            .putString("subLangs2", p.subLangs)
            .putBoolean("autoSubs", p.autoSubs)
            .putString("subMode", p.subMode)
            .putString("dubLang", p.dubLang)
            .putBoolean("embedMetadata", p.tags)
            .putBoolean("compatH264", p.compatH264)
            .putInt("maxConcurrent", p.maxConcurrent)
            .putBoolean("autoUpdate", p.autoUpdate)
            .putBoolean("playlistFolder", p.playlistFolder)
            .apply()
    }

    var lastUpdateCheck: Long
        get() = sp.getLong("lastUpdateCheck", 0L)
        set(v) = sp.edit().putLong("lastUpdateCheck", v).apply()

    /** 저장 위치: 휴대폰 저장소 기준 상대 경로 → 실제 폴더 (예: Download/TubeGet) */
    @Suppress("DEPRECATION")
    fun dirFor(rel: String): File =
        File(Environment.getExternalStorageDirectory(), rel.trim('/').ifBlank { DEFAULT_OUT_DIR })
}
