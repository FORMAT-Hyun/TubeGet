package io.github.formathyun.tubeget

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import io.github.formathyun.tubeget.ui.HistoryScreen
import io.github.formathyun.tubeget.ui.HomeScreen
import io.github.formathyun.tubeget.ui.SettingsScreen
import io.github.formathyun.tubeget.ui.TG
import io.github.formathyun.tubeget.ui.TubeGetTheme

class MainActivity : AppCompatActivity() {
    private val vm: MainViewModel by viewModels()

    private val askPermissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { }

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) handleIntent(intent)
        requestNeededPermissions()
        Downloads.resume()

        setContent {
            TubeGetTheme {
                var tab by rememberSaveable { mutableIntStateOf(0) }
                var showSettings by rememberSaveable { mutableStateOf(false) }
                val snackbar = remember { SnackbarHostState() }
                val items by Downloads.items.collectAsState()
                val activeCount = items.count { it.status != Status.DONE }

                LaunchedEffect(Unit) {
                    vm.messages.collect { snackbar.showSnackbar(it) }
                }
                // 새 링크를 받으면 받기 탭으로
                val link by vm.link.collectAsState()
                LaunchedEffect(link) {
                    if (link !is LinkState.Idle) {
                        tab = 0; showSettings = false
                    }
                }
                BackHandler(enabled = showSettings) { showSettings = false }

                Scaffold(
                    containerColor = TG.Bg,
                    snackbarHost = { SnackbarHost(snackbar) },
                    topBar = {
                        TopAppBar(
                            title = {
                                Text(
                                    if (showSettings) stringResource(R.string.settings) else stringResource(R.string.app_name),
                                    fontWeight = FontWeight.Bold,
                                )
                            },
                            navigationIcon = {
                                if (showSettings) IconButton(onClick = { showSettings = false }) {
                                    Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back))
                                }
                            },
                            actions = {
                                if (!showSettings) IconButton(onClick = { showSettings = true }) {
                                    Icon(Icons.Filled.Settings, stringResource(R.string.settings))
                                }
                            },
                            colors = TopAppBarDefaults.topAppBarColors(containerColor = TG.Bar),
                        )
                    },
                    bottomBar = {
                        if (!showSettings) NavigationBar(containerColor = TG.Bar) {
                            val itemColors = NavigationBarItemDefaults.colors(
                                selectedIconColor = TG.AccentText,
                                selectedTextColor = TG.AccentText,
                                indicatorColor = TG.AccentSoft,
                                unselectedIconColor = TG.Muted,
                                unselectedTextColor = TG.Muted,
                            )
                            NavigationBarItem(
                                selected = tab == 0, onClick = { tab = 0 },
                                icon = {
                                    BadgedBox(badge = { if (activeCount > 0) Badge { Text("$activeCount") } }) {
                                        Icon(painterResource(R.drawable.ic_download), null, Modifier.size(24.dp))
                                    }
                                },
                                label = { Text(stringResource(R.string.tab_home)) },
                                colors = itemColors,
                            )
                            NavigationBarItem(
                                selected = tab == 1, onClick = { tab = 1 },
                                icon = { Icon(painterResource(R.drawable.ic_history), null, Modifier.size(24.dp)) },
                                label = { Text(stringResource(R.string.tab_history)) },
                                colors = itemColors,
                            )
                        }
                    },
                ) { padding ->
                    when {
                        showSettings -> SettingsScreen(padding)
                        tab == 0 -> HomeScreen(vm, padding)
                        else -> HistoryScreen(padding)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    /** 유튜브 앱 등에서 [공유 → TubeGet] 으로 들어온 링크 */
    private fun handleIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND) {
            val text = intent.getStringExtra(Intent.EXTRA_TEXT) ?: intent.getStringExtra(Intent.EXTRA_SUBJECT)
            if (!text.isNullOrBlank()) vm.load(text)
        }
    }

    private fun requestNeededPermissions() {
        val need = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= 33) need += Manifest.permission.POST_NOTIFICATIONS
        if (Build.VERSION.SDK_INT <= 29) need += Manifest.permission.WRITE_EXTERNAL_STORAGE
        val missing = need.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) askPermissions.launch(missing.toTypedArray())
    }
}
