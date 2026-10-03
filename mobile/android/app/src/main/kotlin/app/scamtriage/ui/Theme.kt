package app.scamtriage.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Same palette as the website: one cobalt accent, semantic risk colors.
private val Light = lightColorScheme(
    primary = Color(0xFF2C4FD6), onPrimary = Color.White, background = Color(0xFFF2F3F5), surface = Color(0xFFFBFBFC),
    surfaceVariant = Color(0xFFE9ECF1), onSurface = Color(0xFF121417), onSurfaceVariant = Color(0xFF59616E), error = Color(0xFFC9342A),
)
private val Dark = darkColorScheme(
    primary = Color(0xFF8099FF), onPrimary = Color(0xFF0B0D12), background = Color(0xFF0D0F12), surface = Color(0xFF16191E),
    surfaceVariant = Color(0xFF1C2026), onSurface = Color(0xFFECEEF2), onSurfaceVariant = Color(0xFF939BAA), error = Color(0xFFFF7B6E),
)

data class Risk(val color: Color, val soft: Color)

@Composable
fun riskColors(level: String): Risk {
    val dark = isSystemInDarkTheme()
    val c = when (level) {
        "high" -> if (dark) Color(0xFFFF7B6E) else Color(0xFFC9342A)
        "medium" -> if (dark) Color(0xFFF0B14A) else Color(0xFFA8650A)
        else -> if (dark) Color(0xFF4FD08B) else Color(0xFF1A7F49)
    }
    return Risk(c, c.copy(alpha = 0.12f))
}

@Composable
fun ScamTriageTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = if (isSystemInDarkTheme()) Dark else Light, content = content)
}
