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
        val incoming = extract(n) ?: return
        val text = incoming.texts.last()
        if (text.length < 12) return
        val key = (sbn.packageName + "\u0000" + text).hashCode()
        synchronized(seen) {
            if (seen.containsKey(key)) return
            seen[key] = true
        }
        worker.execute {
            // Judge the newest message together with the chat's recent incoming messages.
            val chatKey = sbn.packageName + "|" + (incoming.chat ?: incoming.sender ?: "")
            val history = ConversationMemory.add(chatKey, incoming.texts)
            val r = EngineHolder.get(this).triageThread(history)
            val app = appLabel(sbn.packageName)
            // A conversation that escalates is the slow-burn pattern itself, so it warns from medium up;
            // single messages warn at high (medium only if the user opted in).
            if (r.riskLevel == "high" || (r.riskLevel == "medium" && (prefs.warnMedium || r.fromContext))) {
                val shown = if (r.fromContext) history.joinToString("\n") else text
                Warnings.post(this, key, app, incoming.chat ?: incoming.sender, shown, r)
                History.add(this, Warning(System.currentTimeMillis(), app, incoming.sender, shown, r.riskLevel, r.riskScore, r.scamTypeLabel))
            } else if (r.cautions.isNotEmpty() && prefs.remindRequests && ConversationMemory.shouldRemind(chatKey)) {
                Warnings.remind(this, key, app, incoming.sender, text, r)
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
        data class Incoming(val chat: String?, val sender: String?, val texts: List<String>)

        /**
         * The chat name, latest sender and recent incoming texts (oldest first) of a messaging notification.
         * Messaging apps usually include the last few messages of the conversation; the user's own messages
         * are left out.
         */
        fun extract(n: Notification): Incoming? {
            val style = NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(n)
            if (style != null) {
                val me = style.user.name?.toString()
                val msgs = style.messages.filter { it.person != null && it.person?.name?.toString() != me }
                    .mapNotNull { m -> m.text?.toString()?.trim()?.takeIf { it.isNotEmpty() }?.let { m.person?.name?.toString() to it } }
                if (msgs.isNotEmpty()) {
                    return Incoming(style.conversationTitle?.toString(), msgs.last().first, msgs.map { it.second })
                }
            }
            val text = n.extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
                ?: n.extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
                ?: return null
            val sender = n.extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
            return Incoming(null, sender, listOf(text.trim()))
        }
    }
}
