import Foundation
import ScamTriageKit

/// Loads the bundled model once per process, off the main thread.
actor EngineProvider {
    static let shared = EngineProvider()
    private var engine: Engine?

    func get() throws -> Engine {
        if let engine { return engine }
        let e = try Engine.bundled()
        engine = e
        return e
    }

    /// One message, or a shared/pasted WhatsApp conversation judged as a whole.
    func triage(_ text: String) async throws -> Engine.Result {
        try get().triageText(text)
    }
}
