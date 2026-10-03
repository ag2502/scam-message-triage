import SwiftUI
import UIKit
import UniformTypeIdentifiers
import ScamTriageKit

/// "Check for Scam" in the share sheet: reads the shared text and shows the verdict over the current app.
final class ShareViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        let host = UIHostingController(rootView: ShareView(load: { [weak self] in await self?.sharedText() ?? "" },
                                                           done: { [weak self] in self?.extensionContext?.completeRequest(returningItems: nil) }))
        addChild(host)
        host.view.frame = view.bounds
        host.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        view.addSubview(host.view)
        host.didMove(toParent: self)
    }

    private func sharedText() async -> String {
        var parts: [String] = []
        for item in extensionContext?.inputItems as? [NSExtensionItem] ?? [] {
            if let t = item.attributedContentText?.string, !t.isEmpty { parts.append(t) }
            for provider in item.attachments ?? [] {
                if provider.hasItemConformingToTypeIdentifier(UTType.plainText.identifier),
                   let t = try? await provider.loadItem(forTypeIdentifier: UTType.plainText.identifier) as? String { parts.append(t) }
                else if provider.hasItemConformingToTypeIdentifier(UTType.url.identifier),
                        let u = try? await provider.loadItem(forTypeIdentifier: UTType.url.identifier) as? URL { parts.append(u.absoluteString) }
            }
        }
        var seen = Set<String>()
        return parts.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty && seen.insert($0).inserted }
            .joined(separator: "\n").prefix(4000).description
    }
}

struct ShareView: View {
    let load: () async -> String
    let done: () -> Void
    @State private var text: String?
    @State private var result: Engine.Result?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let text, !text.isEmpty {
                        Text(text).font(.subheadline).lineLimit(6)
                            .padding(14).frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
                        if let result { VerdictView(result: result) } else { ProgressView().frame(maxWidth: .infinity) }
                    } else if text != nil {
                        Text("There was no text to check. Share the message's text, or copy it into the Scam Triage app.")
                    }
                    Text("Checked on this iPhone. Automated checks can be wrong.").font(.footnote).foregroundStyle(.secondary)
                }.padding()
            }
            .navigationTitle("Check for Scam")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done", action: done) } }
        }
        .tint(Color(red: 0.17, green: 0.31, blue: 0.84))
        .task {
            let t = await load()
            text = t
            if !t.isEmpty { result = try? await EngineProvider.shared.triage(t) }
        }
    }
}
