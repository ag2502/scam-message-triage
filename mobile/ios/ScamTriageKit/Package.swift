// swift-tools-version: 6.0
// Swift port of scam_triage, shared by the iOS app, its Share extension and its SMS filter extension.
import PackageDescription

let package = Package(
    name: "ScamTriageKit",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [.library(name: "ScamTriageKit", targets: ["ScamTriageKit"])],
    targets: [
        .target(name: "ScamTriageKit"),
        .testTarget(name: "ScamTriageKitTests", dependencies: ["ScamTriageKit"]),
    ]
)
