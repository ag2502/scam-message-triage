package app.scamtriage

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class WatchedApp(val pkg: String, val label: String)

/** Messaging apps whose notifications auto-check can read. */
val KNOWN_APPS = listOf(
    WatchedApp("com.whatsapp", "WhatsApp"),
    WatchedApp("com.whatsapp.w4b", "WhatsApp Business"),
    WatchedApp("com.google.android.apps.messaging", "Google Messages"),
    WatchedApp("com.samsung.android.messaging", "Samsung Messages"),
    WatchedApp("org.telegram.messenger", "Telegram"),
    WatchedApp("org.thoughtcrime.securesms", "Signal"),
    WatchedApp("com.facebook.orca", "Messenger"),
    WatchedApp("com.instagram.android", "Instagram"),
)

class Prefs(context: Context) {
    private val sp = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    fun isWatched(pkg: String): Boolean = when {
        BuildConfig.DEBUG && pkg == "com.android.shell" -> true // lets `adb shell cmd notification post` exercise auto-check
        KNOWN_APPS.any { it.pkg == pkg } -> sp.getBoolean("watch:$pkg", true)
        else -> false
    }
    fun setWatched(pkg: String, on: Boolean) = sp.edit().putBoolean("watch:$pkg", on).apply()

    /** Safety net: a quiet "verify first" reminder when a low-risk message asks for money or a code. */
    var remindRequests: Boolean
        get() = sp.getBoolean("remind_requests", true)
        set(v) = sp.edit().putBoolean("remind_requests", v).apply()

    var warnMedium: Boolean
        get() = sp.getBoolean("warn_medium", false)
        set(v) = sp.edit().putBoolean("warn_medium", v).apply()
}

data class Warning(val time: Long, val app: String, val sender: String?, val text: String, val level: String, val score: Double, val label: String)

/** The last warnings, kept only on this device (excluded from backups). */
object History {
    private const val KEY = "warnings"
    private const val MAX = 30

    fun all(context: Context): List<Warning> {
        val raw = context.getSharedPreferences("history", Context.MODE_PRIVATE).getString(KEY, "[]")
        val arr = JSONArray(raw)
        return (0 until arr.length()).map { i ->
            val o = arr.getJSONObject(i)
            Warning(o.getLong("t"), o.getString("app"), o.optString("sender").ifEmpty { null }, o.getString("text"),
                o.getString("level"), o.getDouble("score"), o.getString("label"))
        }
    }

    fun add(context: Context, w: Warning) {
        val list = (listOf(w) + all(context)).take(MAX)
        val arr = JSONArray()
        list.forEach {
            arr.put(JSONObject().put("t", it.time).put("app", it.app).put("sender", it.sender ?: "").put("text", it.text)
                .put("level", it.level).put("score", it.score).put("label", it.label))
        }
        context.getSharedPreferences("history", Context.MODE_PRIVATE).edit().putString(KEY, arr.toString()).apply()
    }

    fun clear(context: Context) = context.getSharedPreferences("history", Context.MODE_PRIVATE).edit().clear().apply()
}
