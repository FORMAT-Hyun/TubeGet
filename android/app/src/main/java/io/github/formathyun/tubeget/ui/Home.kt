package io.github.formathyun.tubeget.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.filled.Share
import io.github.formathyun.tubeget.FileActions
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.formathyun.tubeget.AUDIO_FORMATS
import io.github.formathyun.tubeget.DownloadItem
import io.github.formathyun.tubeget.Downloads
import io.github.formathyun.tubeget.Engine
import io.github.formathyun.tubeget.LinkState
import io.github.formathyun.tubeget.MainViewModel
import io.github.formathyun.tubeget.MediaInfo
import io.github.formathyun.tubeget.R
import io.github.formathyun.tubeget.Settings
import io.github.formathyun.tubeget.Status
import io.github.formathyun.tubeget.VIDEO_CONTAINERS
import io.github.formathyun.tubeget.formatBytes
import io.github.formathyun.tubeget.formatDuration
import io.github.formathyun.tubeget.heightLabel

@Composable
fun HomeScreen(vm: MainViewModel, padding: PaddingValues) {
    val link by vm.link.collectAsState()
    val items by Downloads.items.collectAsState()
    val engine by Engine.state.collectAsState()
    // 진행 중·실패 항목 + 방금(30분 안에) 끝난 항목. 오래된 완료 항목은 [기록] 탭에만
    val recent = System.currentTimeMillis() - 30 * 60 * 1000L
    val queue = items.filter { it.status != Status.DONE || (it.finishedAt ?: 0L) > recent }
    var detail by remember { mutableStateOf<DownloadItem?>(null) }

    LazyColumn(
        contentPadding = PaddingValues(
            start = 16.dp, end = 16.dp,
            top = padding.calculateTopPadding() + 8.dp,
            bottom = padding.calculateBottomPadding() + 24.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item { LinkInput(vm) }

        if (engine is Engine.State.Starting) {
            item { EngineNotice(stringResource(R.string.engine_starting), busy = true) }
        } else if (engine is Engine.State.Failed) {
            item { EngineNotice(stringResource(R.string.engine_failed), busy = false) }
        }

        when (val s = link) {
            is LinkState.Idle -> Unit
            is LinkState.Loading -> item { LoadingCard(s.url, onCancel = vm::dismiss) }
            is LinkState.Error -> item { ErrorCard(s, onRetry = vm::retryLoad, onClose = vm::dismiss) }
            is LinkState.Loaded -> {
                item { MediaCard(s.info, vm) }
                if (s.info.isPlaylist) {
                    item {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                stringResource(R.string.selected_n, s.selected.size, s.info.entries.size),
                                color = TG.Muted, fontSize = 13.sp, modifier = Modifier.weight(1f),
                            )
                            TextButton(onClick = { vm.selectAll(s.selected.size != s.info.entries.size) }) {
                                Text(
                                    stringResource(
                                        if (s.selected.size == s.info.entries.size) R.string.select_none else R.string.select_all
                                    )
                                )
                            }
                        }
                    }
                    items(s.info.entries, key = { "e" + it.index }) { e ->
                        Row(
                            Modifier
                                .fillMaxWidth()
                                .clickable { vm.toggleEntry(e.index) }
                                .padding(vertical = 2.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Checkbox(checked = e.index in s.selected, onCheckedChange = { vm.toggleEntry(e.index) })
                            Text("${e.index}", color = TG.Muted, fontSize = 12.sp, modifier = Modifier.width(28.dp))
                            Thumb(e.thumbnail, Modifier.width(88.dp), corner = 6)
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text(e.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontSize = 14.sp)
                                val d = formatDuration(e.duration)
                                if (d.isNotEmpty()) Text(d, color = TG.Muted, fontSize = 12.sp)
                            }
                        }
                    }
                    item {
                        Button(
                            onClick = vm::download,
                            enabled = s.selected.isNotEmpty(),
                            modifier = Modifier.fillMaxWidth().height(52.dp),
                            shape = RoundedCornerShape(12.dp),
                        ) {
                            Icon(painterResource(R.drawable.ic_download), null, Modifier.size(20.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(stringResource(R.string.download_n, s.selected.size), fontSize = 16.sp)
                        }
                    }
                }
            }
        }

        if (queue.isEmpty() && link is LinkState.Idle) {
            item { EmptyGuide() }
        }

        if (queue.isNotEmpty()) {
            item {
                Text(
                    stringResource(R.string.queue_title, queue.size),
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
            items(queue, key = { it.id }) { item ->
                val ctx = LocalContext.current
                QueueRow(item, onClick = {
                    when (item.status) {
                        Status.FAILED -> detail = item
                        Status.DONE -> FileActions.open(ctx, item.filePath)
                        else -> Unit
                    }
                })
            }
        }
    }

    detail?.let { d -> ErrorDetailDialog(d, onDismiss = { detail = null }) }
}

@Composable
private fun LinkInput(vm: MainViewModel) {
    val clipboard = LocalClipboardManager.current
    val focus = LocalFocusManager.current
    var text by rememberSaveable { mutableStateOf("") }

    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Button(
            onClick = {
                val clip = clipboard.getText()?.text
                focus.clearFocus()
                vm.load(clip)
            },
            modifier = Modifier.fillMaxWidth().height(56.dp),
            shape = RoundedCornerShape(14.dp),
        ) {
            Icon(painterResource(R.drawable.ic_paste), null, Modifier.size(22.dp))
            Spacer(Modifier.width(10.dp))
            Text(stringResource(R.string.paste_link), fontSize = 17.sp, fontWeight = FontWeight.SemiBold)
        }
        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            placeholder = { Text(stringResource(R.string.link_hint), color = TG.Placeholder) },
            shape = RoundedCornerShape(12.dp),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Go),
            keyboardActions = KeyboardActions(onGo = {
                focus.clearFocus(); vm.load(text); text = ""
            }),
            trailingIcon = {
                if (text.isNotEmpty()) {
                    Row {
                        IconButton(onClick = { text = "" }) { Icon(Icons.Filled.Clear, stringResource(R.string.clear)) }
                        TextButton(onClick = { focus.clearFocus(); vm.load(text); text = "" }) {
                            Text(stringResource(R.string.load))
                        }
                    }
                }
            },
        )
    }
}

@Composable
private fun EngineNotice(text: String, busy: Boolean) {
    Card(colors = CardDefaults.cardColors(containerColor = TG.Surface)) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            if (busy) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
            else Text("!", color = TG.Danger, fontWeight = FontWeight.Bold)
            Spacer(Modifier.width(12.dp))
            Text(text, fontSize = 14.sp, color = TG.Muted)
        }
    }
}

@Composable
private fun EmptyGuide() {
    Column(
        Modifier.fillMaxWidth().padding(vertical = 40.dp, horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Icon(painterResource(R.drawable.ic_download), null, tint = TG.BorderStrong, modifier = Modifier.size(56.dp))
        Text(stringResource(R.string.empty_title), fontWeight = FontWeight.SemiBold, fontSize = 16.sp)
        Text(
            stringResource(R.string.empty_body),
            color = TG.Muted, fontSize = 14.sp,
            textAlign = androidx.compose.ui.text.style.TextAlign.Center,
        )
    }
}

@Composable
private fun LoadingCard(url: String, onCancel: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = TG.Surface)) {
        Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.5.dp)
            Spacer(Modifier.width(14.dp))
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.loading), fontWeight = FontWeight.SemiBold)
                Text(url, color = TG.Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            IconButton(onClick = onCancel) { Icon(Icons.Filled.Close, stringResource(R.string.cancel)) }
        }
    }
}

@Composable
private fun ErrorCard(s: LinkState.Error, onRetry: () -> Unit, onClose: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = TG.Surface),
        border = BorderStroke(1.dp, TG.AccentSoft),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.load_failed), fontWeight = FontWeight.SemiBold, color = TG.AccentText)
            Text(s.message, fontSize = 14.sp)
            Text(s.url, color = TG.Muted, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onRetry) { Text(stringResource(R.string.retry)) }
                OutlinedButton(onClick = onClose) { Text(stringResource(R.string.close)) }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun MediaCard(info: MediaInfo, vm: MainViewModel) {
    val prefs by Settings.prefs.collectAsState()
    Card(colors = CardDefaults.cardColors(containerColor = TG.Surface), shape = RoundedCornerShape(16.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Box {
                Thumb(
                    info.thumbnail, Modifier.fillMaxWidth(),
                    badge = if (info.isPlaylist) stringResource(R.string.playlist_count, info.entries.size)
                    else formatDuration(info.duration),
                )
                IconButton(
                    onClick = vm::dismiss,
                    modifier = Modifier.align(Alignment.TopEnd),
                ) {
                    Icon(
                        Icons.Filled.Close, stringResource(R.string.close),
                        tint = androidx.compose.ui.graphics.Color.White,
                        modifier = Modifier
                            .size(32.dp)
                            .background(androidx.compose.ui.graphics.Color(0x99000000), CircleShape)
                            .padding(5.dp),
                    )
                }
            }
            Column {
                Text(info.title, fontWeight = FontWeight.SemiBold, fontSize = 17.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                if (info.uploader.isNotEmpty()) Text(info.uploader, color = TG.Muted, fontSize = 13.sp)
            }

            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                val modes = listOf("video" to R.string.video, "audio" to R.string.audio)
                modes.forEachIndexed { i, (m, label) ->
                    SegmentedButton(
                        selected = prefs.mode == m,
                        onClick = { Settings.update { it.copy(mode = m) } },
                        shape = SegmentedButtonDefaults.itemShape(i, modes.size),
                        colors = SegmentedButtonDefaults.colors(
                            activeContainerColor = TG.AccentSoft,
                            activeContentColor = TG.AccentText,
                            activeBorderColor = TG.Accent,
                        ),
                    ) { Text(stringResource(label)) }
                }
            }

            if (prefs.mode == "video") {
                Section(stringResource(R.string.quality)) {
                    val choices = listOf(0) + info.heights
                    choices.forEach { h ->
                        val label = if (h == 0) stringResource(R.string.best) else heightLabel(h)
                        val size = formatBytes(info.videoSizes[h])
                        Choice(
                            text = if (size.isNotEmpty()) "$label · $size" else label,
                            selected = prefs.maxHeight == h ||
                                (h == 0 && prefs.maxHeight !in choices),
                            onClick = { Settings.update { it.copy(maxHeight = h) } },
                        )
                    }
                }
                Section(stringResource(R.string.format)) {
                    VIDEO_CONTAINERS.forEach { c ->
                        Choice(c.uppercase(), prefs.container == c) { Settings.update { it.copy(container = c) } }
                    }
                }
            } else {
                Section(stringResource(R.string.format)) {
                    AUDIO_FORMATS.forEach { f ->
                        val size = if (f == "mp3" || f == "flac") "" else formatBytes(info.audioSize)
                        Choice(
                            if (size.isNotEmpty()) "${f.uppercase()} · $size" else f.uppercase(),
                            prefs.audioFormat == f,
                        ) { Settings.update { it.copy(audioFormat = f) } }
                    }
                }
            }

            if (!info.isPlaylist) {
                Button(
                    onClick = vm::download,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = TG.Accent),
                ) {
                    Icon(painterResource(R.drawable.ic_download), null, Modifier.size(20.dp))
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.download), fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Section(title: String, content: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, color = TG.Muted, fontSize = 13.sp)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) { content() }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Choice(text: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected,
        onClick = onClick,
        label = { Text(text, fontSize = 13.sp) },
        colors = FilterChipDefaults.filterChipColors(
            selectedContainerColor = TG.AccentSoft,
            selectedLabelColor = TG.AccentText,
        ),
        border = FilterChipDefaults.filterChipBorder(
            enabled = true, selected = selected,
            borderColor = TG.BorderStrong, selectedBorderColor = TG.Accent,
        ),
    )
}

@Composable
private fun QueueRow(item: DownloadItem, onClick: () -> Unit) {
    val ctx = LocalContext.current
    Card(
        colors = CardDefaults.cardColors(containerColor = TG.Surface),
        modifier = Modifier.fillMaxWidth().clickable(
            enabled = item.status == Status.FAILED || item.status == Status.DONE, onClick = onClick,
        ),
    ) {
        Column(Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Thumb(item.thumbnail, Modifier.width(96.dp), corner = 6)
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(item.title, maxLines = 2, overflow = TextOverflow.Ellipsis, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                    Text(optionSummary(ctx, item.options), color = TG.Muted, fontSize = 12.sp, maxLines = 1)
                }
                when (item.status) {
                    Status.QUEUED, Status.RUNNING, Status.POSTPROCESS ->
                        IconButton(onClick = { Downloads.cancel(item.id) }) {
                            Icon(Icons.Filled.Close, stringResource(R.string.cancel), tint = TG.Muted)
                        }
                    Status.DONE ->
                        IconButton(onClick = { FileActions.share(ctx, item.filePath) }) {
                            Icon(Icons.Filled.Share, stringResource(R.string.share), tint = TG.Muted)
                        }
                    else -> Row {
                        IconButton(onClick = { Downloads.retry(item.id) }) {
                            Icon(Icons.Filled.Refresh, stringResource(R.string.retry), tint = TG.Muted)
                        }
                        IconButton(onClick = { Downloads.remove(item.id) }) {
                            Icon(Icons.Filled.Delete, stringResource(R.string.remove), tint = TG.Muted)
                        }
                    }
                }
            }
            if (item.active) {
                Spacer(Modifier.height(8.dp))
                val p = item.progress
                if (p == null || item.status == Status.POSTPROCESS) {
                    LinearProgressIndicator(Modifier.fillMaxWidth(), color = TG.Accent, trackColor = TG.Surface2)
                } else {
                    LinearProgressIndicator(
                        progress = { p }, modifier = Modifier.fillMaxWidth(),
                        color = TG.Accent, trackColor = TG.Surface2,
                    )
                }
            }
            val line = statusLine(ctx, item)
            if (line.isNotEmpty()) {
                Spacer(Modifier.height(6.dp))
                Text(
                    line,
                    fontSize = 12.sp,
                    color = when (item.status) {
                        Status.FAILED -> TG.Danger
                        Status.DONE -> TG.Success
                        else -> TG.Muted
                    },
                    maxLines = 3, overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

@Composable
private fun ErrorDetailDialog(item: DownloadItem, onDismiss: () -> Unit) {
    val clipboard = LocalClipboardManager.current
    val ctx = LocalContext.current
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.error_detail)) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(item.error.orEmpty())
                Text(item.url, color = TG.Muted, fontSize = 12.sp)
            }
        },
        confirmButton = {
            TextButton(onClick = { Downloads.retry(item.id); onDismiss() }) { Text(stringResource(R.string.retry)) }
        },
        dismissButton = {
            TextButton(onClick = {
                clipboard.setText(androidx.compose.ui.text.AnnotatedString(item.log.ifEmpty { item.error.orEmpty() }))
                android.widget.Toast.makeText(ctx, R.string.copied, android.widget.Toast.LENGTH_SHORT).show()
            }) { Text(stringResource(R.string.copy_log)) }
        },
        containerColor = TG.Surface,
    )
}
