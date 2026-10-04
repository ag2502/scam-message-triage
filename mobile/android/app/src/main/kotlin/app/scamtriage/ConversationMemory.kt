package app.scamtriage

/**
 * Recent incoming messages per conversation, so slow-burn scams can be judged as a whole.
 * In memory only (never written to storage): at most 8 messages per chat, for up to 3 days,
 * for the 50 most recently active chats. Accessed from the watcher's single worker thread.
 */
object ConversationMemory {
    private const val MAX_MESSAGES = 8
    private const val MAX_CHATS = 50
    private const val TTL_MS = 3 * 24 * 60 * 60 * 1000L

    private data class Entry(val time: Long, val text: String)

    private val chats = object : LinkedHashMap<String, ArrayDeque<Entry>>(16, 0.75f, true) {
        override fun removeEldestEntry(eldest: MutableMap.MutableEntry<String, ArrayDeque<Entry>>?) = size > MAX_CHATS
    }
    private val reminded = HashMap<String, Long>()

    /** Add new incoming texts (oldest first) and return the chat's recent messages, oldest first. */
    fun add(key: String, texts: List<String>, now: Long = System.currentTimeMillis()): List<String> {
        val q = chats.getOrPut(key) { ArrayDeque() }
        q.removeAll { now - it.time > TTL_MS }
        for (t in texts) if (q.none { it.text == t }) q.addLast(Entry(now, t))
        while (q.size > MAX_MESSAGES) q.removeFirst()
        return q.map { it.text }
    }

    /** True at most once per chat every 12 hours: keeps safety-net reminders from nagging. */
    fun shouldRemind(key: String, now: Long = System.currentTimeMillis()): Boolean {
        val last = reminded[key]
        if (last != null && now - last < 12 * 60 * 60 * 1000L) return false
        reminded[key] = now
        return true
    }

    fun clear() { chats.clear(); reminded.clear() }
}
