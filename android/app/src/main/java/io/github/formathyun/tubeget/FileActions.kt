package io.github.formathyun.tubeget

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.webkit.MimeTypeMap
import android.widget.Toast
import androidx.core.content.FileProvider
import java.io.File

/** 받은 파일 열기·공유하기 */
object FileActions {
    private fun uri(context: Context, file: File): Uri =
        FileProvider.getUriForFile(context, context.packageName + ".files", file)

    private fun mime(file: File): String =
        MimeTypeMap.getSingleton().getMimeTypeFromExtension(file.extension.lowercase()) ?: when (file.extension.lowercase()) {
            "mkv" -> "video/x-matroska"
            "opus" -> "audio/ogg"
            else -> "*/*"
        }

    fun viewIntent(context: Context, path: String): Intent? {
        val f = File(path)
        if (!f.exists()) return null
        return Intent(Intent.ACTION_VIEW)
            .setDataAndType(uri(context, f), mime(f))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    fun open(context: Context, path: String?) {
        val intent = path?.let { viewIntent(context, it) }
        if (intent == null) {
            Toast.makeText(context, R.string.file_missing, Toast.LENGTH_SHORT).show(); return
        }
        try {
            context.startActivity(intent)
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(context, R.string.no_app_to_open, Toast.LENGTH_SHORT).show()
        }
    }

    fun share(context: Context, path: String?) {
        val f = path?.let { File(it) }
        if (f == null || !f.exists()) {
            Toast.makeText(context, R.string.file_missing, Toast.LENGTH_SHORT).show(); return
        }
        val send = Intent(Intent.ACTION_SEND)
            .setType(mime(f))
            .putExtra(Intent.EXTRA_STREAM, uri(context, f))
            .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        context.startActivity(Intent.createChooser(send, null).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }
}
