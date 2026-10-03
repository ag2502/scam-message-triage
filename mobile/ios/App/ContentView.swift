import SwiftUI
import ScamTriageKit

private let samples: [(String, String)] = [
    ("Hi Mum", "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now"),
    ("Parcel fee", "Royal Mail: your parcel is on hold due to an unpaid £1.99 redelivery fee. Pay within 24 hours: royalmail-redelivery.top/pay"),
    ("Code by mistake", "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?"),
    ("Real receipt", "Nubank: you sent a Pix of R$120.00 to Ana Souza."),
]

struct ContentView: View {
    @State private var text = ""
    @State private var result: Engine.Result?
    @State private var error: String?
    @Environment(\.openURL) private var openURL

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    filterCard
                    checkCard
                    howToCard
                    Text("Checks run on this iPhone. Messages are never uploaded, stored or shared. Automated checks can be wrong; when money is involved, call the person on a number you already have.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Scam Triage")
        }
        .tint(Color(red: 0.17, green: 0.31, blue: 0.84))
    }

    private var filterCard: some View {
        card {
            Label("Filter scam texts automatically", systemImage: "line.3.horizontal.decrease.circle.fill").font(.headline)
            Text("Scam SMS from unknown numbers go straight to your Junk folder. The check happens on your iPhone.")
                .font(.subheadline).foregroundStyle(.secondary)
            VStack(alignment: .leading, spacing: 6) {
                step(1, "Open Settings, then Apps, then Messages.")
                step(2, "Tap Unknown & Spam, then SMS Filtering.")
                step(3, "Choose Scam Triage.")
            }.font(.subheadline)
            Button("Open Settings") { if let u = URL(string: UIApplication.openSettingsURLString) { openURL(u) } }
                .buttonStyle(.borderedProminent)
            Text("Apple only lets filters see SMS from unknown senders. For WhatsApp, iMessage or contacts, use Share (below).")
                .font(.footnote).foregroundStyle(.secondary)
        }
    }

    private var checkCard: some View {
        card {
            Text("Check a message").font(.headline)
            TextEditor(text: $text)
                .frame(minHeight: 110)
                .padding(8)
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(Color.secondary.opacity(0.3)))
                .accessibilityLabel("Message to check")
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    PasteButton(payloadType: String.self) { strings in
                        Task { @MainActor in if let s = strings.first { run(s) } }
                    }
                    ForEach(samples, id: \.0) { s in Button(s.0) { run(s.1) }.buttonStyle(.bordered) }
                }
            }
            Button("Check") { run(text) }.buttonStyle(.borderedProminent).disabled(text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            if let error { Text(error).foregroundStyle(.red).font(.footnote) }
            if let result { VerdictView(result: result).padding(.top, 4) }
        }
    }

    private var howToCard: some View {
        card {
            Text("WhatsApp, iMessage and everything else").font(.headline)
            step(1, "Long-press the message and tap Share (or select the text, then Share).")
            step(2, "Choose Check for Scam. The verdict opens on top of the chat.")
            step(3, "Or ask Siri: \"Check a message with Scam Triage\".")
        }
        .font(.subheadline)
    }

    private func run(_ t: String) {
        text = t
        let input = t
        Task {
            do { result = try await EngineProvider.shared.triage(input); error = nil }
            catch { self.error = "The model could not be loaded." }
        }
    }

    private func step(_ n: Int, _ s: String) -> some View {
        Label { Text(s) } icon: { Text("\(n)").font(.subheadline.monospaced().weight(.bold)).foregroundStyle(.tint) }
    }

    private func card<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12, content: content)
            .padding(18)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 18))
    }
}
