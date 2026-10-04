import Foundation

/// Swift port of scam_triage (signals.py, model.py, triage.py).
/// Loads the files written by scripts/export_mobile.py and reproduces Python's `triage()`;
/// parity is enforced by `ParityTests` against mobile/shared/golden/golden.jsonl.
public final class Engine: @unchecked Sendable { // immutable after init
    public struct SignalHit: Equatable, Sendable {
        public let id: String
        public let reason: String
        public let evidence: String
    }

    public struct Result: Sendable {
        public let riskScore: Double
        public let riskLevel: String // low | medium | high
        public let scamType: String
        public let scamTypeLabel: String
        public let typeConfidence: Double
        public let summary: String
        public let reasons: [String]
        public let keyPhrases: [String]
        public let nextSteps: [String]
        public let signals: [SignalHit]
        public var asks: [String] = [] // "money" | "code" | "app"
        public var cautions: [String] = [] // safety-net notes, only when risk is low
        public var threadSize: Int = 1
        public var fromContext: Bool = false // the conversation, not the latest message alone, raised the level
    }

    // MARK: Model data
    private let wordVocab: [String: Int]
    private let charVocab: [String: Int]
    private let wordNames: [String]
    private let weights: Data // memory-mapped; read in place
    private let nWord: Int, nChar: Int, nFeat: Int, nClasses: Int
    private let withTypeModel: Bool

    // MARK: Rules
    private let urlRe, phoneRe, amountRe, refRe, negRe, tokenRe, digitsRe, wsRe, ws2Re: NSRegularExpression
    private let patterns: [(String, [NSRegularExpression])]
    private let reasonsText: [String: String]
    private let negatable, shorteners, riskyTlds, lureWords, stopWords, contextSignals: Set<String>
    private let brands: [String]
    private let zeroWidth: [Character]
    private let signalIds: [String]
    private let wordRange: (Int, Int), charRange: (Int, Int)
    private let signalWeight: Double, riskIntercept: Double
    private let classes: [String]
    private let typeIntercept: [Double]
    private let thresholdHigh: Double, thresholdMedium: Double
    private let maxReasons: Int, maxPhrases: Int
    private let taxonomy: [String: [String: Any]]
    private let askOrder: [String]
    private let askSignals: [String: Set<String>]
    private let cautionText: [String: String]
    private let threadMaxMessages: Int, threadMaxChars: Int
    private let headerRe: NSRegularExpression
    public let version: String

    /// - Parameter withTypeModel: false skips the scam-type model (the SMS filter only needs the risk score).
    public init(directory: URL, withTypeModel: Bool = true) throws {
        let json = try Data(contentsOf: directory.appendingPathComponent("model.json"))
        guard let m = try JSONSerialization.jsonObject(with: json) as? [String: Any] else { throw EngineError.badModel("model.json") }
        let sizes = m["sizes"] as! [String: Int]
        nWord = sizes["n_word"]!; nChar = sizes["n_char"]!; nFeat = sizes["n_feat"]!; nClasses = sizes["n_classes"]!
        self.withTypeModel = withTypeModel
        weights = try Data(contentsOf: directory.appendingPathComponent("weights.bin"), options: .alwaysMapped)
        let expected = 8 * (nWord + nChar + nFeat) + 4 * nClasses * nFeat
        guard weights.count == expected else { throw EngineError.badModel("weights.bin is \(weights.count) bytes, expected \(expected)") }
        wordNames = try Engine.vocab(directory.appendingPathComponent("vocab_word.txt"), nWord)
        let chars = try Engine.vocab(directory.appendingPathComponent("vocab_char.txt"), nChar)
        wordVocab = Dictionary(uniqueKeysWithValues: wordNames.enumerated().map { ($1, $0) })
        charVocab = Dictionary(chars.enumerated().map { ($1, $0) }, uniquingKeysWith: { a, _ in a })

        let rx = m["regex"] as! [String: String]
        urlRe = try Engine.py(rx["url"]!, ignoreCase: true)
        phoneRe = try Engine.py(rx["phone"]!)
        amountRe = try Engine.py(rx["amount"]!, ignoreCase: true)
        refRe = try Engine.py(rx["reference"]!, ignoreCase: true)
        negRe = try Engine.py(rx["negation"]!, ignoreCase: true)
        tokenRe = try Engine.py(rx["token"]!)
        digitsRe = try Engine.py("\\d+")
        wsRe = try Engine.py("\\s+")
        ws2Re = try Engine.py("\\s\\s+")
        signalIds = m["signal_ids"] as! [String]
        // JSONSerialization does not keep key order; signal_ids lists the pattern signals in Python's order.
        let pats = m["patterns"] as! [String: [String]]
        patterns = try signalIds.compactMap { sid in try pats[sid].map { (sid, try $0.map { try Engine.py($0, ignoreCase: true) }) } }
        reasonsText = m["reasons"] as! [String: String]
        negatable = Set(m["negatable"] as! [String])
        shorteners = Set(m["url_shorteners"] as! [String])
        riskyTlds = Set(m["risky_tlds"] as! [String])
        brands = m["imitated_brands"] as! [String]
        lureWords = Set(m["lure_words"] as! [String])
        stopWords = Set(m["stop_words"] as! [String])
        contextSignals = Set(m["context_signals"] as! [String])
        zeroWidth = Array(m["zero_width"] as! String)
        let w = (m["word"] as! [String: Any])["ngram_range"] as! [Int]
        let c = (m["char"] as! [String: Any])["ngram_range"] as! [Int]
        wordRange = (w[0], w[1]); charRange = (c[0], c[1])
        signalWeight = (m["signal_weight"] as! NSNumber).doubleValue
        riskIntercept = ((m["risk"] as! [String: Any])["intercept"] as! NSNumber).doubleValue
        let type = m["type"] as! [String: Any]
        classes = type["classes"] as! [String]
        typeIntercept = (type["intercept"] as! [NSNumber]).map(\.doubleValue)
        let th = m["thresholds"] as! [String: NSNumber]
        thresholdHigh = th["high"]!.doubleValue; thresholdMedium = th["medium"]!.doubleValue
        maxReasons = m["max_reasons"] as! Int; maxPhrases = m["max_phrases"] as! Int
        taxonomy = m["taxonomy"] as! [String: [String: Any]]
        askOrder = m["ask_order"] as! [String]
        askSignals = (m["ask_signals"] as! [String: [String]]).mapValues(Set.init)
        cautionText = m["cautions"] as! [String: String]
        let thread = m["thread"] as! [String: Int]
        threadMaxMessages = thread["max_messages"]!; threadMaxChars = thread["max_chars"]!
        headerRe = try Engine.py(m["conversation_header"] as! String)
        version = m["version"] as? String ?? "?"
    }

    public enum EngineError: Error { case badModel(String) }

    /// The model folder bundled as a resource ("model") in the app or an extension.
    public static func bundled(in bundle: Bundle = .main, withTypeModel: Bool = true) throws -> Engine {
        guard let dir = bundle.url(forResource: "model", withExtension: nil) else { throw EngineError.badModel("model folder missing from \(bundle.bundlePath)") }
        return try Engine(directory: dir, withTypeModel: withTypeModel)
    }

    // Python's re is Unicode-aware for \w \d \b \s; ICU (NSRegularExpression) is too.
    private static func py(_ src: String, ignoreCase: Bool = false) throws -> NSRegularExpression {
        let s = src.hasPrefix("(?u)") ? String(src.dropFirst(4)) : src
        return try NSRegularExpression(pattern: s, options: ignoreCase ? [.caseInsensitive] : [])
    }

    private static func vocab(_ url: URL, _ n: Int) throws -> [String] {
        // Split on "\n" only: char n-grams can start or end with spaces.
        let text = try String(contentsOf: url, encoding: .utf8)
        let lines = text.split(separator: "\n", omittingEmptySubsequences: false).prefix(n).map(String.init)
        guard lines.count == n else { throw EngineError.badModel("\(url.lastPathComponent) has \(lines.count) terms, expected \(n)") }
        return lines
    }

    // Little-endian reads straight from the mapped weights file.
    @inline(__always) private func f64(_ index: Int) -> Double {
        weights.withUnsafeBytes { Double(bitPattern: UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: index * 8, as: UInt64.self))) }
    }
    @inline(__always) private func f32(_ index: Int) -> Double {
        let base = 8 * (nWord + nChar + nFeat)
        return weights.withUnsafeBytes { Double(Float(bitPattern: UInt32(littleEndian: $0.loadUnaligned(fromByteOffset: base + index * 4, as: UInt32.self)))) }
    }
    private func wordIdf(_ j: Int) -> Double { f64(j) }
    private func charIdf(_ j: Int) -> Double { f64(nWord + j) }
    private func riskCoef(_ j: Int) -> Double { f64(nWord + nChar + j) }

    // MARK: Regex helpers (NSString / UTF-16 ranges)
    private func matches(_ re: NSRegularExpression, _ s: String) -> [NSTextCheckingResult] {
        re.matches(in: s, range: NSRange(s.startIndex..., in: s))
    }
    private func first(_ re: NSRegularExpression, _ s: String) -> NSTextCheckingResult? {
        re.firstMatch(in: s, range: NSRange(s.startIndex..., in: s))
    }
    private func replace(_ re: NSRegularExpression, _ s: String, _ with: String) -> String {
        re.stringByReplacingMatches(in: s, range: NSRange(s.startIndex..., in: s), withTemplate: NSRegularExpression.escapedTemplate(for: with))
    }
    private func str(_ s: String, _ r: NSRange) -> String { (s as NSString).substring(with: r) }
    /// Python slices by code point: the last `n` Unicode scalars before UTF-16 offset `utf16Start`.
    private func lastScalars(_ s: String, before utf16Start: Int, _ n: Int) -> String {
        let prefix = (s as NSString).substring(to: utf16Start)
        return String(String.UnicodeScalarView(prefix.unicodeScalars.suffix(n)))
    }

    // MARK: signals.py
    public func normalize(_ text: String) -> String {
        var t = text.precomposedStringWithCompatibilityMapping // NFKC
        t.removeAll { zeroWidth.contains($0) }
        t = t.replacingOccurrences(of: "\u{2019}", with: "'").replacingOccurrences(of: "\u{2018}", with: "'")
            .replacingOccurrences(of: "\u{201C}", with: "\"").replacingOccurrences(of: "\u{201D}", with: "\"")
        return replace(wsRe, t, " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func extractUrls(_ text: String) -> [String] {
        matches(urlRe, text).map { var u = str(text, $0.range); while let l = u.last, ".,;:!?)".contains(l) { u.removeLast() }; return u }
    }

    func findPhones(_ text: String) -> [String] {
        matches(phoneRe, text).compactMap { m in
            let g = str(text, m.range)
            guard g.unicodeScalars.filter({ CharacterSet.decimalDigits.contains($0) }).count >= 9 else { return nil }
            if first(refRe, lastScalars(text, before: m.range.location, 16)) != nil { return nil }
            return g.trimmingCharacters(in: .whitespacesAndNewlines)
        }
    }

    private func host(_ raw: String) -> String {
        var url = raw
        if url.range(of: "^https?://", options: [.regularExpression, .caseInsensitive]) == nil { url = "http://" + url }
        if let r = url.range(of: "^[a-zA-Z][a-zA-Z0-9+.-]*://", options: .regularExpression) { url.removeSubrange(r) }
        let netloc = String(url.split(omittingEmptySubsequences: false, whereSeparator: { "/?#".contains($0) }).first ?? "")
        var h = netloc.components(separatedBy: "@").last ?? ""
        if h.hasPrefix("[") { h = String(h.dropFirst().prefix { $0 != "]" }) } else { h = h.components(separatedBy: ":").first ?? "" }
        return h.lowercased()
    }

    func isSuspiciousUrl(_ url: String) -> Bool {
        let h = host(url)
        if h.isEmpty { return false }
        if shorteners.contains(h) { return true }
        if h.range(of: "^\\d{1,3}(\\.\\d{1,3}){3}$", options: .regularExpression) != nil { return true }
        let labels = h.components(separatedBy: ".")
        if riskyTlds.contains(labels.last!) { return true }
        let reg = labels.count >= 2 ? labels[labels.count - 2] : h
        if reg.contains("-") && brands.contains(where: { reg.contains($0) }) { return true }
        if reg.contains("-") && reg.components(separatedBy: "-").contains(where: { lureWords.contains($0) }) { return true }
        if labels.count >= 4 && brands.contains(where: { labels.dropLast(2).joined(separator: ".").contains($0) }) { return true }
        return false
    }

    private func negated(_ sid: String, _ text: String, _ start: Int) -> Bool {
        negatable.contains(sid) && first(negRe, lastScalars(text, before: start, 60)) != nil
    }

    public func detect(_ text: String) -> [SignalHit] {
        let norm = normalize(text)
        var hits: [SignalHit] = []
        for (sid, pats) in patterns {
            var found: String?
            outer: for p in pats {
                for m in matches(p, norm) where !negated(sid, norm, m.range.location) { found = str(norm, m.range); break outer }
            }
            if let f = found { hits.append(SignalHit(id: sid, reason: reasonsText[sid]!, evidence: f)) }
        }
        let urls = extractUrls(norm)
        if let u = urls.first {
            hits.append(SignalHit(id: "has_link", reason: reasonsText["has_link"]!, evidence: u))
            if let bad = urls.first(where: isSuspiciousUrl) { hits.append(SignalHit(id: "suspicious_link", reason: reasonsText["suspicious_link"]!, evidence: bad)) }
        }
        if let p = findPhones(norm).first { hits.append(SignalHit(id: "has_phone_number", reason: reasonsText["has_phone_number"]!, evidence: p)) }
        if let a = first(amountRe, norm) { hits.append(SignalHit(id: "money_amount", reason: reasonsText["money_amount"]!, evidence: str(norm, a.range))) }
        return hits
    }

    // MARK: model.py
    public func preprocess(_ text: String) -> String {
        var t = normalize(text).lowercased()
        t = replace(urlRe, t, " __url__ ")
        for p in findPhones(t) { t = t.replacingOccurrences(of: p, with: " __phone__ ") }
        t = replace(amountRe, t, " __amount__ ")
        t = replace(digitsRe, t, "0")
        return replace(wsRe, t, " ").trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private func wordNgrams(_ pre: String) -> [String] {
        let s = pre.lowercased()
        let toks = matches(tokenRe, s).map { str(s, $0.range) }
        var grams: [String] = []
        for n in wordRange.0...wordRange.1 where toks.count >= n {
            for i in 0...(toks.count - n) { grams.append(toks[i..<(i + n)].joined(separator: " ")) }
        }
        return grams
    }

    private func charNgrams(_ pre: String) -> [String] {
        let doc = replace(ws2Re, pre.lowercased(), " ")
        var grams: [String] = []
        for raw in doc.split(whereSeparator: { $0.isWhitespace }) {
            let w = Array((" " + raw + " ").unicodeScalars)
            let piece = { (a: Int, b: Int) in String(String.UnicodeScalarView(w[a..<min(b, w.count)])) }
            for n in charRange.0...charRange.1 {
                var off = 0
                grams.append(piece(off, off + n))
                while off + n < w.count { off += 1; grams.append(piece(off, off + n)) }
                if off == 0 { break }
            }
        }
        return grams
    }

    private func tfidf(_ grams: [String], _ vocab: [String: Int], _ idf: (Int) -> Double, offset: Int, into x: inout [(Int, Double)]) {
        var counts: [Int: Int] = [:]
        for g in grams { if let j = vocab[g] { counts[j, default: 0] += 1 } }
        let vals = counts.keys.sorted().map { j in (j, (log(Double(counts[j]!)) + 1) * idf(j)) }
        let norm = sqrt(vals.reduce(0) { $0 + $1.1 * $1.1 })
        for (j, v) in vals { x.append((j + offset, v / (norm > 0 ? norm : 1))) }
    }

    /// Sparse features in the Python featurizer's column order.
    func features(_ text: String) -> [(Int, Double)] {
        let pre = preprocess(text)
        var x: [(Int, Double)] = []
        tfidf(wordNgrams(pre), wordVocab, wordIdf, offset: 0, into: &x)
        tfidf(charNgrams(pre), charVocab, charIdf, offset: nWord, into: &x)
        let fired = Set(detect(text).map(\.id))
        for (k, sid) in signalIds.enumerated() where fired.contains(sid) { x.append((nWord + nChar + k, signalWeight)) }
        return x
    }

    private func isReadablePhrase(_ name: String) -> Bool {
        if name.contains("__") { return false }
        return !name.components(separatedBy: " ").allSatisfy { w in
            stopWords.contains(w) || w.hasPrefix("__") || (!w.isEmpty && w.unicodeScalars.allSatisfy { CharacterSet.decimalDigits.contains($0) }) || w.unicodeScalars.count < 3
        }
    }

    public func level(_ score: Double) -> String { score >= thresholdHigh ? "high" : score >= thresholdMedium ? "medium" : "low" }

    // MARK: triage.py
    /// Risk only (no type model, no explanations): what the SMS filter extension needs.
    public func riskScore(_ text: String) -> Double {
        let logit = features(text).reduce(riskIntercept) { $0 + $1.1 * riskCoef($1.0) }
        return 1 / (1 + exp(-logit))
    }

    public func triage(_ text: String) -> Result {
        let x = features(text)
        var logit = riskIntercept
        var contrib: [(Int, Double)] = []
        contrib.reserveCapacity(x.count)
        for (j, v) in x { let c = v * riskCoef(j); logit += c; contrib.append((j, c)) }
        let score = 1 / (1 + exp(-logit))
        let lvl = level(score)

        var probs = [Double](repeating: 1 / Double(max(classes.count, 1)), count: classes.count)
        if withTypeModel {
            var z = typeIntercept
            for (j, v) in x { for k in 0..<nClasses { z[k] += v * f32(k * nFeat + j) } }
            let zMax = z.max() ?? 0
            let ez = z.map { exp($0 - zMax) }
            let zs = ez.reduce(0, +)
            probs = ez.map { $0 / zs }
        }
        let best = probs.indices.max { probs[$0] < probs[$1] } ?? 0

        // Largest contribution first; ties broken by column index, like scipy's sorted indices.
        contrib.sort { $0.1 != $1.1 ? $0.1 > $1.1 : $0.0 < $1.0 }
        var signalContrib: [String: Double] = [:]
        for (j, c) in contrib where j >= nWord + nChar { signalContrib[signalIds[j - nWord - nChar]] = c }
        let allHits = detect(text)
        var hits = allHits.filter { (signalContrib[$0.id] ?? 0) > 0 }
        if hits.contains(where: { $0.id == "suspicious_link" }) { hits.removeAll { $0.id == "has_link" } }
        if lvl == "low" { hits.removeAll { contextSignals.contains($0.id) } }
        hits = hits.enumerated().sorted { a, b in
            let ca = contextSignals.contains(a.element.id), cb = contextSignals.contains(b.element.id)
            if ca != cb { return !ca }
            let wa = signalContrib[a.element.id]!, wb = signalContrib[b.element.id]!
            return wa != wb ? wa > wb : a.offset < b.offset // stable, like Python's sort
        }.map(\.element)
        let reasons = hits.prefix(maxReasons).map(\.reason)
        var phrases = Array(contrib.lazy.filter { $0.1 > 0 && $0.0 < self.nWord }.map { self.wordNames[$0.0] }.filter(isReadablePhrase).prefix(maxPhrases))

        let typeId: String, conf: Double, summary: String
        if lvl == "low" {
            phrases = []
            typeId = "legit"; conf = 1 - score
            summary = "No strong scam patterns found." + (reasons.isEmpty ? "" : " A few things are worth double-checking, though.")
        } else {
            typeId = classes[best]; conf = probs[best]
            let st = taxonomy[typeId]!
            summary = "\(lvl == "high" ? "This looks like a scam" : "This could be a scam"): \((st["label"] as! String).lowercased()). \(st["description"] as! String)"
        }
        let st = taxonomy[typeId]!
        let asks = asksFrom(allHits)
        return Result(riskScore: Engine.round4(score), riskLevel: lvl, scamType: typeId, scamTypeLabel: st["label"] as! String,
                      typeConfidence: Engine.round4(conf), summary: summary, reasons: reasons, keyPhrases: phrases,
                      nextSteps: st["next_steps"] as! [String], signals: allHits,
                      asks: asks, cautions: lvl == "low" ? cautionsFor(asks) : [])
    }

    // MARK: Safety net + conversations (triage.py)
    private func asksFrom(_ hits: [SignalHit]) -> [String] {
        let fired = Set(hits.map(\.id))
        return askOrder.filter { !askSignals[$0]!.isDisjoint(with: fired) }
    }

    public func asksIn(_ text: String) -> [String] { asksFrom(detect(text)) }

    public func cautionsFor(_ asks: [String]) -> [String] { asks.map { cautionText[$0]! } }

    public func threadWindow(_ messages: [String]) -> [String] {
        var msgs = Array(messages.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }.suffix(threadMaxMessages))
        while msgs.count > 1 && msgs.joined(separator: "\n").unicodeScalars.count > threadMaxChars { msgs.removeFirst() }
        return msgs
    }

    /// The latest message judged in the light of the conversation so far (oldest first).
    public func triageThread(_ messages: [String]) -> Result {
        let msgs = threadWindow(messages)
        precondition(!msgs.isEmpty, "no messages")
        var latest = triage(msgs.last!)
        if msgs.count == 1 { return latest }
        var whole = triage(msgs.joined(separator: "\n"))
        let rank = ["low": 0, "medium": 1, "high": 2]
        if rank[whole.riskLevel]! > rank[latest.riskLevel]! {
            let st = taxonomy[whole.scamType]!
            let lead = whole.riskLevel == "high" ? "Taken together, these messages look like a scam" : "Taken together, these messages could be a scam"
            whole = Result(riskScore: whole.riskScore, riskLevel: whole.riskLevel, scamType: whole.scamType, scamTypeLabel: whole.scamTypeLabel,
                           typeConfidence: whole.typeConfidence, summary: "\(lead): \((st["label"] as! String).lowercased()). \(st["description"] as! String)",
                           reasons: whole.reasons, keyPhrases: whole.keyPhrases, nextSteps: whole.nextSteps, signals: whole.signals,
                           asks: whole.asks, cautions: whole.cautions, threadSize: msgs.count, fromContext: true)
            return whole
        }
        latest.threadSize = msgs.count
        latest.asks = whole.asks
        latest.cautions = latest.riskLevel == "low" ? cautionsFor(whole.asks) : []
        return latest
    }

    /// Split text copied from a WhatsApp chat into messages (oldest first); otherwise [text].
    public func splitConversation(_ text: String) -> [String] {
        // Python's str.splitlines() boundaries; a trailing line break does not add an empty line.
        var lines = text.components(separatedBy: "\r\n").flatMap { $0.split(omittingEmptySubsequences: false, whereSeparator: { c in
            c.unicodeScalars.count == 1 && Engine.lineBreaks.contains(c.unicodeScalars.first!) }).map(String.init) }
        if lines.count > 1 && lines.last == "" { lines.removeLast() }
        var messages: [String] = []
        var headers = 0
        for line in lines {
            if let m = first(headerRe, line), m.range.location == 0 {
                headers += 1
                messages.append((line as NSString).substring(from: m.range.length))
            } else if !messages.isEmpty {
                messages[messages.count - 1] += "\n" + line
            } else {
                messages.append(line)
            }
        }
        if headers < 2 { return [text] }
        return messages.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
    }

    private static let lineBreaks: Set<Unicode.Scalar> = ["\n", "\r", "\u{0B}", "\u{0C}", "\u{1C}", "\u{1D}", "\u{1E}", "\u{85}", "\u{2028}", "\u{2029}"]

    /// One message, or a pasted conversation judged as a whole.
    public func triageText(_ text: String) -> Result {
        let msgs = splitConversation(text)
        return msgs.count > 1 ? triageThread(msgs) : triage(text)
    }

    /// Whole-number percent with round-half-even, like Python's f"{x:.0%}".
    public static func pct0(_ x: Double) -> Int {
        let v = x * 100, f = v.rounded(.down)
        if abs(v - f - 0.5) < 1e-9 { return Int(f) % 2 == 0 ? Int(f) : Int(f) + 1 }
        return Int(v.rounded())
    }

    /// The reply the WhatsApp bot sends (twin of scam_triage/reply.py).
    public func formatReply(_ r: Result) -> String {
        let badge = ["high": "🔴 HIGH RISK", "medium": "🟠 MEDIUM RISK", "low": "🟢 LOW RISK"][r.riskLevel]!
        var lines = ["\(badge) (\(Engine.pct0(r.riskScore))%)", ""]
        if r.riskLevel == "low" { lines.append("*\(r.scamTypeLabel).* \(r.summary)") }
        else {
            lines.append("*Likely scam type:* \(r.scamTypeLabel)")
            lines.append(r.summary.range(of: ". ").map { String(r.summary[$0.upperBound...]) } ?? r.summary)
        }
        if r.fromContext { lines.append("_Based on the last \(r.threadSize) messages together._") }
        if !r.reasons.isEmpty { lines += ["", "*Why:*"] + r.reasons.map { "• \($0)" } }
        if !r.cautions.isEmpty { lines += ["", "*Before you act:*"] + r.cautions.map { "• \($0)" } }
        if !r.nextSteps.isEmpty { lines += ["", "*What to do:*"] + r.nextSteps.map { "• \($0)" } }
        lines += ["", "_Automated check. It can be wrong. When in doubt, verify through a channel you already trust._"]
        return lines.joined(separator: "\n")
    }

    private static func round4(_ v: Double) -> Double { (v * 1e4).rounded() / 1e4 }
}
