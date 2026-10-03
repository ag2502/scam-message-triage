package app.scamtriage

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import androidx.core.app.NotificationCompat
import java.util.concurrent.Executors

/**
 * Auto-check: when a watched messaging app posts a notification, check its latest message on-device
 * and post a warning if it looks like a scam. Nothing is sent anywhere; only warned messages are kept
 * (in local history) so the user can review them.
 */
class MessageWatcherService : NotificationListenerService() {
    private val worker = Executors.newSingleThreadExecutor()

    // Apps re-post a conversation's notification on every new message: remember what was already checked.
    private val seen = object : LinkedHashMap<Int, Boolean>(64, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<Int, Boolean>?) = size > 300
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return
        val prefs = Prefs(this)
        if (!prefs.isWatched(sbn.packageName)) return
        val n = sbn.notification
        if (n.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        val (sender, text) = extract(n) ?: return
        if (text.length < 12) return
        val key = (sbn.packageName + "\u0000" + text).hashCode()
        synchronized(seen) {
            if (seen.containsKey(key)) return
            seen[key] = true
        }
        worker.execute {
            val r = EngineHolder.get(this).triage(text)
            if (r.riskLevel == "high" || (r.riskLevel == "medium" && prefs.warnMedium)) {
                val app = appLabel(sbn.packageName)
                Warnings.post(this, key, app, sender, text, r)
                History.add(this, Warning(System.currentTimeMillis(), app, sender, text, r.riskLevel, r.riskScore, r.scamTypeLabel))
            }
        }
    }

    private fun appLabel(pkg: String): String = KNOWN_APPS.firstOrNull { it.pkg == pkg }?.label
        ?: runCatching { packageManager.getApplicationLabel(packageManager.getApplicationInfo(pkg, 0)).toString() }.getOrDefault(pkg)

    override fun onDestroy() {
        worker.shutdown()
        super.onDestroy()
    }

    companion object {
        /** (sender, latest message text) from a messaging notification, or null if there is no text. */
        fun extract(n: Notification): Pair<String?, String>? {
            val style = NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(n)
            val last = style?.messages?.lastOrNull()
            val text = last?.text?.toString()
                ?: n.extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
                ?: n.extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
                ?: return null
            val sender = last?.person?.name?.toString() ?: n.extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
            return sender to text.trim()
        }
    }
}
