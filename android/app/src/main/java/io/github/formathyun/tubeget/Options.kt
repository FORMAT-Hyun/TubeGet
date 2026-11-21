package io.github.formathyun.tubeget

import org.json.JSONObject

val VIDEO_CONTAINERS = listOf("mp4", "mkv", "webm")
val AUDIO_FORMATS = listOf("mp3", "m4a", "opus", "flac")

private val LOSSY_AUDIO = setOf("mp3", "m4a", "opus")
private val THUMB_AUDIO = setOf("mp3", "m4a", "opus", "flac")
private val THUMB_VIDEO = setOf("mp4", "mkv")

/** 다운로드 한 건의 옵션. PC 판 tubegetapp/core/options.py 와 같은 규칙으로 yt-dlp 인자를 만든다. */
data class DownloadOptions(
    val mode: String = "video",          // video | audio
    val maxHeight: Int = 0,              // 0 = 최고 화질
    val container: String = "mp4",
    val audioFormat: String = "mp3",
    val compatH264: Boolean = true,      // 휴대폰 갤러리에서 잘 열리는 H.264 우선
    val subLangs: String = "",           // 비면 자막 없음
    val embedThumbnail: Boolean = true,
    val embedMetadata: Boolean = true,
    val playlistTitle: String = "",      // 재생목록이면 그 이름의 폴더에 저장
    val index: Int? = null,              // 재생목록 번호 (파일명 앞)
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("mode", mode); put("maxHeight", maxHeight); put("container", container)
        put("audioFormat", audioFormat); put("compatH264", compatH264); put("subLangs", subLangs)
        put("embedThumbnail", embedThumbnail); put("embedMetadata", embedMetadata)
        put("playlistTitle", playlistTitle); if (index != null) put("index", index)
    }

    companion object {
        fun fromJson(o: JSONObject?): DownloadOptions {
            if (o == null) return DownloadOptions()
            return DownloadOptions(
                mode = o.optString("mode", "video"),
                maxHeight = o.optInt("maxHeight", 0),
                container = o.optString("container", "mp4"),
                audioFormat = o.optString("audioFormat", "mp3"),
                compatH264 = o.optBoolean("compatH264", true),
                subLangs = o.optString("subLangs", ""),
                embedThumbnail = o.optBoolean("embedThumbnail", true),
                embedMetadata = o.optBoolean("embedMetadata", true),
                playlistTitle = o.optString("playlistTitle", ""),
                index = if (o.has("index")) o.optInt("index") else null,
            )
        }
    }
}

/** 파일·폴더 이름에 쓸 수 없는 글자를 바꾼다. */
fun sanitizeName(name: String): String {
    val cleaned = name.replace(Regex("""[\\/:*?"<>|\u0000-\u001f]"""), "_").trim().trimEnd('.')
    return cleaned.take(120).ifBlank { "TubeGet" }
}

object Args {
    const val P_PROGRESS = "TGP|"
    const val P_STREAMS = "TGR|"
    const val P_STAGE = "TGS|"
    const val P_FILE = "TGF|"

    private const val PROGRESS_TEMPLATE = "download:" + P_PROGRESS +
        "%(progress.status)s|%(progress.downloaded_bytes)s|%(progress.total_bytes)s" +
        "|%(progress.total_bytes_estimate)s|%(progress.speed)s|%(progress.eta)s" +
        "|%(progress.fragment_index)s|%(progress.fragment_count)s|%(progress.tmpfilename)s"

    private val PRINT_ARGS = listOf(
        "-O", "before_dl:" + P_STREAMS +
            "%(requested_formats.0.filesize,requested_formats.0.filesize_approx)s" +
            "|%(requested_formats.1.filesize,requested_formats.1.filesize_approx)s" +
            "|%(filesize,filesize_approx)s",
        "-O", "post_process:" + P_STAGE + "postprocess",
        "-O", "after_move:" + P_FILE + "%(filepath)s",
    )

    /** 다운로드 인자 (주소 제외). outDir 는 최종 저장 폴더, tempDir 는 받는 중인 조각 파일 폴더. */
    fun download(opts: DownloadOptions, outDir: String, tempDir: String): List<String> {
        val a = mutableListOf(
            "--newline",
            "--color", "never",
            "--encoding", "utf-8",
            "--progress",
            "--progress-template", PROGRESS_TEMPLATE,
        )
        a += PRINT_ARGS
        a += listOf(
            "--no-simulate",
            "--no-playlist",
            "--continue",
            "--no-mtime",
            "--windows-filenames", // 휴대폰 저장소에서도 문제없는 파일 이름
            "-P", outDir,
            "-P", "temp:$tempDir",
            "-o", outputTemplate(opts),
        )

        if (opts.mode == "audio") {
            a += listOf("-f", "ba/b", "-x")
            a += listOf("--audio-format", opts.audioFormat)
            if (opts.audioFormat in LOSSY_AUDIO) a += listOf("--audio-quality", "0")
            if (opts.embedMetadata) {
                if (opts.embedThumbnail && opts.audioFormat in THUMB_AUDIO) a += "--embed-thumbnail"
                a += "--embed-metadata"
            }
        } else {
            // 휴대폰에서는 고른 화질을 먼저 맞추고, 같은 화질 안에서 H.264 를 고른다
            val sort = mutableListOf<String>()
            if (opts.maxHeight > 0) sort += "res:${opts.maxHeight}"
            if (opts.compatH264) {
                sort += "vcodec:h264"; sort += "acodec:aac"
            }
            when (opts.container) {
                "mp4" -> sort += "ext:mp4:m4a"
                "webm" -> sort += "ext:webm:webm"
            }
            a += listOf("-f", "bv*+ba/b")
            if (sort.isNotEmpty()) a += listOf("-S", sort.joinToString(","))
            a += listOf("--merge-output-format", opts.container)
            if (opts.embedThumbnail && opts.container in THUMB_VIDEO) a += "--embed-thumbnail"
            if (opts.embedMetadata) a += "--embed-metadata"
        }

        val langs = opts.subLangs.split(',').map { it.trim() }.filter { it.isNotEmpty() }
        if (langs.isNotEmpty()) {
            a += listOf("--write-subs", "--write-auto-subs", "--sub-langs", langs.joinToString(","))
            if (opts.mode == "video") {
                a += listOf("--embed-subs", "--compat-options", "no-keep-subs")
            } else {
                a += listOf("--convert-subs", "srt")
            }
        }
        return a
    }

    fun outputTemplate(opts: DownloadOptions): String {
        var t = "%(title).150B [%(id)s].%(ext)s"
        if (opts.index != null) t = String.format(java.util.Locale.US, "%02d - ", opts.index) + t
        if (opts.playlistTitle.isNotBlank()) t = sanitizeName(opts.playlistTitle).replace("%", "%%") + "/" + t
        return t
    }

    /** 정보 조회 인자 */
    fun info(): List<String> = listOf(
        "--dump-single-json",
        "--flat-playlist",
        "--no-warnings",
        "--encoding", "utf-8",
    )
}

/** yt-dlp 출력 한 줄을 읽어 전체 진행률을 계산한다. 영상·음성을 따로 받아도 막대는 하나. */
class ProgressTracker {
    var fraction: Float? = null; private set
    var speed: Double? = null; private set
    var eta: Long? = null; private set
    var postprocessing = false; private set
    var finalPath: String? = null; private set

    private var streamSizes: List<Long?> = emptyList()
    private var currentTmp: String? = null
    private var partIndex = 0
    private var doneBytes = 0L
    private var lastTotal = 0L

    private fun num(s: String?): Double? {
        val t = s?.trim() ?: return null
        if (t.isEmpty() || t == "NA" || t == "None" || t == "null") return null
        return t.toDoubleOrNull()
    }

    /** 진행률이 바뀌었으면 true */
    fun feed(rawLine: String): Boolean {
        val line = rawLine.trim()
        when {
            line.startsWith(Args.P_STREAMS) -> {
                val p = line.removePrefix(Args.P_STREAMS).split('|')
                val s0 = num(p.getOrNull(0))?.toLong()
                val s1 = num(p.getOrNull(1))?.toLong()
                val single = num(p.getOrNull(2))?.toLong()
                streamSizes = if (s0 != null || s1 != null) listOf(s0, s1) else listOf(single)
                return false
            }
            line.startsWith(Args.P_STAGE) -> {
                postprocessing = true
                fraction = 1f
                speed = null; eta = null
                return true
            }
            line.startsWith(Args.P_FILE) -> {
                finalPath = line.removePrefix(Args.P_FILE).trim()
                return false
            }
            line.startsWith(Args.P_PROGRESS) -> {
                val p = line.removePrefix(Args.P_PROGRESS).split('|')
                val status = p.getOrNull(0) ?: ""
                val downloaded = num(p.getOrNull(1))
                val total = num(p.getOrNull(2)) ?: num(p.getOrNull(3))
                val fi = num(p.getOrNull(6))
                val fn = num(p.getOrNull(7))
                val tmp = p.getOrNull(8)?.trim()?.takeIf { it.isNotEmpty() && it != "NA" }
                if (tmp != null && currentTmp != null && tmp != currentTmp) {
                    partIndex++
                    doneBytes += lastTotal
                }
                if (tmp != null) currentTmp = tmp
                if (total != null) lastTotal = total.toLong()
                speed = num(p.getOrNull(4))
                eta = num(p.getOrNull(5))?.toLong()

                val parts = maxOf(1, streamSizes.size)
                val own: Float? = when {
                    status == "finished" -> 1f
                    total != null && total > 0 && downloaded != null -> (downloaded / total).toFloat()
                    fn != null && fn > 0 && fi != null -> (fi / fn).toFloat()
                    else -> null
                }
                val known = streamSizes.filterNotNull()
                fraction = if (known.size == parts && known.sum() > 0 && downloaded != null) {
                    ((doneBytes + (if (status == "finished") (total ?: downloaded) else downloaded)) / known.sum().toDouble())
                        .toFloat()
                } else if (own != null) {
                    (minOf(partIndex, parts - 1) + own) / parts
                } else null
                fraction = fraction?.coerceIn(0f, 1f)
                return true
            }
        }
        return false
    }
}
