package io.github.formathyun.tubeget

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed interface LinkState {
    data object Idle : LinkState
    data class Loading(val url: String) : LinkState
    /** tags: 이 영상에 넣을 태그 값 (제목에서 추측한 값으로 시작, 카드에서 고칠 수 있음) */
    data class Loaded(val info: MediaInfo, val selected: Set<Int>, val tags: Map<String, String> = emptyMap()) : LinkState
    data class Error(val url: String, val message: String) : LinkState
}

class MainViewModel(app: Application) : AndroidViewModel(app) {
    private val _link = MutableStateFlow<LinkState>(LinkState.Idle)
    val link: StateFlow<LinkState> get() = _link

    private val _messages = MutableSharedFlow<String>(extraBufferCapacity = 4)
    val messages: SharedFlow<String> get() = _messages

    private var loadJob: Job? = null

    fun load(text: String?) {
        val url = extractUrl(text)
        if (url == null) {
            _messages.tryEmit(getApplication<Application>().getString(R.string.no_link_found))
            return
        }
        loadJob?.cancel()
        _link.value = LinkState.Loading(url)
        loadJob = viewModelScope.launch {
            _link.value = try {
                val info = Engine.fetch(url)
                LinkState.Loaded(
                    info, info.entries.map { it.index }.toSet(),
                    if (info.isPlaylist) emptyMap() else Tags.guess(info),
                )
            } catch (e: FriendlyException) {
                LinkState.Error(url, e.message.orEmpty())
            } catch (e: kotlinx.coroutines.CancellationException) {
                throw e
            } catch (e: Exception) {
                LinkState.Error(url, e.message ?: e.toString())
            }
            // '바로 받기': 영상 하나면 카드를 거치지 않고 지금 설정으로 바로 받는다 (재생목록은 고르는 화면)
            val s = _link.value
            if (s is LinkState.Loaded && !s.info.isPlaylist && Settings.prefs.value.instant) download()
        }
    }

    fun setTags(values: Map<String, String>) {
        val s = _link.value as? LinkState.Loaded ?: return
        _link.value = s.copy(tags = values)
    }

    fun resetTags() {
        val s = _link.value as? LinkState.Loaded ?: return
        _link.value = s.copy(tags = Tags.guess(s.info))
    }

    fun retryLoad() {
        when (val s = _link.value) {
            is LinkState.Error -> load(s.url)
            else -> Unit
        }
    }

    fun dismiss() {
        loadJob?.cancel()
        _link.value = LinkState.Idle
    }

    fun toggleEntry(index: Int) {
        val s = _link.value as? LinkState.Loaded ?: return
        _link.value = s.copy(selected = if (index in s.selected) s.selected - index else s.selected + index)
    }

    fun selectAll(all: Boolean) {
        val s = _link.value as? LinkState.Loaded ?: return
        _link.value = s.copy(selected = if (all) s.info.entries.map { it.index }.toSet() else emptySet())
    }

    /** 지금 카드의 설정으로 다운로드 목록에 넣는다. */
    fun download() {
        val s = _link.value as? LinkState.Loaded ?: return
        val prefs = Settings.prefs.value
        val base = prefs.toOptions()
        val info = s.info
        val ctx = getApplication<Application>()
        if (info.isPlaylist) {
            val picked = info.entries.filter { it.index in s.selected }
            if (picked.isEmpty()) return
            for (e in picked) {
                Downloads.add(
                    e.url, e.title, e.thumbnail,
                    base.copy(
                        tagSmart = prefs.tags,
                        playlistTitle = if (prefs.playlistFolder) info.title else "",
                        index = if (prefs.playlistFolder) e.index else null,
                    ),
                )
            }
            _messages.tryEmit(ctx.getString(R.string.added_many, picked.size))
        } else {
            // 고른 화질이 이 영상에 없으면 '최고 화질'과 같으니 목록에도 그렇게 보여준다
            var opts = if (base.maxHeight != 0 && base.maxHeight !in info.heights &&
                base.maxHeight > (info.heights.maxOrNull() ?: 0)
            ) base.copy(maxHeight = 0) else base
            if (prefs.tags) opts = opts.copy(tagValues = s.tags)
            Downloads.add(info.url, info.title, info.thumbnail, opts)
            _messages.tryEmit(ctx.getString(R.string.added_one))
        }
        _link.value = LinkState.Idle
    }
}
