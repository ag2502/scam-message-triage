package app.scamtriage

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import app.scamtriage.engine.Engine

object Warnings {
    private const val CHANNEL = "scam_warnings"

    fun createChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val ch = NotificationChannel(CHANNEL, context.getString(R.string.channel_warnings), NotificationManager.IMPORTANCE_HIGH).apply {
            description = context.getString(R.string.channel_warnings_desc)
            enableVibration(true)
            lightColor = Color.RED
        }
        context.getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
    }

    fun canPost(context: Context): Boolean =
        (Build.VERSION.SDK_INT < 33 || ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) &&
            NotificationManagerCompat.from(context).areNotificationsEnabled()

    @android.annotation.SuppressLint("MissingPermission") // checked by canPost()
    fun post(context: Context, id: Int, app: String, sender: String?, text: String, r: Engine.Result) {
        if (!canPost(context)) return
        val open = Intent(context, CheckActivity::class.java)
            .setAction(CheckActivity.ACTION_REVIEW)
            .putExtra(Intent.EXTRA_TEXT, text)
            .putExtra(CheckActivity.EXTRA_SOURCE, app)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        val pi = PendingIntent.getActivity(context, id, open, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val level = if (r.riskLevel == "high") "Likely scam" else "Possible scam"
        val from = sender?.let { " from $it" } ?: ""
        val body = buildString {
            append(r.scamTypeLabel).append(". ").append(r.nextSteps.firstOrNull().orEmpty())
            if (r.reasons.isNotEmpty()) append("\n\nWhy: ").append(r.reasons.take(2).joinToString(" "))
        }
        val n = NotificationCompat.Builder(context, CHANNEL)
            .setSmallIcon(R.drawable.ic_stat_warning)
            .setColor(Color.parseColor(if (r.riskLevel == "high") "#C9342A" else "#A8650A"))
            .setContentTitle("$level in $app$from")
            .setContentText("${r.scamTypeLabel}. ${r.nextSteps.firstOrNull().orEmpty()}")
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_STATUS)
            .setContentIntent(pi)
            .addAction(0, "Why?", pi)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(id, n)
    }
}
