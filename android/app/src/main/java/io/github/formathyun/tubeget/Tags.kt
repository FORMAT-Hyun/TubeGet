package io.github.formathyun.tubeget

/** 태그(제목·아티스트·앨범·연도) 추측과 yt-dlp 인자 (PC 판 core/tags.py 와 같은 규칙). */
object Tags {
    val FIELDS = listOf("title", "artist", "album", "year")
    private val META_KEY = mapOf("title" to "meta_title", "artist" to "meta_artist", "album" to "meta_album", "year" to "meta_date")

    private const val TAIL_WORDS = "(?:official\\s*)?(?:music\\s*)?(?:video|audio|mv|m/v|lyrics?|lyric\\s*video|visuali[sz]er" +
        "|performance\\s*video|hd|4k)"
    const val CLEAN_RE_TEXT = "(?i)\\s*[\\(\\[【]$TAIL_WORDS[^\\)\\]】]*[\\)\\]】]"
    private val CLEAN_RE = Regex(CLEAN_RE_TEXT)
    private val SPLIT_RE = Regex("^(.+?)\\s+[-–—]\\s+(.+)$")
    private val TOPIC_RE = Regex("\\s*-\\s*Topic$")

    fun cleanTitle(text: String): String =
        CLEAN_RE.replace(text, "").replace(Regex("\\s{2,}"), " ").trim(' ', '-', '|')

    /** 제목에서 '아티스트 - 곡명'을 나누고 (Official Video) 같은 꼬리표를 지운 추천 값 */
    fun guess(info: MediaInfo): Map<String, String> {
        var title = info.track.ifBlank { info.title }
        var artist = info.artist.ifBlank { info.uploader }
        if (info.track.isBlank()) {
            SPLIT_RE.find(info.title)?.let { m ->
                artist = m.groupValues[1].trim(); title = m.groupValues[2].trim()
            }
        }
        return mapOf(
            "title" to cleanTitle(title),
            "artist" to TOPIC_RE.replace(artist, "").trim(),
            "album" to info.album,
            "year" to info.year,
        )
    }

    private fun literal(value: String): String {
        val v = value.replace("\r", " ").replace("\n", " ").trimEnd('\\')
        return "#" + v.replace("%", "%%").replace(":", "\\:")
    }

    fun customArgs(values: Map<String, String>): List<String> {
        val a = mutableListOf<String>()
        for (f in FIELDS) {
            val v = values[f]?.trim() ?: continue
            val key = META_KEY.getValue(f)
            a += "--parse-metadata"
            a += if (v.isNotEmpty()) "${literal(v)}:#(?P<$key>.*)" else ":(?P<$key>)"
        }
        return a
    }

    /** 재생목록처럼 영상마다 값을 볼 수 없을 때: yt-dlp 가 영상마다 자동으로 정리 */
    fun smartArgs(): List<String> = listOf(
        "--parse-metadata", "%(track,title)s:%(meta_title)s",
        "--parse-metadata", "%(artist,creator,uploader)s:%(meta_artist)s",
        "--parse-metadata", "title:(?P<meta_artist>.+?) [-–—] (?P<meta_title>.+)",
        "--replace-in-metadata", "meta_title", CLEAN_RE_TEXT, "",
        "--replace-in-metadata", "meta_artist", " - Topic$", "",
    )
}
