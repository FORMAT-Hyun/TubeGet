package io.github.formathyun.tubeget

import android.content.Context
import android.content.SharedPreferences
import android.os.Environment
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.io.File

data class Prefs(
    val mode: String = "video",
    val maxHeight: Int = 1080,
    val container: String = "mp4",
    val audioFormat: String = "mp3",
    val compatH264: Boolean = true,
    val subtitles: Boolean = false,
    val subLangs: String = "",
    val embedThumbnail: Boolean = true,
    val embedMetadata: Boolean = true,
    val maxConcurrent: Int = 2,
    val autoUpdate: Boolean = true,
    val playlistFolder: Boolean = true,
) {
    fun toOptions(): DownloadOptions = DownloadOptions(
        mode = mode,
        maxHeight = maxHeight,
        container = container,
        audioFormat = audioFormat,
        compatH264 = compatH264,
        subLangs = if (subtitles) subLangs else "",
        embedThumbnail = embedThumbnail,
        embedMetadata = embedMetadata,
    )
}

object Settings {
    private lateinit var sp: SharedPreferences
    private val _prefs = MutableStateFlow(Prefs())
    val prefs: StateFlow<Prefs> get() = _prefs

    fun init(context: Context) {
        sp = context.getSharedPreferences("settings", Context.MODE_PRIVATE)
        val d = Prefs(subLangs = defaultSubLang())
        _prefs.value = Prefs(
            mode = sp.getString("mode", d.mode)!!,
            maxHeight = sp.getInt("maxHeight", d.maxHeight),
            container = sp.getString("container", d.container)!!,
            audioFormat = sp.getString("audioFormat", d.audioFormat)!!,
            compatH264 = sp.getBoolean("compatH264", d.compatH264),
            subtitles = sp.getBoolean("subtitles", d.subtitles),
            subLangs = sp.getString("subLangs", d.subLangs)!!,
            embedThumbnail = sp.getBoolean("embedThumbnail", d.embedThumbnail),
            embedMetadata = sp.getBoolean("embedMetadata", d.embedMetadata),
            maxConcurrent = sp.getInt("maxConcurrent", d.maxConcurrent).coerceIn(1, 3),
            autoUpdate = sp.getBoolean("autoUpdate", d.autoUpdate),
            playlistFolder = sp.getBoolean("playlistFolder", d.playlistFolder),
        )
    }

    private fun defaultSubLang(): String =
        java.util.Locale.getDefault().language.ifBlank { "en" }

    fun update(change: (Prefs) -> Prefs) {
        val p = change(_prefs.value)
        _prefs.value = p
        sp.edit()
            .putString("mode", p.mode)
            .putInt("maxHeight", p.maxHeight)
            .putString("container", p.container)
            .putString("audioFormat", p.audioFormat)
            .putBoolean("compatH264", p.compatH264)
            .putBoolean("subtitles", p.subtitles)
            .putString("subLangs", p.subLangs)
            .putBoolean("embedThumbnail", p.embedThumbnail)
            .putBoolean("embedMetadata", p.embedMetadata)
            .putInt("maxConcurrent", p.maxConcurrent)
            .putBoolean("autoUpdate", p.autoUpdate)
            .putBoolean("playlistFolder", p.playlistFolder)
            .apply()
    }

    var lastUpdateCheck: Long
        get() = sp.getLong("lastUpdateCheck", 0L)
        set(v) = sp.edit().putLong("lastUpdateCheck", v).apply()

    /** 저장 위치: 휴대폰의 Download/TubeGet */
    fun outputDir(): File =
        File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "TubeGet")
}
