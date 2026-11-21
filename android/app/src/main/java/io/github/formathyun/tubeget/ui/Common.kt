package io.github.formathyun.tubeget.ui

import android.content.Context
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import io.github.formathyun.tubeget.DownloadItem
import io.github.formathyun.tubeget.DownloadOptions
import io.github.formathyun.tubeget.R
import io.github.formathyun.tubeget.Status
import io.github.formathyun.tubeget.formatBytes
import io.github.formathyun.tubeget.heightLabel

@Composable
fun Thumb(url: String?, modifier: Modifier = Modifier, badge: String? = null, corner: Int = 10) {
    Box(
        modifier
            .aspectRatio(16f / 9f)
            .clip(RoundedCornerShape(corner.dp))
            .background(TG.Surface2)
    ) {
        if (url != null) {
            AsyncImage(
                model = url,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
        }
        if (!badge.isNullOrEmpty()) {
            Text(
                badge,
                color = Color.White,
                fontSize = 11.sp,
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(5.dp)
                    .background(Color(0xCC000000), RoundedCornerShape(4.dp))
                    .padding(horizontal = 5.dp, vertical = 1.dp),
            )
        }
    }
}

fun optionSummary(context: Context, o: DownloadOptions): String {
    val base = if (o.mode == "audio") {
        context.getString(R.string.summary_audio, o.audioFormat.uppercase()) +
            if (o.audioFormat in io.github.formathyun.tubeget.LOSSY_AUDIO && o.audioQuality != "0") " · " + o.audioQuality.removeSuffix("K") + "k" else ""
    } else {
        val q = if (o.maxHeight > 0) heightLabel(o.maxHeight).substringBefore(' ') else context.getString(R.string.best)
        context.getString(R.string.summary_video, q, o.container.uppercase())
    }
    val parts = mutableListOf(base)
    if (o.subLangs.isNotBlank()) parts += context.getString(R.string.summary_subs, o.subLangs)
    if (o.dubLang.isNotBlank()) parts += context.getString(R.string.dub_short, o.dubLang)
    if (!o.embedMetadata) parts += context.getString(R.string.summary_no_tags)
    return parts.joinToString(" · ")
}

fun statusLine(context: Context, item: DownloadItem): String = when (item.status) {
    Status.QUEUED -> context.getString(R.string.status_waiting)
    Status.POSTPROCESS -> context.getString(R.string.status_converting)
    Status.CANCELED -> context.getString(R.string.status_canceled)
    Status.FAILED -> item.error ?: context.getString(R.string.err_unknown)
    Status.DONE -> context.getString(R.string.status_done)
    Status.RUNNING -> {
        val p = item.progress
        if (p == null) context.getString(R.string.status_starting) else buildString {
            append((p * 100).toInt()).append('%')
            item.speed?.takeIf { it > 0 }?.let { append(" · ").append(formatBytes(it.toLong())).append("/s") }
            item.eta?.takeIf { it > 0 }?.let { e ->
                append(" · ")
                append(context.getString(R.string.eta_left, if (e >= 60) "${e / 60}:${"%02d".format(e % 60)}" else "${e}s"))
            }
        }
    }
}
