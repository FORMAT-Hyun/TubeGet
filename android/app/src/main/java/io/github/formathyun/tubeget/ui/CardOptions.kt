package io.github.formathyun.tubeget.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import io.github.formathyun.tubeget.LinkState
import io.github.formathyun.tubeget.MainViewModel
import io.github.formathyun.tubeget.MediaInfo
import io.github.formathyun.tubeget.OUT_DIR_CHOICES
import io.github.formathyun.tubeget.Prefs
import io.github.formathyun.tubeget.R
import io.github.formathyun.tubeget.Settings
import io.github.formathyun.tubeget.Tags
import java.util.Locale

private val COMMON_LANGS = listOf("ko", "en", "ja", "zh-Hans", "zh-Hant", "es", "fr", "de", "ru", "pt", "vi", "th", "id")
private val PRIORITY_AUTO = listOf("ko", "en", "ja")

/** 언어 코드 → 현재 앱 언어로 된 이름 (ko → 한국어 / Korean) */
@Composable
fun langName(code: String): String {
    val ui = LocalContext.current.resources.configuration.locales[0]
    val base = code.removeSuffix("-orig")
    val name = Locale.forLanguageTag(base).getDisplayName(ui)
    return if (name.isBlank() || name == base) code else name.replaceFirstChar { it.titlecase(ui) }
}

private fun codes(s: String) = s.split(',').map { it.trim() }.filter { it.isNotEmpty() }

/** 영상 카드 아래의 '저장 위치 / 자막·더빙 / 태그' 줄 (PC 판 툴바와 같은 항목) */
@Composable
fun CardOptionRows(info: MediaInfo, link: LinkState.Loaded, vm: MainViewModel) {
    val prefs by Settings.prefs.collectAsState()
    var sheet by remember { mutableStateOf<String?>(null) }

    Column {
        HorizontalDivider(color = TG.Border)
        OptionRow(stringResource(R.string.save_to), prefs.outDir) { sheet = "dir" }
        HorizontalDivider(color = TG.Border)
        OptionRow(stringResource(R.string.subs_dub), subsSummary(prefs)) { sheet = "subs" }
        HorizontalDivider(color = TG.Border)
        val tagText = when {
            !prefs.tags -> stringResource(R.string.off)
            info.isPlaylist -> stringResource(R.string.tags_auto)
            else -> listOf(link.tags["artist"], link.tags["title"]).filter { !it.isNullOrBlank() }
                .joinToString(" / ").ifEmpty { stringResource(R.string.on) }
        }
        OptionRow(stringResource(R.string.tags), tagText) { sheet = "tags" }
        HorizontalDivider(color = TG.Border)
    }

    when (sheet) {
        "dir" -> SaveDirSheet(prefs) { sheet = null }
        "subs" -> SubsSheet(info, prefs) { sheet = null }
        "tags" -> TagsSheet(info, link, vm, prefs) { sheet = null }
    }
}

@Composable
private fun subsSummary(p: Prefs): String {
    val langs = codes(p.subLangs)
    val parts = mutableListOf<String>()
    if (langs.isNotEmpty()) {
        val names = langs.take(2).map { langName(it) }.joinToString(", ") + if (langs.size > 2) " +${langs.size - 2}" else ""
        val mode = when (if (p.mode == "audio") "file" else p.subMode) {
            "file" -> stringResource(R.string.sub_mode_file_short)
            "both" -> stringResource(R.string.sub_mode_both_short)
            else -> stringResource(R.string.sub_mode_embed_short)
        }
        parts += "$names ($mode)"
    }
    if (p.dubLang.isNotBlank()) parts += stringResource(R.string.dub_short, langName(p.dubLang))
    return parts.joinToString(" · ").ifEmpty { stringResource(R.string.none) }
}

@Composable
private fun OptionRow(title: String, value: String, onClick: () -> Unit) {
    Row(
        Modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .clickable(onClick = onClick)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(title, color = TG.Muted, fontSize = 14.sp, modifier = Modifier.width(96.dp))
        Text(
            value, fontWeight = FontWeight.SemiBold, fontSize = 14.sp,
            maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f),
        )
        Icon(Icons.AutoMirrored.Filled.KeyboardArrowRight, null, tint = TG.Muted)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Sheet(title: String, onDismiss: () -> Unit, content: @Composable () -> Unit) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
        containerColor = TG.Surface,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .navigationBarsPadding()
                .padding(bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(title, fontWeight = FontWeight.Bold, fontSize = 18.sp, modifier = Modifier.padding(bottom = 8.dp))
            content()
            Spacer(Modifier.padding(4.dp))
            Button(onClick = onDismiss, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) {
                Text(stringResource(R.string.done))
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, color = TG.AccentText, fontWeight = FontWeight.SemiBold, fontSize = 14.sp,
        modifier = Modifier.padding(top = 10.dp, bottom = 2.dp))
}

@Composable
private fun CheckRow(text: String, checked: Boolean, sub: String? = null, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!checked) }, verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked, onChange, colors = CheckboxDefaults.colors(checkedColor = TG.Accent))
        Column(Modifier.weight(1f)) {
            Text(text, fontSize = 15.sp)
            if (sub != null) Text(sub, color = TG.Muted, fontSize = 12.sp)
        }
    }
}

@Composable
private fun RadioRow(text: String, selected: Boolean, sub: String? = null, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick), verticalAlignment = Alignment.CenterVertically) {
        RadioButton(selected, onClick, colors = RadioButtonDefaults.colors(selectedColor = TG.Accent))
        Column(Modifier.weight(1f)) {
            Text(text, fontSize = 15.sp)
            if (sub != null) Text(sub, color = TG.Muted, fontSize = 12.sp)
        }
    }
}

// ---- 저장 위치 ----------------------------------------------------------------

@Composable
private fun SaveDirSheet(prefs: Prefs, onDismiss: () -> Unit) {
    var custom by remember { mutableStateOf(if (prefs.outDir in OUT_DIR_CHOICES) "" else prefs.outDir.removePrefix("Download/")) }
    Sheet(stringResource(R.string.save_to), onDismiss) {
        OUT_DIR_CHOICES.forEach { d ->
            RadioRow(d, prefs.outDir == d) { Settings.update { it.copy(outDir = d) }; custom = "" }
        }
        SectionTitle(stringResource(R.string.custom_folder))
        OutlinedTextField(
            value = custom,
            onValueChange = { t ->
                custom = t
                val name = io.github.formathyun.tubeget.sanitizeName(t).takeIf { t.isNotBlank() }
                if (name != null) Settings.update { it.copy(outDir = "Download/$name") }
            },
            prefix = { Text("Download/") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(10.dp),
        )
        Text(stringResource(R.string.save_dir_note), color = TG.Muted, fontSize = 12.sp, modifier = Modifier.padding(top = 6.dp))
    }
}

// ---- 자막 / 더빙 ----------------------------------------------------------------

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SubsSheet(info: MediaInfo, prefs: Prefs, onDismiss: () -> Unit) {
    val selected = codes(prefs.subLangs)
    fun setSubs(list: List<String>) = Settings.update { p ->
        p.copy(subLangs = list.distinct().joinToString(","), autoSubs = true)
    }
    fun toggle(code: String, on: Boolean) = setSubs(if (on) selected + code else selected - code)

    Sheet(stringResource(R.string.subs_dub), onDismiss) {
        SectionTitle(stringResource(R.string.subs_section))
        RadioRow(stringResource(R.string.none), selected.isEmpty()) { setSubs(emptyList()) }

        if (info.isPlaylist) {
            Text(stringResource(R.string.subs_playlist_note), color = TG.Muted, fontSize = 12.sp)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                COMMON_LANGS.forEach { c -> LangChip(langName(c), c in selected) { toggle(c, c !in selected) } }
            }
        } else {
            // 올린 자막
            info.subtitles.forEach { (code, name) ->
                // 앱 언어로 된 이름 우선 (유튜브가 주는 이름은 영어인 경우가 많음)
                val label = langName(code).let { if (it == code && name.isNotBlank()) name else it }
                CheckRow("$label  [$code]", code in selected) { toggle(code, it) }
            }
            // 자동 생성 자막: 원본 언어 + 자주 쓰는 언어만
            val autos = info.autoCaptions.keys.filter { c ->
                c !in info.subtitles && (c.endsWith("-orig") || c in PRIORITY_AUTO || c in selected)
            }
            autos.forEach { code ->
                val sub = if (code.endsWith("-orig")) stringResource(R.string.auto_original) else stringResource(R.string.auto_translated)
                CheckRow(langName(code) + "  [$code]", code in selected, sub) { toggle(code, it) }
            }
            if (info.subtitles.isEmpty() && autos.isEmpty()) {
                Text(stringResource(R.string.no_subs), color = TG.Muted, fontSize = 13.sp, modifier = Modifier.padding(start = 12.dp))
            }
            // 전에 골랐지만 이 영상에는 없는 언어
            selected.filter { it !in info.subtitles && it !in info.autoCaptions }.forEach { code ->
                CheckRow(langName(code) + "  [$code]", true, stringResource(R.string.not_in_video)) { toggle(code, it) }
            }
        }

        if (selected.isNotEmpty() && prefs.mode == "video") {
            SectionTitle(stringResource(R.string.sub_mode))
            val modes = listOf(
                "embed" to R.string.sub_mode_embed_short,
                "file" to R.string.sub_mode_file_short,
                "both" to R.string.sub_mode_both_short,
            )
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                modes.forEachIndexed { i, (m, label) ->
                    SegmentedButton(
                        selected = prefs.subMode == m,
                        onClick = { Settings.update { it.copy(subMode = m) } },
                        shape = SegmentedButtonDefaults.itemShape(i, modes.size),
                        colors = SegmentedButtonDefaults.colors(
                            activeContainerColor = TG.AccentSoft, activeContentColor = TG.AccentText, activeBorderColor = TG.Accent,
                        ),
                    ) { Text(stringResource(label), fontSize = 13.sp) }
                }
            }
        } else if (selected.isNotEmpty()) {
            Text(stringResource(R.string.subs_audio_note), color = TG.Muted, fontSize = 12.sp)
        }

        SectionTitle(stringResource(R.string.dub_section))
        RadioRow(stringResource(R.string.original_audio), prefs.dubLang.isBlank()) {
            Settings.update { it.copy(dubLang = "") }
        }
        if (info.isPlaylist) {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                COMMON_LANGS.forEach { c ->
                    LangChip(langName(c), prefs.dubLang == c) {
                        Settings.update { it.copy(dubLang = if (it.dubLang == c) "" else c) }
                    }
                }
            }
        } else {
            info.dubs.forEach { (code, kind) ->
                val sub = when (kind) {
                    "original" -> stringResource(R.string.dub_original)
                    "dubbed" -> stringResource(R.string.dub_dubbed)
                    else -> null
                }
                RadioRow(langName(code) + "  [$code]", prefs.dubLang == code, sub) {
                    Settings.update { it.copy(dubLang = code) }
                }
            }
            if (prefs.dubLang.isNotBlank() && prefs.dubLang !in info.dubs) {
                RadioRow(langName(prefs.dubLang), true, stringResource(R.string.dub_missing)) {}
            }
            if (info.dubs.isEmpty()) {
                Text(stringResource(R.string.no_dubs), color = TG.Muted, fontSize = 13.sp, modifier = Modifier.padding(start = 12.dp))
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LangChip(text: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected, onClick = onClick,
        label = { Text(text, fontSize = 13.sp) },
        colors = FilterChipDefaults.filterChipColors(selectedContainerColor = TG.AccentSoft, selectedLabelColor = TG.AccentText),
    )
}

// ---- 태그 ----------------------------------------------------------------

@Composable
private fun TagsSheet(info: MediaInfo, link: LinkState.Loaded, vm: MainViewModel, prefs: Prefs, onDismiss: () -> Unit) {
    Sheet(stringResource(R.string.tags), onDismiss) {
        Row(
            Modifier.fillMaxWidth().clickable { Settings.update { it.copy(tags = !it.tags) } },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.tags_on), fontSize = 15.sp)
                Text(
                    stringResource(if (prefs.tags) R.string.tags_on_desc else R.string.tags_off_note),
                    color = TG.Muted, fontSize = 12.sp,
                )
            }
            Switch(
                prefs.tags, { v -> Settings.update { it.copy(tags = v) } },
                colors = SwitchDefaults.colors(checkedTrackColor = TG.Accent),
            )
        }
        if (prefs.tags) {
            if (info.isPlaylist) {
                Text(stringResource(R.string.tags_playlist_note), color = TG.Muted, fontSize = 13.sp, modifier = Modifier.padding(top = 8.dp))
            } else {
                val labels = mapOf(
                    "title" to R.string.tag_title, "artist" to R.string.tag_artist,
                    "album" to R.string.tag_album, "year" to R.string.tag_year,
                )
                Tags.FIELDS.forEach { f ->
                    OutlinedTextField(
                        value = link.tags[f].orEmpty(),
                        onValueChange = { v -> vm.setTags(link.tags + (f to v)) },
                        label = { Text(stringResource(labels.getValue(f))) },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                        shape = RoundedCornerShape(10.dp),
                    )
                }
                TextButton(onClick = vm::resetTags) { Text(stringResource(R.string.tag_reset)) }
            }
        }
    }
}
