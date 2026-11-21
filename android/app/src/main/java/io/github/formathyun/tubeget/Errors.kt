package io.github.formathyun.tubeget

import android.content.Context

/** yt-dlp 오류 로그 → 알기 쉬운 안내 (PC 판 core/errors.py 와 같은 규칙). */
object Errors {
    private val RULES: List<Pair<Regex, Int>> = listOf(
        r("""confirm you.?re not a bot|Sign in to confirm you""") to R.string.err_bot,
        r("""confirm your age|age.?restricted|inappropriate for some users""") to R.string.err_age,
        r("""Private video|This video is private""") to R.string.err_private,
        r("""members.?only|Join this channel|available to this channel's members""") to R.string.err_members,
        r("""Premieres in|This live event will begin|will begin in""") to R.string.err_premiere,
        r("""(?:video|stream) is (?:currently )?live|is a live (?:stream|broadcast)|live streams? (?:are|is) not supported""") to R.string.err_live,
        r("""DRM""") to R.string.err_drm,
        r("""not available in your country|blocked it in your country|geo.?restrict""") to R.string.err_geo,
        r("""Video unavailable|This video is unavailable|has been removed|account associated with this video has been terminated""") to R.string.err_unavailable,
        r("""Requested format is not available""") to R.string.err_format,
        r("""HTTP Error 403|403: Forbidden""") to R.string.err_403,
        r("""HTTP Error 429|Too Many Requests""") to R.string.err_429,
        r("""HTTP Error 404|404: Not Found""") to R.string.err_404,
        r("""Unsupported URL|is not a valid URL""") to R.string.err_unsupported,
        r("""getaddrinfo failed|Name or service not known|Temporary failure in name resolution|Failed to resolve|Connection refused|timed out|Unable to download webpage|No address associated""") to R.string.err_network,
        r("""No space left on device|disk is full|\[Errno 28\]""") to R.string.err_space,
        r("""Permission denied|\[Errno 13\]|Operation not permitted|\[Errno 1\]""") to R.string.err_permission,
        r("""File name too long|\[Errno 36\]""") to R.string.err_name_long,
    )

    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    fun lastErrorLine(text: String): String? {
        val lines = text.lines().map { it.trim() }.filter { it.isNotEmpty() }
        lines.lastOrNull { it.startsWith("ERROR:") }?.let { return it.removePrefix("ERROR:").trim() }
        return lines.lastOrNull()
    }

    fun explain(context: Context, text: String?): String {
        val log = text.orEmpty()
        val err = lastErrorLine(log).orEmpty()
        for (hay in listOf(err, log)) {
            if (hay.isEmpty()) continue
            for ((re, id) in RULES) if (re.containsMatchIn(hay)) return context.getString(id)
        }
        if (err.isNotEmpty()) {
            val short = err.replace(Regex("""^\[[^\]]+\]\s*"""), "")
                .replace(Regex("""\s*;?\s*please report this issue.*$""", RegexOption.IGNORE_CASE), "")
            return context.getString(R.string.err_generic, short.take(200))
        }
        return context.getString(R.string.err_unknown)
    }
}
