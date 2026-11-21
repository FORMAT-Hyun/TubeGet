package io.github.formathyun.tubeget

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.launch

/** 화면을 꺼도 다운로드가 계속되게 붙잡아 두는 서비스 (알림에 진행률 표시). */
class DownloadService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var job: Job? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Notifier.ensureChannels(this)
        val first = Notifier.progress(this, Downloads.items.value)
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0
        ServiceCompat.startForeground(this, Notifier.ID_PROGRESS, first, type)
        if (job == null) {
            @OptIn(kotlinx.coroutines.FlowPreview::class)
            job = scope.launch {
                Downloads.items.debounce(500).collect { list ->
                    if (list.none { it.active }) {
                        ServiceCompat.stopForeground(this@DownloadService, ServiceCompat.STOP_FOREGROUND_REMOVE)
                        stopSelf()
                    } else {
                        NotificationManagerCompat.from(this@DownloadService).let { nm ->
                            if (nm.areNotificationsEnabled()) {
                                runCatching { nm.notify(Notifier.ID_PROGRESS, Notifier.progress(this@DownloadService, list)) }
                            }
                        }
                    }
                }
            }
        }
        return START_NOT_STICKY
    }

    override fun onDestroy() {
        scope.cancel()
        super.onDestroy()
    }
}

object Notifier {
    const val ID_PROGRESS = 1
    private const val CH_PROGRESS = "progress"
    private const val CH_DONE = "done"

    fun ensureChannels(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val nm = context.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CH_PROGRESS, context.getString(R.string.ch_progress), NotificationManager.IMPORTANCE_LOW)
        )
        nm.createNotificationChannel(
            NotificationChannel(CH_DONE, context.getString(R.string.ch_done), NotificationManager.IMPORTANCE_DEFAULT)
        )
    }

    private fun openApp(context: Context): PendingIntent = PendingIntent.getActivity(
        context, 0,
        Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    fun progress(context: Context, list: List<DownloadItem>): Notification {
        val active = list.filter { it.active }
        val runningItems = active.filter { it.status != Status.QUEUED }
        val title = if (active.size <= 1) active.firstOrNull()?.title ?: context.getString(R.string.app_name)
        else context.getString(R.string.notif_active_count, active.size)
        val fracs = runningItems.mapNotNull { it.progress }
        val b = NotificationCompat.Builder(context, CH_PROGRESS)
            .setSmallIcon(R.drawable.ic_stat_download)
            .setContentTitle(title)
            .setContentIntent(openApp(context))
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
        if (fracs.isNotEmpty()) {
            val pct = (fracs.average() * 100).toInt()
            b.setProgress(100, pct, false).setContentText("$pct%")
        } else {
            b.setProgress(0, 0, true).setContentText(context.getString(R.string.status_waiting))
        }
        return b.build()
    }

    private fun canNotify(context: Context) = NotificationManagerCompat.from(context).areNotificationsEnabled()

    fun finished(context: Context, item: DownloadItem) {
        if (!canNotify(context)) return
        ensureChannels(context)
        val tap = item.filePath?.let { FileActions.viewIntent(context, it) }
        val pi = if (tap != null) PendingIntent.getActivity(
            context, item.id.hashCode(), tap, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        ) else openApp(context)
        val n = NotificationCompat.Builder(context, CH_DONE)
            .setSmallIcon(R.drawable.ic_stat_download)
            .setContentTitle(context.getString(R.string.notif_done))
            .setContentText(item.title)
            .setContentIntent(pi)
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(context).notify(item.id.hashCode(), n) }
    }

    fun failed(context: Context, item: DownloadItem) {
        if (!canNotify(context)) return
        ensureChannels(context)
        val n = NotificationCompat.Builder(context, CH_DONE)
            .setSmallIcon(R.drawable.ic_stat_download)
            .setContentTitle(context.getString(R.string.notif_failed, item.title))
            .setContentText(item.error)
            .setStyle(NotificationCompat.BigTextStyle().bigText(item.error))
            .setContentIntent(openApp(context))
            .setAutoCancel(true)
            .build()
        runCatching { NotificationManagerCompat.from(context).notify(item.id.hashCode(), n) }
    }
}
