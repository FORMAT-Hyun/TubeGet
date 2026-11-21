package io.github.formathyun.tubeget.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// PC 판(tubegetapp/ui/theme.py)과 같은 어두운 테마 + 빨강 포인트
object TG {
    val Accent = Color(0xFFFF4D4F)
    val AccentSoft = Color(0xFF3A2225)
    val AccentText = Color(0xFFFF7B7D)
    val Bg = Color(0xFF141518)
    val Bar = Color(0xFF1A1C20)
    val Surface = Color(0xFF1D1F24)
    val Surface2 = Color(0xFF272A31)
    val Border = Color(0xFF2B2E36)
    val BorderStrong = Color(0xFF3B404B)
    val Text = Color(0xFFE8E9EC)
    val Muted = Color(0xFF9AA0AA)
    val Placeholder = Color(0xFF6B717C)
    val Success = Color(0xFF3ECF8E)
    val Danger = Color(0xFFFF6B6B)
    val Warning = Color(0xFFF5B544)
}

private val Colors = darkColorScheme(
    primary = TG.Accent,
    onPrimary = Color.White,
    primaryContainer = TG.AccentSoft,
    onPrimaryContainer = TG.AccentText,
    secondary = TG.AccentText,
    onSecondary = Color.White,
    secondaryContainer = TG.AccentSoft,
    onSecondaryContainer = TG.AccentText,
    background = TG.Bg,
    onBackground = TG.Text,
    surface = TG.Bg,
    onSurface = TG.Text,
    surfaceVariant = TG.Surface2,
    onSurfaceVariant = TG.Muted,
    surfaceContainerLowest = TG.Bg,
    surfaceContainerLow = TG.Surface,
    surfaceContainer = TG.Surface,
    surfaceContainerHigh = TG.Surface2,
    surfaceContainerHighest = TG.Surface2,
    outline = TG.BorderStrong,
    outlineVariant = TG.Border,
    error = TG.Danger,
    onError = Color.White,
)

@Composable
fun TubeGetTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Colors, typography = Typography(), content = content)
}
