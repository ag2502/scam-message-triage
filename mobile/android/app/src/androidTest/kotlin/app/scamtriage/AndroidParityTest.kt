package app.scamtriage

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.math.abs

/** Android's regex (ICU) differs from the JVM's, so parity with Python is re-checked on device. */
@RunWith(AndroidJUnit4::class)
class AndroidParityTest {
    @Test
    fun triageMatchesPythonOnDevice() {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val testCtx = InstrumentationRegistry.getInstrumentation().context
        val engine = EngineHolder.get(ctx)
        val golden = testCtx.assets.open("golden.jsonl").bufferedReader().readLines().filter { it.isNotBlank() }.map { JSONObject(it) }
        val bad = mutableListOf<String>()
        for (g in golden) {
            val text = g.getString("text")
            val r = engine.triage(text)
            val reasons = g.getJSONArray("reasons").let { a -> (0 until a.length()).map { a.getString(it) } }
            val phrases = g.getJSONArray("key_phrases").let { a -> (0 until a.length()).map { a.getString(it) } }
            val signals = g.getJSONArray("signals").let { a -> (0 until a.length()).map { a.getJSONArray(it).let { p -> p.getString(0) to p.getString(1) } } }
            val ok = abs(r.riskScore - g.getDouble("risk_score")) <= 2e-4 && r.riskLevel == g.getString("risk_level") &&
                r.scamType == g.getString("scam_type") && r.reasons == reasons && r.keyPhrases == phrases &&
                engine.detect(text).map { it.id to it.evidence } == signals
            if (!ok) bad += "${text.take(50)} | py=${g.getString("risk_level")}/${g.getString("scam_type")} kt=${r.riskLevel}/${r.scamType}"
        }
        assertTrue("${bad.size}/${golden.size} differ:\n" + bad.take(8).joinToString("\n"), bad.isEmpty())
    }

    @Test
    fun conversationsMatchPythonOnDevice() {
        val ctx = InstrumentationRegistry.getInstrumentation().targetContext
        val testCtx = InstrumentationRegistry.getInstrumentation().context
        val engine = EngineHolder.get(ctx)
        val cases = testCtx.assets.open("threads.jsonl").bufferedReader().readLines().filter { it.isNotBlank() }.map { JSONObject(it) }
        val bad = cases.filter { c ->
            val msgs = c.getJSONArray("messages").let { a -> (0 until a.length()).map { a.getString(it) } }
            val r = engine.triageThread(msgs)
            r.riskLevel != c.getString("risk_level") || r.fromContext != c.getBoolean("from_context") || engine.formatReply(r) != c.getString("reply")
        }
        assertTrue("${bad.size}/${cases.size} conversations differ", bad.isEmpty())
    }
}
