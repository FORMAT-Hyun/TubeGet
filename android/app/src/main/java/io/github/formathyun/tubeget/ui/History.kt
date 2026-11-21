package io.github.formathyun.tubeget.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.formathyun.tubeget.DownloadItem
import io.github.formathyun.tubeget.Downloads
import io.github.formathyun.tubeget.FileActions
import io.github.formathyun.tubeget.R
import io.github.formathyun.tubeget.Status
import java.io.File
import java.text.DateFormat
import java.util.Date

@Composable
fun HistoryScreen(padding: PaddingValues) {
    val items by Downloads.items.collectAsState()
    val done = items.filter { it.status == Status.DONE }.sortedByDescending { it.finishedAt ?: it.createdAt }
    var confirmClear by remember { mutableStateOf(false) }

    if (done.isEmpty()) {
        Box(Modifier.fillMaxSize().padding(padding).padding(32.dp), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(painterResource(R.drawable.ic_history), null, tint = TG.BorderStrong, modifier = Modifier.size(56.dp))
                Text(stringResource(R.string.history_empty), color = TG.Muted, textAlign = TextAlign.Center)
            }
        }
        return
    }

    LazyColumn(
        contentPadding = PaddingValues(
            start = 16.dp, end = 16.dp,
            top = padding.calculateTopPadding() + 8.dp,
            bottom = padding.calculateBottomPadding() + 24.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    stringResource(R.string.history_count, done.size),
                    fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f),
                )
                TextButton(onClick = { confirmClear = true }) { Text(stringResource(R.string.clear_history)) }
            }
        }
        items(done, key = { it.id }) { HistoryRow(it) }
        item {
            Text(
                stringResource(R.string.saved_in, "Download/TubeGet"),
                color = TG.Placeholder, fontSize = 12.sp,
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                textAlign = TextAlign.Center,
            )
        }
    }

    if (confirmClear) {
        AlertDialog(
            onDismissRequest = { confirmClear = false },
            text = { Text(stringResource(R.string.clear_history_confirm)) },
            confirmButton = {
                TextButton(onClick = { Downloads.clearFinished(); confirmClear = false }) {
                    Text(stringResource(R.string.clear_history))
                }
            },
            dismissButton = { TextButton(onClick = { confirmClear = false }) { Text(stringResource(R.string.cancel)) } },
            containerColor = TG.Surface,
        )
    }
}

@Composable
private fun HistoryRow(item: DownloadItem) {
    val ctx = LocalContext.current
    var menu by remember { mutableStateOf(false) }
    var confirmDelete by remember { mutableStateOf(false) }
    val exists = item.filePath?.let { File(it).exists() } == true

    Card(
        colors = CardDefaults.cardColors(containerColor = TG.Surface),
        modifier = Modifier.fillMaxWidth().clickable { FileActions.open(ctx, item.filePath) },
    ) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Thumb(item.thumbnail, Modifier.width(96.dp), corner = 6)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                val date = item.finishedAt?.let { DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(it)) }
                Text(
                    listOfNotNull(optionSummary(ctx, item.options), date).joinToString(" · "),
                    color = TG.Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis,
                )
                if (!exists) Text(stringResource(R.string.file_missing), color = TG.Warning, fontSize = 12.sp)
            }
            IconButton(onClick = { FileActions.share(ctx, item.filePath) }, enabled = exists) {
                Icon(Icons.Filled.Share, stringResource(R.string.share), tint = TG.Muted)
            }
            Box {
                IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, null, tint = TG.Muted) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.redownload)) },
                        onClick = { menu = false; Downloads.retry(item.id) },
                    )
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.remove_from_list)) },
                        onClick = { menu = false; Downloads.remove(item.id) },
                    )
                    if (exists) DropdownMenuItem(
                        text = { Text(stringResource(R.string.delete_file), color = TG.Danger) },
                        onClick = { menu = false; confirmDelete = true },
                    )
                }
            }
        }
    }

    if (confirmDelete) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            text = { Text(stringResource(R.string.delete_file_confirm, item.title)) },
            confirmButton = {
                TextButton(onClick = { Downloads.remove(item.id, deleteFile = true); confirmDelete = false }) {
                    Text(stringResource(R.string.delete_file), color = TG.Danger)
                }
            },
            dismissButton = { TextButton(onClick = { confirmDelete = false }) { Text(stringResource(R.string.cancel)) } },
            containerColor = TG.Surface,
        )
    }
}
