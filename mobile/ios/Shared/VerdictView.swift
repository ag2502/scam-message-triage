import SwiftUI
import ScamTriageKit

/// The explained verdict, shared by the app and the Share extension.
struct VerdictView: View {
    let result: Engine.Result

    private var color: Color {
        switch result.riskLevel {
        case "high": return Color(red: 0.79, green: 0.20, blue: 0.16)
        case "medium": return Color(red: 0.66, green: 0.40, blue: 0.04)
        default: return Color(red: 0.10, green: 0.50, blue: 0.29)
        }
    }
    private var levelLabel: String { ["high": "High risk", "medium": "Medium risk", "low": "Low risk"][result.riskLevel] ?? "" }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label(levelLabel, systemImage: result.riskLevel == "low" ? "checkmark.shield.fill" : "exclamationmark.shield.fill")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(color)
                    .padding(.horizontal, 12).padding(.vertical, 6)
                    .background(color.opacity(0.12), in: Capsule())
                Spacer()
                Text("\(Engine.pct0(result.riskScore))%")
                    .font(.system(size: 30, weight: .bold, design: .monospaced))
                    .foregroundStyle(color)
            }
            Text(result.riskLevel == "low" ? result.scamTypeLabel : "Likely: \(result.scamTypeLabel)")
                .font(.title3.weight(.semibold))
            Text(result.riskLevel == "low" ? result.summary : (result.summary.components(separatedBy: ". ").dropFirst().joined(separator: ". ")))
                .font(.subheadline).foregroundStyle(.secondary)
            if result.fromContext {
                Label("Judged as a conversation: the last \(result.threadSize) messages together raised the risk.", systemImage: "square.stack.3d.up.fill")
                    .font(.footnote.weight(.semibold)).foregroundStyle(.tint)
            }
            if !result.cautions.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    Label("Before you act", systemImage: "hand.raised.fill").font(.footnote.weight(.semibold))
                        .foregroundStyle(Color(red: 0.66, green: 0.40, blue: 0.04))
                    ForEach(result.cautions, id: \.self) { Text($0).font(.subheadline) }
                }
                .padding(12).frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(red: 0.78, green: 0.48, blue: 0.04).opacity(0.13), in: RoundedRectangle(cornerRadius: 12))
            }
            if !result.reasons.isEmpty {
                section("Why") {
                    ForEach(result.reasons, id: \.self) { r in
                        Label { Text(r) } icon: { Image(systemName: "flag.fill").foregroundStyle(color) }
                    }
                }
            }
            section("What to do") {
                ForEach(Array(result.nextSteps.enumerated()), id: \.offset) { i, s in
                    Label { Text(s) } icon: { Text("\(i + 1)").font(.headline.monospaced()).foregroundStyle(.tint) }
                }
            }
        }
        .accessibilityElement(children: .contain)
    }

    @ViewBuilder private func section<Content: View>(_ title: String, @ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.footnote.weight(.semibold)).foregroundStyle(.secondary)
            content().font(.subheadline)
        }
    }
}
