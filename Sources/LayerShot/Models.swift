import Foundation
import AppKit
import AVFoundation

struct PrinterSnapshot: Sendable {
    var state = "inconnue"
    var filename = ""
    var layer: Int?
    var totalLayers: Int?
    var progress: Double?
}

enum LayerShotError: LocalizedError {
    case invalidAddress, invalidResponse, printerUnavailable, espUnavailable
    var errorDescription: String? {
        switch self {
        case .invalidAddress: "Adresse incorrecte. Exemple : 192.168.1.42"
        case .invalidResponse: "La réponse reçue n’est pas reconnue."
        case .printerUnavailable: "Impossible de joindre l’imprimante."
        case .espUnavailable: "Impossible de joindre le boîtier LayerShot."
        }
    }
}

final class CrealityConnector: @unchecked Sendable {
    private let session: URLSession = {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 12
        configuration.timeoutIntervalForResource = 45
        configuration.waitsForConnectivity = true
        return URLSession(configuration: configuration)
    }()

    func snapshot(host: String, port: Int) async throws -> PrinterSnapshot {
        let request = try makeRequest(host: host, port: port)
        let (data, response) = try await session.data(for: request)
        return try parse(data: data, response: response)
    }

    func snapshot(host: String, port: Int, completion: @escaping @Sendable (Result<PrinterSnapshot, Error>) -> Void) {
        do {
            let request = try makeRequest(host: host, port: port)
            session.dataTask(with: request) { [self] data, response, error in
                if let error { completion(.failure(error)); return }
                do { completion(.success(try parse(data: data ?? Data(), response: response))) }
                catch { completion(.failure(error)) }
            }.resume()
        } catch { completion(.failure(error)) }
    }

    func snapshotUsingSystemNetwork(host: String, port: Int, completion: @escaping @Sendable (Result<PrinterSnapshot, Error>) -> Void) {
        let clean = host.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "http://", with: "")
            .replacingOccurrences(of: "https://", with: "")
        guard !clean.isEmpty, (1...65535).contains(port) else { completion(.failure(LayerShotError.invalidAddress)); return }
        let url = "http://\(clean):\(port)/printer/objects/query?print_stats&virtual_sdcard&display_status"
        let process = Process()
        let output = Pipe(); let errors = Pipe()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
        process.arguments = ["--silent", "--show-error", "--max-time", "8", "--fail-with-body", url]
        process.standardOutput = output; process.standardError = errors
        process.terminationHandler = { [self] task in
            let data = output.fileHandleForReading.readDataToEndOfFile()
            if task.terminationStatus == 0 {
                do { completion(.success(try parseJSON(data: data))) }
                catch { completion(.failure(error)) }
            } else {
                let detail = String(data: errors.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                completion(.failure(NSError(domain: "LayerShot.Network", code: Int(task.terminationStatus), userInfo: [NSLocalizedDescriptionKey: detail.isEmpty ? "Connexion impossible" : detail])))
            }
        }
        do { try process.run() } catch { completion(.failure(error)) }
    }

    private func makeRequest(host: String, port: Int) throws -> URLRequest {
        let clean = host.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "http://", with: "")
            .replacingOccurrences(of: "https://", with: "")
        guard let url = URL(string: "http://\(clean):\(port)/printer/objects/query?print_stats&virtual_sdcard&display_status") else {
            throw LayerShotError.invalidAddress
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 4
        return request
    }

    private func parse(data: Data, response: URLResponse?) throws -> PrinterSnapshot {
        guard (response as? HTTPURLResponse)?.statusCode == 200,
              !data.isEmpty else {
            throw LayerShotError.invalidResponse
        }
        return try parseJSON(data: data)
    }

    private func parseJSON(data: Data) throws -> PrinterSnapshot {
        guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LayerShotError.invalidResponse }
        let result = root["result"] as? [String: Any]
        let status = result?["status"] as? [String: Any] ?? result ?? root
        let printStats = status["print_stats"] as? [String: Any] ?? [:]
        let virtualSD = status["virtual_sdcard"] as? [String: Any] ?? [:]
        let display = status["display_status"] as? [String: Any] ?? [:]

        var snap = PrinterSnapshot()
        snap.state = (printStats["state"] as? String) ?? "connectée"
        snap.filename = (printStats["filename"] as? String) ?? ""
        snap.progress = number(virtualSD["progress"]) ?? number(display["progress"])
        snap.layer = findInt(keys: ["current_layer", "layer", "currentLayer"], in: status)
        snap.totalLayers = findInt(keys: ["total_layer", "total_layers", "totalLayer", "layer_count"], in: status)
        return snap
    }

    private func number(_ value: Any?) -> Double? {
        if let n = value as? NSNumber { return n.doubleValue }
        if let s = value as? String { return Double(s) }
        return nil
    }

    private func findInt(keys: Set<String>, in value: Any) -> Int? {
        if let object = value as? [String: Any] {
            for (key, item) in object where keys.contains(key) {
                if let n = item as? NSNumber { return n.intValue }
                if let s = item as? String, let n = Int(s) { return n }
            }
            for item in object.values {
                if let found = findInt(keys: keys, in: item) { return found }
            }
        } else if let array = value as? [Any] {
            for item in array {
                if let found = findInt(keys: keys, in: item) { return found }
            }
        }
        return nil
    }
}

final class ESPConnector: @unchecked Sendable {
    func trigger(host: String) async throws {
        _ = try await request(host: host, path: "/trigger", method: "POST")
    }

    func status(host: String) async throws -> [String: Any] {
        let data = try await request(host: host, path: "/status", method: "GET")
        guard let object = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw LayerShotError.invalidResponse }
        return object
    }

    func pair(host: String, clear: Bool = false) async throws {
        _ = try await request(host: host, path: clear ? "/reset-bonds" : "/pair", method: "POST")
    }

    func configure(host: String, ssid: String, password: String) async throws {
        let body = "ssid=\(form(ssid))&password=\(form(password))"
        _ = try await request(host: host, path: "/configure", method: "POST", body: body)
    }

    func configurePrinter(host: String, printerHost: String, port: Int, every: Int, skip: Int, stopAfter: Int, delayMilliseconds: Int) async throws {
        let body = "host=\(form(printerHost))&port=\(port)&every=\(every)&skip=\(skip)&stop=\(stopAfter)&delay=\(delayMilliseconds)"
        _ = try await request(host: host, path: "/printer-config", method: "POST", body: body)
    }

    private func request(host: String, path: String, method: String, body: String? = nil) async throws -> Data {
        let clean = host.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "http://", with: "")
            .replacingOccurrences(of: "https://", with: "")
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        guard !clean.isEmpty else { throw LayerShotError.invalidAddress }
        return try await withCheckedThrowingContinuation { continuation in
            let process = Process()
            let output = Pipe(); let errors = Pipe()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
            process.arguments = ["--silent", "--show-error", "--max-time", "5", "--fail-with-body", "-X", method] +
                (body.map { ["-H", "Content-Type: application/x-www-form-urlencoded", "--data", $0] } ?? []) +
                ["http://\(clean)\(path)"]
            process.standardOutput = output; process.standardError = errors
            process.terminationHandler = { task in
                let data = output.fileHandleForReading.readDataToEndOfFile()
                if task.terminationStatus == 0 { continuation.resume(returning: data) }
                else {
                    let detail = String(data: errors.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                    continuation.resume(throwing: NSError(domain: "LayerShot.ESP", code: Int(task.terminationStatus), userInfo: [NSLocalizedDescriptionKey: detail.isEmpty ? LayerShotError.espUnavailable.localizedDescription : detail]))
                }
            }
            do { try process.run() } catch { continuation.resume(throwing: error) }
        }
    }

    private func form(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""
    }
}

struct TimelapseOptions: Sendable {
    var fps = 30
    var width = 1920
    var height = 1080
    var fill = false
    var zoom = 1.0
    var panX = 0.0
    var panY = 0.0
    var rotation = 0
    var mirror = false
    var fade = false
    var addLogo = false
    var removeDuplicates = false
    var removeBlurred = false
}

enum TimelapseMaker {
    static func create(images: [URL], destination: URL, options: TimelapseOptions, logoURL: URL?, progress: @escaping @Sendable (Double) -> Void) async throws {
        let size = CGSize(width: options.width, height: options.height)
        let filtered = filter(images: images, options: options)
        try? FileManager.default.removeItem(at: destination)
        let writer = try AVAssetWriter(outputURL: destination, fileType: .mp4)
        let settings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: Int(size.width), AVVideoHeightKey: Int(size.height),
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: options.width >= 3000 ? 24_000_000 : 10_000_000]
        ]
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
        let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
            kCVPixelBufferWidthKey as String: Int(size.width), kCVPixelBufferHeightKey as String: Int(size.height)
        ])
        guard writer.canAdd(input) else { throw LayerShotError.invalidResponse }
        writer.add(input); writer.startWriting(); writer.startSession(atSourceTime: .zero)
        for (index, url) in filtered.enumerated() {
            while !input.isReadyForMoreMediaData { try await Task.sleep(for: .milliseconds(10)) }
            if let image = NSImage(contentsOf: url), let buffer = pixelBuffer(image: image, size: size, pool: adaptor.pixelBufferPool, options: options, index: index, count: filtered.count, logoURL: logoURL) {
                adaptor.append(buffer, withPresentationTime: CMTime(value: Int64(index), timescale: Int32(options.fps)))
            }
            progress(Double(index + 1) / Double(max(filtered.count, 1)))
        }
        input.markAsFinished()
        await writer.finishWriting()
        if writer.status != .completed { throw writer.error ?? LayerShotError.invalidResponse }
    }

    private static func pixelBuffer(image: NSImage, size: CGSize, pool: CVPixelBufferPool?, options: TimelapseOptions, index: Int, count: Int, logoURL: URL?) -> CVPixelBuffer? {
        guard let pool, let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        var buffer: CVPixelBuffer?
        guard CVPixelBufferPoolCreatePixelBuffer(nil, pool, &buffer) == kCVReturnSuccess, let buffer else { return nil }
        CVPixelBufferLockBaseAddress(buffer, [])
        defer { CVPixelBufferUnlockBaseAddress(buffer, []) }
        guard let context = CGContext(data: CVPixelBufferGetBaseAddress(buffer), width: Int(size.width), height: Int(size.height), bitsPerComponent: 8, bytesPerRow: CVPixelBufferGetBytesPerRow(buffer), space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue) else { return nil }
        context.setFillColor(NSColor.black.cgColor); context.fill(CGRect(origin: .zero, size: size))
        context.saveGState()
        context.translateBy(x: size.width / 2, y: size.height / 2)
        if options.mirror { context.scaleBy(x: -1, y: 1) }
        context.rotate(by: CGFloat(options.rotation) * .pi / 180)
        let rotated = options.rotation % 180 != 0
        let sourceWidth = rotated ? CGFloat(cg.height) : CGFloat(cg.width)
        let sourceHeight = rotated ? CGFloat(cg.width) : CGFloat(cg.height)
        let baseScale = (options.fill ? max : min)(size.width / sourceWidth, size.height / sourceHeight)
        let scale = baseScale * CGFloat(max(options.zoom, 0.1))
        let target = CGSize(width: CGFloat(cg.width) * scale, height: CGFloat(cg.height) * scale)
        let x = -target.width / 2 + CGFloat(options.panX) * size.width / 2
        let y = -target.height / 2 + CGFloat(options.panY) * size.height / 2
        if options.fade {
            let edge = max(1, min(count / 10, options.fps))
            let alpha = min(1, min(CGFloat(index + 1) / CGFloat(edge), CGFloat(count - index) / CGFloat(edge)))
            context.setAlpha(alpha)
        }
        context.draw(cg, in: CGRect(x: x, y: y, width: target.width, height: target.height))
        context.restoreGState()
        if options.addLogo, let logoURL, let logo = NSImage(contentsOf: logoURL), let logoCG = logo.cgImage(forProposedRect: nil, context: nil, hints: nil) {
            let logoWidth = size.width * 0.13
            let logoHeight = logoWidth * CGFloat(logoCG.height) / CGFloat(logoCG.width)
            context.setAlpha(0.82)
            context.draw(logoCG, in: CGRect(x: size.width - logoWidth - 28, y: 28, width: logoWidth, height: logoHeight))
        }
        return buffer
    }

    private static func filter(images: [URL], options: TimelapseOptions) -> [URL] {
        guard options.removeDuplicates || options.removeBlurred else { return images }
        var output: [URL] = []
        var previous: [UInt8]?
        for url in images {
            guard let image = NSImage(contentsOf: url), let sample = sample(image) else { continue }
            if options.removeBlurred && sharpness(sample) < 7 { continue }
            if options.removeDuplicates, let previous, difference(sample, previous) < 1.2 { continue }
            output.append(url)
            previous = sample
        }
        return output.isEmpty ? images : output
    }

    private static func sample(_ image: NSImage) -> [UInt8]? {
        guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return nil }
        var bytes = [UInt8](repeating: 0, count: 32 * 32)
        guard let context = CGContext(data: &bytes, width: 32, height: 32, bitsPerComponent: 8, bytesPerRow: 32, space: CGColorSpaceCreateDeviceGray(), bitmapInfo: 0) else { return nil }
        context.draw(cg, in: CGRect(x: 0, y: 0, width: 32, height: 32))
        return bytes
    }

    private static func difference(_ a: [UInt8], _ b: [UInt8]) -> Double {
        zip(a, b).reduce(0.0) { $0 + abs(Double($1.0) - Double($1.1)) } / Double(max(a.count, 1))
    }

    private static func sharpness(_ pixels: [UInt8]) -> Double {
        var total = 0.0
        for y in 1..<31 {
            for x in 1..<31 {
                let i = y * 32 + x
                total += abs(Double(pixels[i]) * 4 - Double(pixels[i-1]) - Double(pixels[i+1]) - Double(pixels[i-32]) - Double(pixels[i+32]))
            }
        }
        return total / 900
    }
}
