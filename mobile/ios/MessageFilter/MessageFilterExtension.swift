import IdentityLookup
import ScamTriageKit

/// SMS/MMS filter for unknown senders: scam texts go to Junk. Runs entirely on-device (no network URL is
/// configured, so iOS never sends message content anywhere). Uses the risk-only engine to stay well
/// within the extension's memory budget.
final class MessageFilterExtension: ILMessageFilterExtension {
    private static let engine: Engine? = try? Engine.bundled(in: Bundle(for: MessageFilterExtension.self), withTypeModel: false)
}

extension MessageFilterExtension: ILMessageFilterQueryHandling {
    func handle(_ queryRequest: ILMessageFilterQueryRequest, context: ILMessageFilterExtensionContext,
                completion: @escaping (ILMessageFilterQueryResponse) -> Void) {
        let response = ILMessageFilterQueryResponse()
        response.action = Self.action(for: queryRequest.messageBody)
        completion(response)
    }

    /// High risk goes to Junk; everything else is left alone (false alarms in Junk are costly).
    static func action(for body: String?) -> ILMessageFilterAction {
        guard let body, !body.isEmpty, let engine else { return .none }
        return engine.level(engine.riskScore(body)) == "high" ? .junk : .none
    }
}
