package app.scamtriage.engine

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

/** The Kotlin engine must reproduce Python's triage() on every golden case (scripts/export_mobile.py). */
class EngineParityTest {
    private val shared = File(System.getProperty("sharedDir"))
    private val engine = Engine.load(File(shared, "model"))
    private val golden: List<JsonObject> = File(shared, "golden/golden.jsonl").readLines().filter { it.isNotBlank() }
        .map { Json.parseToJsonElement(it).jsonObject }

    private fun JsonObject.strings(key: String) = this[key]!!.jsonArray.map { it.jsonPrimitive.content }

    @Test
    fun signalsMatchPython() {
        val bad = golden.filter { g ->
            val expected = g["signals"]!!.jsonArray.map { it.jsonArray.let { p -> p[0].jsonPrimitive.content to p[1].jsonPrimitive.content } }
            engine.detect(g.str("text")).map { it.id to it.evidence } != expected
        }
        assertTrue(bad.isEmpty(), "${bad.size}/${golden.size} differ, e.g. ${bad.take(3).map { it.str("text") }}")
    }

    @Test
    fun triageMatchesPython() {
        val mismatches = mutableListOf<String>()
        for (g in golden) {
            val r = engine.triage(g.str("text"))
            val same = abs(r.riskScore - g["risk_score"]!!.jsonPrimitive.double) <= 2e-4 &&
                r.riskLevel == g.str("risk_level") && r.scamType == g.str("scam_type") &&
                r.reasons == g.strings("reasons") && r.keyPhrases == g.strings("key_phrases")
            if (!same) mismatches += "${g.str("text").take(60)} | py=${g.str("risk_level")}/${g.str("scam_type")}/${g.strings("key_phrases")} kt=${r.riskLevel}/${r.scamType}/${r.keyPhrases}"
        }
        assertTrue(mismatches.isEmpty(), "${mismatches.size}/${golden.size} differ:\n${mismatches.take(5).joinToString("\n")}")
    }

    @Test
    fun replyFormat() {
        val r = engine.triage("Hi Mum, new number. Send R$800 by Pix now, can't talk")
        val reply = engine.formatReply(r)
        assertTrue(reply.startsWith("🔴 HIGH RISK"), reply)
        assertEquals("high", r.riskLevel)
    }

    private fun JsonObject.str(key: String) = this[key]!!.jsonPrimitive.content
    private fun jsonl(name: String) = File(shared, "golden/$name").readLines().filter { it.isNotBlank() }.map { Json.parseToJsonElement(it).jsonObject }

    @Test
    fun safetyNetAndReplyTextMatchPython() {
        val bad = golden.filter { g ->
            val r = engine.triage(g.str("text"))
            r.asks != g.strings("asks") || r.cautions != g.strings("cautions") || engine.formatReply(r) != g.str("reply")
        }
        assertTrue(bad.isEmpty(), "${bad.size}/${golden.size} differ, e.g. ${bad.take(3).map { it.str("text").take(50) }}")
    }

    @Test
    fun conversationsMatchPython() {
        val cases = jsonl("threads.jsonl")
        val bad = cases.filter { c ->
            val r = engine.triageThread(c.strings("messages"))
            r.riskLevel != c.str("risk_level") || r.scamType != c.str("scam_type") || r.fromContext.toString() != c.str("from_context") ||
                r.threadSize.toString() != c.str("thread_size") || r.summary != c.str("summary") || r.asks != c.strings("asks") ||
                r.cautions != c.strings("cautions") || engine.formatReply(r) != c.str("reply")
        }
        assertTrue(bad.isEmpty(), "${bad.size}/${cases.size} differ, e.g. ${bad.take(3).map { it.strings("messages").last().take(40) }}")
    }

    @Test
    fun splitConversationMatchesPython() {
        for (c in jsonl("split.jsonl")) assertEquals(c.strings("messages"), engine.splitConversation(c.str("text")))
    }
}
