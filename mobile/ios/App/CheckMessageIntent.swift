import AppIntents
import ScamTriageKit

/// "Check a message with Scam Triage": usable from Siri, Spotlight and the Shortcuts app.
struct CheckMessageIntent: AppIntent {
    static let title: LocalizedStringResource = "Check Message for Scam"
    static let description = IntentDescription("Checks a message for scam patterns on your iPhone and explains the risk.")

    @Parameter(title: "Message", inputOptions: String.IntentInputOptions(multiline: true))
    var message: String

    static var parameterSummary: some ParameterSummary { Summary("Check \(\.$message) for scams") }

    func perform() async throws -> some IntentResult & ReturnsValue<String> & ProvidesDialog {
        let r = try await EngineProvider.shared.triage(message)
        let level = ["high": "High risk", "medium": "Medium risk", "low": "Low risk"][r.riskLevel] ?? r.riskLevel
        let spoken = r.riskLevel == "low"
            ? "\(level). No strong scam patterns found."
            : "\(level): \(r.scamTypeLabel). \(r.nextSteps.first ?? "")"
        return .result(value: r.riskLevel, dialog: IntentDialog(stringLiteral: spoken))
    }
}

struct ScamTriageShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: CheckMessageIntent(),
            phrases: ["Check a message with \(.applicationName)", "Is this a scam in \(.applicationName)"],
            shortTitle: "Check Message",
            systemImageName: "checkmark.shield"
        )
    }
}
