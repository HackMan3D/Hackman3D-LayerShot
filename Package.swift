// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "LayerShot",
    platforms: [.macOS(.v14)],
    products: [.executable(name: "LayerShot", targets: ["LayerShot"])],
    targets: [.executableTarget(name: "LayerShot")]
)
