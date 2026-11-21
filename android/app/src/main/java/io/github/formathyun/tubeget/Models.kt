package io.github.formathyun.tubeget

import org.json.JSONArray
import org.json.JSONObject

/** 링크에서 불러온 영상(또는 재생목록) 정보. */
data class MediaInfo(
    val url: String,
    val id: String,
    val title: String,
    val uploader: String,
    val duration: Double?,
    val thumbnail: String?,
    /** 고를 수 있는 화질 (예: 2160, 1080, 720 ...) 큰 것부터 */
    val heights: List<Int>,
    /** 화질별 예상 크기(바이트). 0 키는 최고 화질 */
    val videoSizes: Map<Int, Long>,
    val audioSize: Long?,
    val isPlaylist: Boolean = false,
    val entries: List<PlaylistEntry> = emptyList(),
    /** 올린 자막: 코드 → 이름 */
    val subtitles: Map<String, String> = emptyMap(),
    /** 자동 생성·번역 자막: 코드 → 이름 */
    val autoCaptions: Map<String, String> = emptyMap(),
    /** 음성 트랙 언어: 코드 → "original" | "dubbed" | "" */
    val dubs: Map<String, String> = emptyMap(),
    val track: String = "",
    val artist: String = "",
    val album: String = "",
    val year: String = "",
)

data class PlaylistEntry(
    val index: Int,
    val url: String,
    val title: String,
    val duration: Double?,
    val thumbnail: String?,
)

private val HEIGHT_CHOICES = listOf(4320, 2160, 1440, 1080, 720, 480, 360, 240, 144)

private fun JSONObject.str(key: String): String? =
    if (has(key) && !isNull(key)) optString(key).takeIf { it.isNotBlank() && it != "none" } else null

private fun JSONObject.num(key: String): Double? =
    if (has(key) && !isNull(key)) optDouble(key).takeIf { !it.isNaN() } else null

private fun thumbnailOf(o: JSONObject): String? {
    o.str("thumbnail")?.let { return it }
    val arr = o.optJSONArray("thumbnails") ?: return null
    var best: String? = null
    for (i in 0 until arr.length()) {
        val t = arr.optJSONObject(i) ?: continue
        val u = t.str("url") ?: continue
        // 너무 큰 썸네일(maxres) 보다 중간 크기를 고른다
        if (best == null || (t.optInt("width", 0) in 300..1000)) best = u
    }
    return best
}

/** 화질 이름 (2160 → "2160p 4K") */
fun heightLabel(h: Int): String = when (h) {
    4320 -> "4320p 8K"
    2160 -> "2160p 4K"
    1440 -> "1440p QHD"
    1080 -> "1080p FHD"
    720 -> "720p HD"
    else -> "${h}p"
}

object InfoParser {

    fun parse(json: String, url: String): MediaInfo = parse(JSONObject(json), url)

    fun parse(o: JSONObject, url: String): MediaInfo {
        val type = o.optString("_type", "video")
        if (type == "playlist" || o.has("entries")) return parsePlaylist(o, url)

        val formats = o.optJSONArray("formats") ?: JSONArray()
        val duration = o.num("duration")
        data class F(val dim: Int, val size: Long?, val vcodec: String?, val tbr: Double)

        val videos = mutableListOf<F>()
        var bestAudio: Long? = null
        var bestAbr = -1.0
        val dubs = linkedMapOf<String, String>()
        for (i in 0 until formats.length()) {
            val f = formats.optJSONObject(i) ?: continue
            val vcodec = f.str("vcodec")
            val acodec = f.str("acodec")
            val proto = f.optString("protocol", "")
            if (proto.startsWith("mhtml")) continue // 스토리보드
            val tbr = f.num("tbr") ?: 0.0
            val size = (f.num("filesize") ?: f.num("filesize_approx"))?.toLong()
                ?: if (tbr > 0 && duration != null) (tbr * 125 * duration).toLong() else null
            if (vcodec != null) {
                val w = f.optInt("width", 0)
                val h = f.optInt("height", 0)
                val dim = if (w > 0 && h > 0) minOf(w, h) else h
                if (dim > 0) videos += F(dim, size, vcodec, tbr)
            } else if (acodec != null) {
                val lang = f.str("language")
                if (lang != null && lang != "und") {
                    val note = f.optString("format_note", "").lowercase()
                    when {
                        "original" in note -> dubs[lang] = "original"
                        lang !in dubs -> dubs[lang] = if ("dubbed" in note) "dubbed" else ""
                    }
                }
                val abr = f.num("abr") ?: tbr
                if (abr > bestAbr) {
                    bestAbr = abr; bestAudio = size
                }
            }
        }

        // 화질 칸: 그 화질 근처(0.8~1.1배)의 영상 스트림이 실제로 있을 때만 보여준다
        val heights = HEIGHT_CHOICES.filter { c ->
            videos.any { it.dim >= c * 0.8 && it.dim <= c * 1.1 }
        }

        val sizes = mutableMapOf<Int, Long>()
        fun videoSizeAtMost(limit: Int?): Long? {
            val cands = videos.filter { limit == null || it.dim <= limit * 1.1 }
            val top = cands.maxOfOrNull { it.dim } ?: return null
            val best = cands.filter { it.dim == top }.maxByOrNull { it.tbr } ?: return null
            return best.size?.let { it + (bestAudio ?: 0) }
        }
        videoSizeAtMost(null)?.let { sizes[0] = it }
        for (h in heights) videoSizeAtMost(h)?.let { sizes[h] = it }

        return MediaInfo(
            url = o.str("webpage_url") ?: url,
            id = o.optString("id"),
            title = o.str("title") ?: url,
            uploader = o.str("uploader") ?: o.str("channel") ?: "",
            duration = duration,
            thumbnail = thumbnailOf(o),
            heights = heights,
            videoSizes = sizes,
            audioSize = bestAudio,
            subtitles = subNames(o.optJSONObject("subtitles")),
            autoCaptions = subNames(o.optJSONObject("automatic_captions")),
            dubs = if (dubs.size > 1) dubs else emptyMap(), // 음성이 하나뿐이면 고를 게 없다
            track = o.str("track") ?: "",
            artist = o.str("artist") ?: o.str("creator") ?: "",
            album = o.str("album") ?: "",
            year = (if (o.has("release_year") && !o.isNull("release_year")) o.optInt("release_year").toString() else null)
                ?: o.str("upload_date")?.take(4) ?: "",
        )
    }

    private fun subNames(raw: JSONObject?): Map<String, String> {
        if (raw == null) return emptyMap()
        val out = linkedMapOf<String, String>()
        for (code in raw.keys()) {
            if (code.isBlank() || code == "live_chat") continue
            val arr = raw.optJSONArray(code) ?: continue
            if (arr.length() == 0) continue
            var name = ""
            for (i in 0 until arr.length()) {
                val n = arr.optJSONObject(i)?.str("name")
                if (n != null) { name = n; break }
            }
            out[code] = name
        }
        return out
    }

    private fun parsePlaylist(o: JSONObject, url: String): MediaInfo {
        val arr = o.optJSONArray("entries") ?: JSONArray()
        val entries = mutableListOf<PlaylistEntry>()
        for (i in 0 until arr.length()) {
            val e = arr.optJSONObject(i) ?: continue
            val id = e.str("id")
            val eu = e.str("url")?.let { if (it.startsWith("http")) it else null }
                ?: e.str("webpage_url")
                ?: id?.let { "https://www.youtube.com/watch?v=$it" }
                ?: continue
            entries += PlaylistEntry(
                index = entries.size + 1,
                url = eu,
                title = e.str("title") ?: eu,
                duration = e.num("duration"),
                thumbnail = thumbnailOf(e),
            )
        }
        return MediaInfo(
            url = o.str("webpage_url") ?: url,
            id = o.optString("id"),
            title = o.str("title") ?: url,
            uploader = o.str("uploader") ?: o.str("channel") ?: "",
            duration = null,
            thumbnail = thumbnailOf(o) ?: entries.firstOrNull()?.thumbnail,
            heights = HEIGHT_CHOICES.filter { it in 360..2160 },
            videoSizes = emptyMap(),
            audioSize = null,
            isPlaylist = true,
            entries = entries,
        )
    }
}

/** 글 속에서 첫 번째 http(s) 주소를 찾는다 (공유하기로 받은 글에는 제목이 같이 붙어 오기도 함). */
fun extractUrl(text: String?): String? {
    if (text.isNullOrBlank()) return null
    val m = Regex("""https?://[^\s<>"']+""").find(text) ?: return null
    return m.value.trimEnd('.', ',', ')', ']', '>')
}

fun formatBytes(bytes: Long?): String {
    if (bytes == null || bytes <= 0) return ""
    val units = listOf("B", "KB", "MB", "GB", "TB")
    var v = bytes.toDouble()
    var i = 0
    while (v >= 1024 && i < units.size - 1) {
        v /= 1024; i++
    }
    return if (i >= 2) String.format(java.util.Locale.US, "%.1f %s", v, units[i]) else "${v.toLong()} ${units[i]}"
}

fun formatDuration(sec: Double?): String {
    if (sec == null || sec <= 0) return ""
    val s = sec.toLong()
    val h = s / 3600
    val m = (s % 3600) / 60
    val ss = s % 60
    return if (h > 0) String.format(java.util.Locale.US, "%d:%02d:%02d", h, m, ss)
    else String.format(java.util.Locale.US, "%d:%02d", m, ss)
}
