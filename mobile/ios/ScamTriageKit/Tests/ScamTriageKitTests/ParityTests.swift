import Foundation
import Testing
@testable import ScamTriageKit

/// The Swift engine must reproduce Python's triage() on every golden case (scripts/export_mobile.py).
struct ParityTests {
    static let shared = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("shared") // -> mobile/shared
    static let engine = try! Engine(directory: shared.appendingPathComponent("model"))
    struct Golden: Decodable, Sendable {
        let text: String
        let risk_score: Double
        let risk_level: String
        let scam_type: String
        let reasons: [String]
        let key_phrases: [String]
        let signals: [[String]]
        let asks: [String]
        let cautions: [String]
        let reply: String
    }
    struct ThreadCase: Decodable, Sendable {
        let messages: [String]
        let risk_level: String
        let scam_type: String
        let from_context: Bool
        let thread_size: Int
        let summary: String
        let asks: [String]
        let cautions: [String]
        let reply: String
    }
    struct SplitCase: Decodable, Sendable { let text: String; let messages: [String] }
    static func jsonl<T: Decodable>(_ name: String, _: T.Type) -> [T] {
        let text = try! String(contentsOf: shared.appendingPathComponent("golden/\(name)"), encoding: .utf8)
        return text.split(separator: "\n").map { try! JSONDecoder().decode(T.self, from: Data($0.utf8)) }
    }
    static let golden: [Golden] = {
        let text = try! String(contentsOf: shared.appendingPathComponent("golden/golden.jsonl"), encoding: .utf8)
        return text.split(separator: "\n").map { try! JSONDecoder().decode(Golden.self, from: Data($0.utf8)) }
    }()

    @Test func signalsMatchPython() {
        var bad: [String] = []
        for g in Self.golden {
            let text = g.text
            let expected = g.signals.map { $0[0] + "|" + $0[1] }
            let got = Self.engine.detect(text).map { $0.id + "|" + $0.evidence }
            if got != expected { bad.append("\(text.prefix(50)) | py=\(expected) swift=\(got)") }
        }
        #expect(bad.isEmpty, "\(bad.count)/\(Self.golden.count) differ:\n\(bad.prefix(5).joined(separator: "\n"))")
    }

    @Test func triageMatchesPython() {
        var bad: [String] = []
        for g in Self.golden {
            let text = g.text
            let r = Self.engine.triage(text)
            let ok = abs(r.riskScore - g.risk_score) <= 2e-4 && r.riskLevel == g.risk_level && r.scamType == g.scam_type &&
                r.reasons == g.reasons && r.keyPhrases == g.key_phrases
            if !ok { bad.append("\(text.prefix(50)) | py=\(g.risk_level)/\(g.scam_type)/\(g.key_phrases) swift=\(r.riskLevel)/\(r.scamType)/\(r.keyPhrases)") }
        }
        #expect(bad.isEmpty, "\(bad.count)/\(Self.golden.count) differ:\n\(bad.prefix(5).joined(separator: "\n"))")
    }

    @Test func riskOnlyEngineAgrees() throws {
        let lean = try Engine(directory: Self.shared.appendingPathComponent("model"), withTypeModel: false)
        for g in Self.golden.prefix(80) {
            let text = g.text
            #expect(abs(lean.riskScore(text) - Self.engine.riskScore(text)) < 1e-12)
        }
    }

    @Test func replyFormat() {
        let r = Self.engine.triage("Hi Mum, new number. Send R$800 by Pix now, can't talk")
        #expect(r.riskLevel == "high")
        #expect(Self.engine.formatReply(r).hasPrefix("🔴 HIGH RISK"))
    }

    @Test func safetyNetAndReplyTextMatchPython() {
        let bad = Self.golden.filter { g in
            let r = Self.engine.triage(g.text)
            return r.asks != g.asks || r.cautions != g.cautions || Self.engine.formatReply(r) != g.reply
        }
        #expect(bad.isEmpty, "\(bad.count)/\(Self.golden.count) differ, e.g. \(bad.prefix(3).map { $0.text.prefix(50) })")
    }

    @Test func conversationsMatchPython() {
        let cases = Self.jsonl("threads.jsonl", ThreadCase.self)
        let bad = cases.filter { c in
            let r = Self.engine.triageThread(c.messages)
            return r.riskLevel != c.risk_level || r.scamType != c.scam_type || r.fromContext != c.from_context ||
                r.threadSize != c.thread_size || r.summary != c.summary || r.asks != c.asks || r.cautions != c.cautions ||
                Self.engine.formatReply(r) != c.reply
        }
        #expect(bad.isEmpty, "\(bad.count)/\(cases.count) differ, e.g. \(bad.prefix(3).map { $0.messages.last!.prefix(40) })")
    }

    @Test func splitConversationMatchesPython() {
        for c in Self.jsonl("split.jsonl", SplitCase.self) { #expect(Self.engine.splitConversation(c.text) == c.messages) }
    }
}
