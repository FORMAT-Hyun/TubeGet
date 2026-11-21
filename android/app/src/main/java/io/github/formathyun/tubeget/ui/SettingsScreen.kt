package io.github.formathyun.tubeget.ui

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.appcompat.app.AppCompatDelegate
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.os.LocaleListCompat
import io.github.formathyun.tubeget.BuildConfig
import io.github.formathyun.tubeget.Engine
import io.github.formathyun.tubeget.R
import io.github.formathyun.tubeget.Settings
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(padding: PaddingValues) {
    val prefs by Settings.prefs.collectAsState()
    val version by Engine.version.collectAsState()
    val updating by Engine.updating.collectAsState()
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()

    LazyColumn(
        contentPadding = PaddingValues(
            start = 16.dp, end = 16.dp,
            top = padding.calculateTopPadding() + 8.dp,
            bottom = padding.calculateBottomPadding() + 32.dp,
        ),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Group(stringResource(R.string.settings_language)) {
                val current = AppCompatDelegate.getApplicationLocales().toLanguageTags()
                var lang by remember { mutableStateOf(current.substringBefore('-').ifEmpty { "" }) }
                val langs = listOf("" to stringResource(R.string.lang_auto), "ko" to "한국어", "en" to "English")
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    langs.forEachIndexed { i, (code, label) ->
                        SegmentedButton(
                            selected = lang == code,
                            onClick = {
                                lang = code
                                AppCompatDelegate.setApplicationLocales(
                                    if (code.isEmpty()) LocaleListCompat.getEmptyLocaleList()
                                    else LocaleListCompat.forLanguageTags(code)
                                )
                            },
                            shape = SegmentedButtonDefaults.itemShape(i, langs.size),
                            colors = segColors(),
                        ) { Text(label, fontSize = 13.sp) }
                    }
                }
            }
        }

        item {
            Group(stringResource(R.string.settings_download)) {
                Text(stringResource(R.string.concurrent), fontSize = 14.sp)
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    (1..3).forEach { n ->
                        SegmentedButton(
                            selected = prefs.maxConcurrent == n,
                            onClick = { Settings.update { it.copy(maxConcurrent = n) } },
                            shape = SegmentedButtonDefaults.itemShape(n - 1, 3),
                            colors = segColors(),
                        ) { Text("$n") }
                    }
                }
                Toggle(
                    stringResource(R.string.compat_h264), stringResource(R.string.compat_h264_desc), prefs.compatH264,
                ) { v -> Settings.update { it.copy(compatH264 = v) } }
                Toggle(
                    stringResource(R.string.playlist_folder), null, prefs.playlistFolder,
                ) { v -> Settings.update { it.copy(playlistFolder = v) } }
                Text(stringResource(R.string.card_options_note), color = TG.Muted, fontSize = 13.sp)
            }
        }

        item {
            Group("yt-dlp") {
                Text(stringResource(R.string.ytdlp_version, version.ifEmpty { "-" }), fontSize = 14.sp)
                Toggle(stringResource(R.string.auto_update), null, prefs.autoUpdate) { v ->
                    Settings.update { it.copy(autoUpdate = v) }
                }
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            val r = Engine.update()
                            Toast.makeText(
                                ctx,
                                when (r) {
                                    true -> R.string.update_done
                                    false -> R.string.update_latest
                                    null -> R.string.update_failed
                                },
                                Toast.LENGTH_SHORT,
                            ).show()
                        }
                    },
                    enabled = !updating,
                ) {
                    if (updating) {
                        CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                        Spacer(Modifier.width(8.dp))
                        Text(stringResource(R.string.updating))
                    } else {
                        Text(stringResource(R.string.update_now))
                    }
                }
                Text(stringResource(R.string.update_hint), color = TG.Muted, fontSize = 12.sp)
            }
        }

        item {
            Group(stringResource(R.string.about)) {
                Text(stringResource(R.string.app_version, BuildConfig.VERSION_NAME), fontWeight = FontWeight.SemiBold)
                fun open(url: String) = runCatching {
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }
                // GitHub 저장소: 소스, 새 버전(릴리스), 문제 신고
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { open(REPO_URL) }) { Text(stringResource(R.string.github_repo)) }
                    OutlinedButton(onClick = { open("$REPO_URL/releases") }) { Text(stringResource(R.string.github_releases)) }
                }
                Text(
                    REPO_URL.removePrefix("https://"),
                    color = TG.AccentText, fontSize = 13.sp,
                    modifier = Modifier.clickable { open(REPO_URL) },
                )
                Text(stringResource(R.string.licenses), color = TG.Muted, fontSize = 12.sp)
            }
        }
    }
}

const val REPO_URL = "https://github.com/FORMAT-Hyun/TubeGet"

@Composable
private fun segColors() = SegmentedButtonDefaults.colors(
    activeContainerColor = TG.AccentSoft,
    activeContentColor = TG.AccentText,
    activeBorderColor = TG.Accent,
)

@Composable
private fun Group(title: String, content: @Composable () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = TG.Surface), shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, fontWeight = FontWeight.SemiBold, color = TG.AccentText, fontSize = 14.sp)
            content()
        }
    }
}

@Composable
private fun Toggle(title: String, desc: String?, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        Modifier.fillMaxWidth().clickable { onChange(!checked) },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f).padding(end = 12.dp)) {
            Text(title, fontSize = 15.sp)
            if (desc != null) Text(desc, color = TG.Muted, fontSize = 12.sp)
        }
        Switch(
            checked = checked, onCheckedChange = onChange,
            colors = SwitchDefaults.colors(checkedTrackColor = TG.Accent),
        )
    }
}
