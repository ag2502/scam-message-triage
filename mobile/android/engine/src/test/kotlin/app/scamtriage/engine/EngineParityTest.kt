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
}
