package app.scamtriage.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import app.scamtriage.R
import app.scamtriage.engine.Engine

private val LEVEL_LABEL = mapOf("high" to "High risk", "medium" to "Medium risk", "low" to "Low risk")

/** The explained verdict: level, score, scam type, reasons and next steps. */
@Composable
fun Verdict(r: Engine.Result, modifier: Modifier = Modifier) {
    val risk = riskColors(r.riskLevel)
    Column(modifier, verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(
                Modifier.background(risk.soft, RoundedCornerShape(50)).padding(horizontal = 12.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(painterResource(if (r.riskLevel == "low") R.drawable.ic_shield_check else R.drawable.ic_shield_warning), null,
                    tint = risk.color, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text(LEVEL_LABEL.getValue(r.riskLevel), color = risk.color, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            }
            Spacer(Modifier.weight(1f))
            Text("${Engine.pct0(r.riskScore)}%", fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold,
                fontSize = 28.sp, color = risk.color)
        }
        Text(if (r.riskLevel == "low") r.scamTypeLabel else "Likely: ${r.scamTypeLabel}",
            style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        Text(if (r.riskLevel == "low") r.summary else r.summary.substringAfter(". "),
            color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
        if (r.fromContext) Text("Judged as a conversation: the last ${r.threadSize} messages together raised the risk.",
            color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
        if (r.cautions.isNotEmpty()) {
            val med = riskColors("medium")
            Column(Modifier.fillMaxWidth().background(med.soft, RoundedCornerShape(12.dp)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Before you act", color = med.color, fontWeight = FontWeight.SemiBold, style = MaterialTheme.typography.labelLarge)
                r.cautions.forEach { Text(it, style = MaterialTheme.typography.bodyMedium) }
            }
        }
        if (r.reasons.isNotEmpty()) Section("Why") {
            r.reasons.forEach { Bullet("⚑", it, risk.color) }
        }
        Section("What to do") {
            r.nextSteps.forEachIndexed { i, s -> Bullet("${i + 1}", s, MaterialTheme.colorScheme.primary) }
        }
    }
}

@Composable
private fun Section(title: String, content: @Composable () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        content()
    }
}

@Composable
private fun Bullet(mark: String, text: String, color: androidx.compose.ui.graphics.Color) {
    Row(Modifier.fillMaxWidth()) {
        Text(mark, color = color, fontWeight = FontWeight.Bold, modifier = Modifier.width(22.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
    Spacer(Modifier.height(2.dp))
}
