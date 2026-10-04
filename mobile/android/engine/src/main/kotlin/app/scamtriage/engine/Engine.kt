package app.scamtriage.engine

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.io.File
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.text.Normalizer
import java.util.Locale
import java.util.regex.Matcher
import java.util.regex.Pattern
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.roundToLong
import kotlin.math.sqrt

/**
 * Kotlin port of scam_triage (signals.py, model.py, triage.py).
 * Loads the files written by scripts/export_mobile.py and reproduces Python's triage() exactly;
 * parity is enforced by EngineParityTest against mobile/shared/golden.jsonl.
 */
class Engine private constructor(
    private val m: JsonObject,
    private val wordVocab: Map<String, Int>,
    private val charVocab: Map<String, Int>,
    private val wordNames: List<String>,
    private val wordIdf: DoubleArray,
    private val charIdf: DoubleArray,
    private val riskCoef: DoubleArray,
    private val typeCoef: FloatArray,
) {
    data class SignalHit(val id: String, val reason: String, val evidence: String)

    data class Result(
        val riskScore: Double,
        val riskLevel: String, // low | medium | high
        val scamType: String,
        val scamTypeLabel: String,
        val typeConfidence: Double,
        val summary: String,
        val reasons: List<String>,
        val keyPhrases: List<String>,
        val nextSteps: List<String>,
        val signals: List<SignalHit>,
        val typeProbabilities: Map<String, Double>,
        val asks: List<String> = emptyList(), // "money" | "code" | "app"
        val cautions: List<String> = emptyList(), // safety-net notes, only when risk is low
        val threadSize: Int = 1,
        val fromContext: Boolean = false, // the conversation, not the latest message alone, raised the level
    )

    // Python's re is Unicode-aware for \w \d \b \s. On the JVM that needs UNICODE_CHARACTER_CLASS;
    // Android's ICU-backed regex is Unicode-aware by default and rejects that flag.
    private fun py(src: String, ignoreCase: Boolean = false): Pattern {
        val base = if (ignoreCase) Pattern.CASE_INSENSITIVE or Pattern.UNICODE_CASE else 0
        return Pattern.compile(src.removePrefix("(?u)"), base or unicodeFlag)
    }

    private val rx = m.obj("regex")
    private val urlRe = py(rx.str("url"), ignoreCase = true)
    private val phoneRe = py(rx.str("phone"))
    private val amountRe = py(rx.str("amount"), ignoreCase = true)
    private val refRe = py(rx.str("reference"), ignoreCase = true)
    private val negRe = py(rx.str("negation"), ignoreCase = true)
    private val tokenRe = py(rx.str("token"))
    private val digitsRe = py("\\d+")
    private val wsRe = py("\\s+")
    private val ws2Re = py("\\s\\s+")
    private val patterns: List<Pair<String, List<Pattern>>> =
        m.obj("patterns").map { (sid, pats) -> sid to pats.jsonArray.map { py(it.jsonPrimitive.content, ignoreCase = true) } }
    private val reasonsText = m.obj("reasons").mapValues { it.value.jsonPrimitive.content }
    private val negatable = m.strList("negatable").toSet()
    private val shorteners = m.strList("url_shorteners").toSet()
    private val riskyTlds = m.strList("risky_tlds").toSet()
    private val brands = m.strList("imitated_brands")
    private val lureWords = m.strList("lure_words").toSet()
    private val stopWords = m.strList("stop_words").toSet()
    private val contextSignals = m.strList("context_signals").toSet()
    private val zeroWidth = m.str("zero_width")
    private val signalIds = m.strList("signal_ids")
    private val nWord = wordIdf.size
    private val nChar = charIdf.size
    private val nFeat = riskCoef.size
    private val wordRange = m.obj("word")["ngram_range"]!!.jsonArray.map { it.jsonPrimitive.int }
    private val charRange = m.obj("char")["ngram_range"]!!.jsonArray.map { it.jsonPrimitive.int }
    private val signalWeight = m["signal_weight"]!!.jsonPrimitive.double
    private val riskIntercept = m.obj("risk")["intercept"]!!.jsonPrimitive.double
    private val classes = m.obj("type")["classes"]!!.jsonArray.map { it.jsonPrimitive.content }
    private val typeIntercept = m.obj("type")["intercept"]!!.jsonArray.map { it.jsonPrimitive.double }
    private val thresholdHigh = m.obj("thresholds")["high"]!!.jsonPrimitive.double
    private val thresholdMedium = m.obj("thresholds")["medium"]!!.jsonPrimitive.double
    private val maxReasons = m["max_reasons"]!!.jsonPrimitive.int
    private val maxPhrases = m["max_phrases"]!!.jsonPrimitive.int
    private val taxonomy = m.obj("taxonomy")
    private val askOrder = m.strList("ask_order")
    private val askSignals = m.obj("ask_signals").mapValues { (_, v) -> v.jsonArray.map { it.jsonPrimitive.content }.toSet() }
    private val cautionText = m.obj("cautions").mapValues { it.value.jsonPrimitive.content }
    private val threadMaxMessages = m.obj("thread")["max_messages"]!!.jsonPrimitive.int
    private val threadMaxChars = m.obj("thread")["max_chars"]!!.jsonPrimitive.int
    private val headerRe = py(m.str("conversation_header"))

    val version: String = m["version"]?.jsonPrimitive?.content ?: "?"

    // ---------------- signals.py ----------------
    fun normalize(text: String): String {
        var t = Normalizer.normalize(text, Normalizer.Form.NFKC)
        for (z in zeroWidth) t = t.replace(z.toString(), "")
        t = t.replace('’', '\'').replace('‘', '\'').replace('“', '"').replace('”', '"')
        return wsRe.matcher(t).replaceAll(" ").trim()
    }

    private fun lastCodePoints(s: String, n: Int): String {
        val count = s.codePointCount(0, s.length)
        return if (count <= n) s else s.substring(s.offsetByCodePoints(0, count - n))
    }

    fun extractUrls(text: String): List<String> {
        val out = mutableListOf<String>()
        val mt = urlRe.matcher(text)
        while (mt.find()) out += mt.group().trimEnd('.', ',', ';', ':', '!', '?', ')')
        return out
    }

    fun findPhones(text: String): List<String> {
        val out = mutableListOf<String>()
        val mt = phoneRe.matcher(text)
        while (mt.find()) {
            val g = mt.group()
            if (g.count { Character.isDigit(it) } < 9) continue
            if (refRe.matcher(lastCodePoints(text.substring(0, mt.start()), 16)).find()) continue
            out += g.trim()
        }
        return out
    }

    private fun host(raw: String): String {
        var url = raw
        if (!Regex("^https?://", RegexOption.IGNORE_CASE).containsMatchIn(url)) url = "http://$url"
        val rest = url.replaceFirst(Regex("^[a-zA-Z][a-zA-Z0-9+.-]*://"), "")
        val netloc = rest.split(Regex("[/?#]"), limit = 2)[0]
        var h = netloc.substringAfterLast("@")
        h = if (h.startsWith("[")) h.substring(1, h.indexOf(']').coerceAtLeast(1)) else h.substringBefore(":")
        return h.lowercase(Locale.ROOT)
    }

    fun isSuspiciousUrl(url: String): Boolean {
        val h = host(url)
        if (h.isEmpty()) return false
        if (h in shorteners) return true
        if (Regex("\\d{1,3}(\\.\\d{1,3}){3}").matches(h)) return true
        val labels = h.split(".")
        if (labels.last() in riskyTlds) return true
        val reg = if (labels.size >= 2) labels[labels.size - 2] else h
        if ('-' in reg && brands.any { it in reg }) return true
        if ('-' in reg && reg.split("-").any { it in lureWords }) return true
        if (labels.size >= 4 && brands.any { it in labels.dropLast(2).joinToString(".") }) return true
        return false
    }

    private fun negated(sid: String, text: String, start: Int): Boolean =
        sid in negatable && negRe.matcher(lastCodePoints(text.substring(0, start), 60)).find()

    fun detect(text: String): List<SignalHit> {
        val norm = normalize(text)
        val hits = mutableListOf<SignalHit>()
        for ((sid, pats) in patterns) {
            var found: String? = null
            outer@ for (p in pats) {
                val mt = p.matcher(norm)
                while (mt.find()) {
                    if (!negated(sid, norm, mt.start())) { found = mt.group(); break@outer }
                }
            }
            if (found != null) hits += SignalHit(sid, reasonsText.getValue(sid), found)
        }
        val urls = extractUrls(norm)
        if (urls.isNotEmpty()) {
            hits += SignalHit("has_link", reasonsText.getValue("has_link"), urls[0])
            urls.firstOrNull { isSuspiciousUrl(it) }?.let { hits += SignalHit("suspicious_link", reasonsText.getValue("suspicious_link"), it) }
        }
        findPhones(norm).firstOrNull()?.let { hits += SignalHit("has_phone_number", reasonsText.getValue("has_phone_number"), it) }
        val am = amountRe.matcher(norm)
        if (am.find()) hits += SignalHit("money_amount", reasonsText.getValue("money_amount"), am.group())
        return hits
    }

    // ---------------- model.py ----------------
    fun preprocess(text: String): String {
        var t = normalize(text).lowercase(Locale.ROOT)
        t = urlRe.matcher(t).replaceAll(" __url__ ")
        for (p in findPhones(t)) t = t.replace(p, " __phone__ ")
        t = amountRe.matcher(t).replaceAll(" __amount__ ")
        t = digitsRe.matcher(t).replaceAll("0")
        return wsRe.matcher(t).replaceAll(" ").trim()
    }

    private fun wordNgrams(pre: String): List<String> {
        val toks = mutableListOf<String>()
        val mt = tokenRe.matcher(pre.lowercase(Locale.ROOT))
        while (mt.find()) toks += mt.group()
        val grams = mutableListOf<String>()
        for (n in wordRange[0]..wordRange[1]) for (i in 0..toks.size - n) grams += toks.subList(i, i + n).joinToString(" ")
        return grams
    }

    private fun charNgrams(pre: String): List<String> {
        val doc = ws2Re.matcher(pre.lowercase(Locale.ROOT)).replaceAll(" ")
        val grams = mutableListOf<String>()
        for (raw in splitWs(doc)) {
            val w = " $raw ".codePoints().toArray()
            for (n in charRange[0]..charRange[1]) {
                var off = 0
                grams += String(w, off, minOf(n, w.size - off))
                while (off + n < w.size) { off++; grams += String(w, off, n) }
                if (off == 0) break
            }
        }
        return grams
    }

    private fun splitWs(s: String): List<String> = wsRe.split(s.trim()).filter { it.isNotEmpty() }

    private fun tfidf(grams: List<String>, vocab: Map<String, Int>, idf: DoubleArray, offset: Int, out: MutableMap<Int, Double>) {
        val counts = sortedMapOf<Int, Int>()
        for (g in grams) vocab[g]?.let { counts[it] = (counts[it] ?: 0) + 1 }
        val vals = counts.map { (j, c) -> j to (ln(c.toDouble()) + 1) * idf[j] }
        val norm = sqrt(vals.sumOf { it.second * it.second }).takeIf { it > 0 } ?: 1.0
        for ((j, v) in vals) out[j + offset] = v / norm
    }

    /** Sparse features in the Python featurizer's column order. */
    fun features(text: String): Pair<String, Map<Int, Double>> {
        val pre = preprocess(text)
        val x = sortedMapOf<Int, Double>()
        tfidf(wordNgrams(pre), wordVocab, wordIdf, 0, x)
        tfidf(charNgrams(pre), charVocab, charIdf, nWord, x)
        val fired = detect(text).map { it.id }.toSet()
        signalIds.forEachIndexed { k, sid -> if (sid in fired) x[nWord + nChar + k] = signalWeight }
        return pre to x
    }

    private fun featureName(j: Int): String = when {
        j < nWord -> wordNames[j]
        j < nWord + nChar -> "char:"
        else -> "signal:" + signalIds[j - nWord - nChar]
    }

    private fun isReadablePhrase(name: String): Boolean {
        if (name.startsWith("char:") || name.startsWith("signal:") || "__" in name) return false
        return !name.split(" ").all { w -> w in stopWords || w.startsWith("__") || (w.isNotEmpty() && w.all { Character.isDigit(it) }) || w.codePointCount(0, w.length) < 3 }
    }

    fun level(score: Double): String = when {
        score >= thresholdHigh -> "high"
        score >= thresholdMedium -> "medium"
        else -> "low"
    }

    // ---------------- triage.py ----------------
    fun triage(text: String): Result {
        val (_, x) = features(text)
        var logit = riskIntercept
        val contrib = ArrayList<Pair<Int, Double>>(x.size)
        for ((j, v) in x) { val c = v * riskCoef[j]; logit += c; contrib += j to c }
        val score = 1.0 / (1.0 + exp(-logit))
        val lvl = level(score)

        val z = DoubleArray(classes.size) { typeIntercept[it] }
        for ((j, v) in x) for (k in classes.indices) z[k] += v * typeCoef[k * nFeat + j]
        val zMax = z.max()
        val ez = z.map { exp(it - zMax) }
        val zs = ez.sum()
        val probs = ez.map { it / zs }
        val best = probs.indices.maxBy { probs[it] }

        // Largest contribution first; ties broken by column index, like scipy's sorted indices.
        contrib.sortWith(compareByDescending<Pair<Int, Double>> { it.second }.thenBy { it.first })
        val signalContrib = contrib.filter { it.first >= nWord + nChar }.associate { featureName(it.first).removePrefix("signal:") to it.second }
        val allHits = detect(text)
        var hits = allHits.filter { (signalContrib[it.id] ?: 0.0) > 0 }
        if (hits.any { it.id == "suspicious_link" }) hits = hits.filter { it.id != "has_link" }
        if (lvl == "low") hits = hits.filter { it.id !in contextSignals }
        hits = hits.sortedWith(compareBy<SignalHit> { it.id in contextSignals }.thenByDescending { signalContrib.getValue(it.id) })
        val reasons = hits.take(maxReasons).map { it.reason }
        var phrases = contrib.asSequence().filter { it.second > 0 && it.first < nWord }.map { wordNames[it.first] }
            .filter { isReadablePhrase(it) }.take(maxPhrases).toList()

        val typeId: String
        val conf: Double
        val summary: String
        if (lvl == "low") {
            phrases = emptyList()
            typeId = "legit"
            conf = 1 - score
            summary = "No strong scam patterns found." + if (reasons.isNotEmpty()) " A few things are worth double-checking, though." else ""
        } else {
            typeId = classes[best]
            conf = probs[best]
            val st = taxonomy.obj(typeId)
            summary = "${if (lvl == "high") "This looks like a scam" else "This could be a scam"}: ${st.str("label").lowercase(Locale.ROOT)}. ${st.str("description")}"
        }
        val st = taxonomy.obj(typeId)
        val asks = asksFrom(allHits)
        return Result(
            riskScore = round4(score), riskLevel = lvl, scamType = typeId, scamTypeLabel = st.str("label"),
            typeConfidence = round4(conf), summary = summary, reasons = reasons, keyPhrases = phrases,
            nextSteps = st.strList("next_steps"), signals = allHits,
            typeProbabilities = classes.indices.associate { classes[it] to probs[it] },
            asks = asks, cautions = if (lvl == "low") cautionsFor(asks) else emptyList(),
        )
    }

    // ---------------- safety net + conversations (triage.py) ----------------
    private fun asksFrom(hits: List<SignalHit>): List<String> {
        val fired = hits.map { it.id }.toSet()
        return askOrder.filter { a -> askSignals.getValue(a).any { it in fired } }
    }

    fun asksIn(text: String): List<String> = asksFrom(detect(text))

    fun cautionsFor(asks: List<String>): List<String> = asks.map { cautionText.getValue(it) }

    fun threadWindow(messages: List<String>): List<String> {
        var msgs = messages.map { it.trim() }.filter { it.isNotEmpty() }.takeLast(threadMaxMessages)
        while (msgs.size > 1 && msgs.joinToString("\n").let { it.codePointCount(0, it.length) } > threadMaxChars) msgs = msgs.drop(1)
        return msgs
    }

    /** The latest message judged in the light of the conversation so far (oldest first). */
    fun triageThread(messages: List<String>): Result {
        val msgs = threadWindow(messages)
        require(msgs.isNotEmpty()) { "no messages" }
        val latest = triage(msgs.last())
        if (msgs.size == 1) return latest
        val whole = triage(msgs.joinToString("\n"))
        val rank = mapOf("low" to 0, "medium" to 1, "high" to 2)
        if (rank.getValue(whole.riskLevel) > rank.getValue(latest.riskLevel)) {
            val st = taxonomy.obj(whole.scamType)
            val lead = if (whole.riskLevel == "high") "Taken together, these messages look like a scam" else "Taken together, these messages could be a scam"
            return whole.copy(summary = "$lead: ${st.str("label").lowercase(Locale.ROOT)}. ${st.str("description")}",
                threadSize = msgs.size, fromContext = true)
        }
        return latest.copy(threadSize = msgs.size, asks = whole.asks,
            cautions = if (latest.riskLevel == "low") cautionsFor(whole.asks) else emptyList())
    }

    /** Split text copied from a WhatsApp chat into messages (oldest first); otherwise listOf(text). */
    fun splitConversation(text: String): List<String> {
        // Python's str.splitlines() boundaries; a trailing line break does not add an empty line.
        val lines = text.split(LINE_BREAKS).toMutableList()
        if (lines.size > 1 && lines.last().isEmpty()) lines.removeAt(lines.size - 1)
        val messages = mutableListOf<String>()
        var headers = 0
        for (line in lines) {
            val mt = headerRe.matcher(line)
            if (mt.lookingAt()) { headers++; messages += line.substring(mt.end()) }
            else if (messages.isNotEmpty()) messages[messages.size - 1] = messages.last() + "\n" + line
            else messages += line
        }
        if (headers < 2) return listOf(text)
        return messages.map { it.trim() }.filter { it.isNotEmpty() }
    }

    /** One message, or a pasted conversation judged as a whole. */
    fun triageText(text: String): Result {
        val msgs = splitConversation(text)
        return if (msgs.size > 1) triageThread(msgs) else triage(text)
    }

    /** The reply the WhatsApp bot sends (twin of scam_triage/reply.py). */
    fun formatReply(r: Result): String {
        val badge = mapOf("high" to "🔴 HIGH RISK", "medium" to "🟠 MEDIUM RISK", "low" to "🟢 LOW RISK").getValue(r.riskLevel)
        val lines = mutableListOf("$badge (${pct0(r.riskScore)}%)", "")
        if (r.riskLevel == "low") lines += "*${r.scamTypeLabel}.* ${r.summary}"
        else { lines += "*Likely scam type:* ${r.scamTypeLabel}"; lines += r.summary.substringAfter(". ") }
        if (r.fromContext) lines += "_Based on the last ${r.threadSize} messages together._"
        if (r.reasons.isNotEmpty()) { lines += ""; lines += "*Why:*"; lines += r.reasons.map { "• $it" } }
        if (r.cautions.isNotEmpty()) { lines += ""; lines += "*Before you act:*"; lines += r.cautions.map { "• $it" } }
        if (r.nextSteps.isNotEmpty()) { lines += ""; lines += "*What to do:*"; lines += r.nextSteps.map { "• $it" } }
        lines += ""; lines += "_Automated check. It can be wrong. When in doubt, verify through a channel you already trust._"
        return lines.joinToString("\n")
    }

    companion object {
        private val unicodeFlag: Int = runCatching { Pattern.compile("\\w", Pattern.UNICODE_CHARACTER_CLASS); Pattern.UNICODE_CHARACTER_CLASS }.getOrDefault(0)

        /** Load from the four files written by scripts/export_mobile.py. */
        fun load(modelJson: String, vocabWord: InputStream, vocabChar: InputStream, weights: ByteArray): Engine {
            val m = Json.parseToJsonElement(modelJson).jsonObject
            val sizes = m.obj("sizes")
            val nWord = sizes["n_word"]!!.jsonPrimitive.int
            val nChar = sizes["n_char"]!!.jsonPrimitive.int
            val nFeat = sizes["n_feat"]!!.jsonPrimitive.int
            val nClasses = sizes["n_classes"]!!.jsonPrimitive.int
            val words = readVocab(vocabWord, nWord)
            val chars = readVocab(vocabChar, nChar)
            val buf = ByteBuffer.wrap(weights).order(ByteOrder.LITTLE_ENDIAN)
            val wordIdf = DoubleArray(nWord) { buf.getDouble() }
            val charIdf = DoubleArray(nChar) { buf.getDouble() }
            val risk = DoubleArray(nFeat) { buf.getDouble() }
            val type = FloatArray(nClasses * nFeat) { buf.getFloat() }
            check(!buf.hasRemaining()) { "weights.bin has unexpected trailing bytes" }
            return Engine(m, words.withIndex().associate { it.value to it.index }, chars.withIndex().associate { it.value to it.index },
                words, wordIdf, charIdf, risk, type)
        }

        fun load(dir: File): Engine = load(
            File(dir, "model.json").readText(),
            File(dir, "vocab_word.txt").inputStream(),
            File(dir, "vocab_char.txt").inputStream(),
            File(dir, "weights.bin").readBytes(),
        )

        private fun readVocab(stream: InputStream, n: Int): List<String> {
            // Split on '\n' only: char n-grams can start or end with spaces.
            val lines = stream.readBytes().toString(Charsets.UTF_8).split("\n")
            return lines.take(n).also { check(it.size == n) { "vocab has ${it.size} terms, expected $n" } }
        }

        private fun round4(v: Double): Double = (v * 1e4).roundToLong() / 1e4

        private val LINE_BREAKS = Regex("\r\n|[\n\r\u000B\u000C\u001C\u001D\u001E\u0085\u2028\u2029]")

        /** Whole-number percent with round-half-even, like Python's f"{x:.0%}". */
        fun pct0(x: Double): Long {
            val v = x * 100
            val f = kotlin.math.floor(v)
            return if (kotlin.math.abs(v - f - 0.5) < 1e-9) (if (f.toLong() % 2 == 0L) f.toLong() else f.toLong() + 1) else v.roundToLong()
        }
    }
}

private fun JsonObject.obj(key: String): JsonObject = this[key]!!.jsonObject
private fun JsonObject.str(key: String): String = this[key]!!.jsonPrimitive.content
private fun JsonObject.strList(key: String): List<String> = (this[key] as JsonArray).map { it.jsonPrimitive.content }
