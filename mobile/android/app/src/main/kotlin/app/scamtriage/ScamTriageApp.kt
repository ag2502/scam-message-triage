package app.scamtriage

import android.app.Application
import android.content.Context
import app.scamtriage.engine.Engine
import kotlin.concurrent.thread

class ScamTriageApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Warnings.createChannel(this)
        thread(name = "engine-warmup", isDaemon = true) { EngineHolder.get(this) }
    }
}

/** One engine per process, loaded lazily from the bundled model files (assets = mobile/shared/model). */
object EngineHolder {
    @Volatile private var engine: Engine? = null

    fun get(context: Context): Engine = engine ?: synchronized(this) {
        engine ?: load(context.applicationContext).also { engine = it }
    }

    private fun load(c: Context): Engine {
        val a = c.assets
        return Engine.load(
            a.open("model.json").bufferedReader().use { it.readText() },
            a.open("vocab_word.txt"),
            a.open("vocab_char.txt"),
            a.open("weights.bin").use { it.readBytes() },
        )
    }
}
