package app.scamtriage

import android.Manifest
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.format.DateUtils
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import app.scamtriage.engine.Engine
import app.scamtriage.ui.ScamTriageTheme
import app.scamtriage.ui.Verdict
import app.scamtriage.ui.riskColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private val SAMPLES = listOf(
    "Hi Mum" to "Hi Mum, I dropped my phone so this is my new number. Can you send R\$800 by Pix today? It's urgent and I can't talk right now",
    "Parcel fee" to "Royal Mail: your parcel is on hold due to an unpaid £1.99 redelivery fee. Pay within 24 hours: royalmail-redelivery.top/pay",
    "Code by mistake" to "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?",
    "Real receipt" to "Nubank: you sent a Pix of R\$120.00 to Ana Souza.",
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent { ScamTriageTheme { Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) { Home() } } }
    }
}

private fun listenerEnabled(c: Context) = NotificationManagerCompat.getEnabledListenerPackages(c).contains(c.packageName)

private fun openListenerSettings(c: Context) {
    val component = ComponentName(c, MessageWatcherService::class.java)
    val intent = if (Build.VERSION.SDK_INT >= 30) {
        Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS)
            .putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME, component.flattenToString())
    } else Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
    runCatching { c.startActivity(intent) }.onFailure { c.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)) }
}

private fun openAppInfo(c: Context) =
    c.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", c.packageName, null)))

private fun installed(c: Context, pkg: String) = runCatching { c.packageManager.getPackageInfo(pkg, 0) }.isSuccess

@Composable
private fun Home() {
    val ctx = LocalContext.current
    val prefs = remember { Prefs(ctx) }
    var autoOn by remember { mutableStateOf(listenerEnabled(ctx)) }
    var canNotify by remember { mutableStateOf(Warnings.canPost(ctx)) }
    var history by remember { mutableStateOf(History.all(ctx)) }
    var refresh by remember { mutableIntStateOf(0) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        autoOn = listenerEnabled(ctx); canNotify = Warnings.canPost(ctx); history = History.all(ctx)
    }
    val askNotify = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { canNotify = Warnings.canPost(ctx) }

    LazyColumn(
        Modifier.fillMaxSize().safeDrawingPadding(),
        contentPadding = PaddingValues(18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = RoundedCornerShape(12.dp), color = MaterialTheme.colorScheme.primary) {
                    Icon(painterResource(R.drawable.ic_shield_check), null, tint = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.padding(8.dp).size(22.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text("Scam Triage", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("Checks run on this phone. Nothing is uploaded.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        item { Protection(autoOn, canNotify, onEnable = { openListenerSettings(ctx) }, onNotify = {
            if (Build.VERSION.SDK_INT >= 33) askNotify.launch(Manifest.permission.POST_NOTIFICATIONS) else openAppInfo(ctx)
        }, onAppInfo = { openAppInfo(ctx) }) }
        item { CheckBox() }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Recent warnings", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Spacer(Modifier.weight(1f))
                        if (history.isNotEmpty()) TextButton(onClick = { History.clear(ctx); history = emptyList() }) { Text("Clear") }
                    }
                    if (history.isEmpty()) Text(if (autoOn) "No scams spotted yet. Warnings will appear here." else "Turn on auto-check to get warnings here.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                    history.forEach { w -> WarningRow(w) { ctx.startActivity(Intent(ctx, CheckActivity::class.java).setAction(CheckActivity.ACTION_REVIEW)
                        .putExtra(Intent.EXTRA_TEXT, w.text).putExtra(CheckActivity.EXTRA_SOURCE, w.app)) } }
                }
            }
        }
        item {
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text("Apps to watch", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    KNOWN_APPS.forEach { app ->
                        var on by remember(refresh) { mutableStateOf(prefs.isWatched(app.pkg)) }
                        val has = remember { installed(ctx, app.pkg) }
                        SwitchRow(app.label + if (has) "" else " (not installed)", on) { on = it; prefs.setWatched(app.pkg, it) }
                    }
                    HorizontalDivider(Modifier.padding(vertical = 6.dp))
                    var medium by remember { mutableStateOf(prefs.warnMedium) }
                    SwitchRow("Also warn on medium risk (more alerts, more false alarms)", medium) { medium = it; prefs.warnMedium = it }
                }
            }
        }
        item {
            Text("Scam Triage reads message notifications only to check them on this phone. It keeps a message only if it warned you about it, and you can clear that any time. Version ${BuildConfig.VERSION_NAME}, model ${EngineVersion.get(ctx)}.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

private object EngineVersion { fun get(c: Context) = runCatching { EngineHolder.get(c).version }.getOrDefault("?") }

@Composable
private fun Protection(autoOn: Boolean, canNotify: Boolean, onEnable: () -> Unit, onNotify: () -> Unit, onAppInfo: () -> Unit) {
    val ok = autoOn && canNotify
    val risk = riskColors(if (ok) "low" else "medium")
    Card(colors = CardDefaults.cardColors(containerColor = risk.soft)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(painterResource(if (ok) R.drawable.ic_shield_check else R.drawable.ic_shield_warning), null, tint = risk.color, modifier = Modifier.size(26.dp))
                Spacer(Modifier.width(10.dp))
                Text(if (ok) "Auto-check is on" else "Auto-check is off", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, color = risk.color)
            }
            Text(if (ok) "New messages in the apps below are checked as they arrive. You'll get a warning if one looks like a scam."
                 else "Let Scam Triage check new messages as they arrive in WhatsApp, Messages and more. You'll be warned before you reply or pay.",
                style = MaterialTheme.typography.bodyMedium)
            if (!autoOn) {
                Button(onClick = onEnable, modifier = Modifier.fillMaxWidth()) { Text("Turn on auto-check") }
                Text("Installed the app from the website? Android may grey out the switch. Open App info, tap ⋮, choose \"Allow restricted settings\", then try again.",
                    style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                TextButton(onClick = onAppInfo) { Text("Open App info") }
            }
            if (!canNotify) FilledTonalButton(onClick = onNotify, modifier = Modifier.fillMaxWidth()) { Text("Allow warning notifications") }
            Text("Also: select any text, or share a message, and choose \"Check for scam\".", style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun CheckBox() {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var text by remember { mutableStateOf("") }
    var result by remember { mutableStateOf<Engine.Result?>(null) }
    fun run(t: String) {
        text = t
        if (t.isBlank()) return
        scope.launch { result = withContext(Dispatchers.Default) { EngineHolder.get(ctx).triage(t) } }
    }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Check a message", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            OutlinedTextField(text, { text = it }, Modifier.fillMaxWidth(), minLines = 3, label = { Text("Paste the message") })
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(SAMPLES) { (label, sample) -> SuggestionChip(onClick = { run(sample) }, label = { Text(label) }) }
            }
            Button(onClick = { run(text) }, enabled = text.isNotBlank()) { Text("Check") }
            result?.let { Verdict(it) }
        }
    }
}

@Composable
private fun WarningRow(w: Warning, onClick: () -> Unit) {
    val risk = riskColors(w.level)
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(painterResource(R.drawable.ic_shield_warning), null, tint = risk.color, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text("${w.label} · ${w.app}", fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.bodyMedium)
            Text(w.text, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(DateUtils.getRelativeTimeSpanString(w.time).toString(), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onChange)
    }
}
