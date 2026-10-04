package app.scamtriage

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import app.scamtriage.engine.Engine
import app.scamtriage.ui.ScamTriageTheme
import app.scamtriage.ui.Verdict
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/** Bottom sheet over the current app: opened from the share sheet, the text-selection menu or a warning. */
class CheckActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val text = sharedText(intent)
        val source = intent.getStringExtra(EXTRA_SOURCE)
        setContent { ScamTriageTheme { Sheet(text, source) { finish() } } }
    }

    @OptIn(ExperimentalMaterial3Api::class)
    @Composable
    private fun Sheet(text: String, source: String?, onDone: () -> Unit) {
        var result by remember { mutableStateOf<Engine.Result?>(null) }
        LaunchedEffect(text) {
            if (text.isNotBlank()) result = withContext(Dispatchers.Default) { EngineHolder.get(this@CheckActivity).triageText(text) }
        }
        ModalBottomSheet(onDismissRequest = onDone, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(
                Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(horizontal = 22.dp).padding(bottom = 18.dp).navigationBarsPadding(),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Text(if (source != null) "Message in $source" else "Checked on this device",
                    style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (text.isBlank()) {
                    Text("There was no text to check. Select or share the message's text and try again.")
                } else {
                    Surface(shape = RoundedCornerShape(16.dp, 16.dp, 16.dp, 4.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                        Text(text, Modifier.padding(14.dp), maxLines = 6, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyMedium)
                    }
                    val r = result
                    if (r == null) Box(Modifier.fillMaxWidth().height(4.dp)) { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                    else Verdict(r)
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    result?.let { r ->
                        OutlinedButton(onClick = { copyReply(r) }) { Text("Copy reply") }
                    }
                    Button(onClick = onDone) { Text("Done") }
                }
                Text("Automated check. It can be wrong. When in doubt, call the person on a number you already have.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }

    private fun copyReply(r: Engine.Result) {
        val reply = EngineHolder.get(this).formatReply(r)
        getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Scam Triage", reply))
        Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show()
    }

    companion object {
        const val ACTION_REVIEW = "app.scamtriage.REVIEW"
        const val EXTRA_SOURCE = "app.scamtriage.SOURCE"

        fun sharedText(intent: Intent): String {
            val parts = when (intent.action) {
                Intent.ACTION_PROCESS_TEXT -> listOf(intent.getCharSequenceExtra(Intent.EXTRA_PROCESS_TEXT)?.toString())
                else -> listOf(intent.getStringExtra(Intent.EXTRA_SUBJECT), intent.getCharSequenceExtra(Intent.EXTRA_TEXT)?.toString())
            }
            return parts.mapNotNull { it?.trim() }.filter { it.isNotEmpty() }.distinct().joinToString("\n").take(4000)
        }
    }
}
