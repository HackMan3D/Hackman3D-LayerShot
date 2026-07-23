import Foundation
import AppKit
import WebKit
import UniformTypeIdentifiers
import Network
import CoreWLAN
import CoreLocation

private struct SavedPrinter: Codable {
    var host: String
    var port: Int
    var name: String
    var model: String
}

final class AppBridge: NSObject, WKScriptMessageHandler, @unchecked Sendable {
    weak var webView: WKWebView?
    private let printer = CrealityConnector()
    private let esp = ESPConnector()
    private var isMonitoring = false
    private var isStatusPolling = false
    private var statusPollers: Set<String> = []
    private var savedPrinters: [String: SavedPrinter] = [:]
    private var lastLayer: Int?
    private var photos: [URL] = []
    private var permissionBrowser: NWBrowser?
    private var permissionConnection: NWConnection?
    private var captureLog: [[String: Any]] = []
    private let locationManager = CLLocationManager()

    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any] else { return }
        handle(body)
    }

    private func handle(_ body: [String: Any]) {
        let action = body["action"] as? String ?? ""
        let host = body["printerHost"] as? String ?? ""
        let port = body["port"] as? Int ?? 4408
        let espHost = body["espHost"] as? String ?? "hackman-layershot.local"
        let printerName = body["printerName"] as? String ?? ""
        let printerModel = body["printerModel"] as? String ?? "Creality / Klipper"
        switch action {
        case "testPrinter":
            testPrinter(host: host, port: port, attempt: 1, name: printerName, model: printerModel)
        case "removePrinter":
            removePrinter(key: body["printerKey"] as? String ?? "")
        case "testShutter":
            Task { do { try await esp.trigger(host: espHost); status("triggerSent") } catch { errorStatus(error) } }
        case "testESP":
            Task { do { let info = try await esp.status(host: espHost); js("updateESP(\(json(info)));setAutonomous(\((info["autonomous"] as? Bool) == true ? "true" : "false"))"); statusText("ESP32 connecté · \(info["firmware"] as? String ?? "")") } catch { errorStatus(error) } }
        case "pairESP":
            Task { do { try await esp.pair(host: espHost); statusText("Mode appairage activé pendant 3 minutes.") } catch { errorStatus(error) } }
        case "clearPairing":
            Task { do { try await esp.pair(host: espHost, clear: true); statusText("Ancien iPhone oublié. Vous pouvez recommencer l’appairage.") } catch { errorStatus(error) } }
        case "configureESP":
            Task { do { try await esp.configure(host: espHost, ssid: body["ssid"] as? String ?? "", password: body["wifiPassword"] as? String ?? ""); statusText("Wi-Fi enregistré. L’ESP32 redémarre…") } catch { errorStatus(error) } }
        case "scanWiFi":
            scanWiFi()
        case "wifiPassword":
            retrieveWiFiPassword(ssid: body["ssid"] as? String ?? "")
        case "scanUSB":
            js("setSerialPorts(\(json(serialPorts())))")
        case "flash":
            flash(port: body["serialPort"] as? String ?? "")
        case "start":
            captureLog.removeAll()
            start(host: host, port: port, espHost: espHost, every: body["every"] as? Int ?? 1,
                  skip: body["skip"] as? Int ?? 0, stopAfter: body["stopAfter"] as? Int ?? 0,
                  delay: body["captureDelay"] as? Double ?? 0)
        case "configureAutonomous":
            let every = body["every"] as? Int ?? 1
            let skip = body["skip"] as? Int ?? 0
            let stopAfter = body["stopAfter"] as? Int ?? 0
            let delay = Int((body["captureDelay"] as? Double ?? 1) * 1000)
            Task {
                do {
                    try await esp.configurePrinter(host: espHost, printerHost: host, port: port, every: every, skip: skip, stopAfter: stopAfter, delayMilliseconds: delay)
                    statusText("Réglages enregistrés dans l’ESP32. Le mode autonome est actif, vous pouvez fermer l’app.")
                    js("setAutonomous(true)")
                } catch { errorStatus(error) }
            }
        case "stop": isMonitoring = false; status("monitorStopped"); js("setMonitoring(false)")
        case "import": importPhotos()
        case "export": export(options: timelapseOptions(body))
        case "exportDiagnostics": exportDiagnostics(host: host, port: port, espHost: espHost)
        case "openURL":
            if let rawURL = body["url"] as? String, let url = URL(string: rawURL), ["https", "mailto"].contains(url.scheme?.lowercased() ?? "") {
                NSWorkspace.shared.open(url)
            }
        case "save":
            UserDefaults.standard.set(host, forKey: "printerHost"); UserDefaults.standard.set(port, forKey: "printerPort"); UserDefaults.standard.set(espHost, forKey: "espHost")
        case "language":
            if let language = body["language"] as? String { UserDefaults.standard.set(language, forKey: "language") }
        case "ready":
            let savedHost = UserDefaults.standard.string(forKey: "printerHost") ?? ""
            let savedPort = UserDefaults.standard.integer(forKey: "printerPort")
            var savedESP = UserDefaults.standard.string(forKey: "espHost") ?? "hackman-layershot.local"
            if savedESP == "layershot.local" { savedESP = "hackman-layershot.local"; UserDefaults.standard.set(savedESP, forKey: "espHost") }
            let language = UserDefaults.standard.string(forKey: "language") ?? Locale.current.language.languageCode?.identifier ?? "fr"
            js("restoreSettings(\(json(["printerHost": savedHost, "port": savedPort == 0 ? 4408 : savedPort, "espHost": savedESP, "language": language])))")
            js("setSerialPorts(\(json(serialPorts())))")
            loadSavedPrinters()
        case "quit":
            NSApp.terminate(nil)
        default: break
        }
    }

    private func start(host: String, port: Int, espHost: String, every: Int, skip: Int, stopAfter: Int, delay: Double) {
        isMonitoring = true; js("setMonitoring(true)"); status("monitorActive")
        pollPrinter(host: host, port: port, espHost: espHost, every: every, skip: skip, stopAfter: stopAfter, delay: delay)
    }

    private func pollPrinter(host: String, port: Int, espHost: String, every: Int, skip: Int, stopAfter: Int, delay: Double) {
        guard isMonitoring else { return }
        printer.snapshotUsingSystemNetwork(host: host, port: port) { [weak self] result in
            DispatchQueue.main.async {
                guard let self, self.isMonitoring else { return }
                switch result {
                case .success(let snap):
                    self.update(snap)
                    if let layer = snap.layer, layer != self.lastLayer {
                        if stopAfter > 0 && layer > stopAfter {
                            self.isMonitoring = false; self.js("setMonitoring(false)"); self.statusText("Surveillance terminée à la couche \(stopAfter).")
                        } else if self.lastLayer != nil && layer > skip && (layer - skip) % max(every, 1) == 0 {
                            Task {
                                if delay > 0 { try? await Task.sleep(for: .milliseconds(Int(delay * 1000))) }
                                do {
                                    try await self.esp.trigger(host: espHost)
                                    let entry: [String: Any] = ["layer": layer, "time": ISO8601DateFormatter().string(from: Date()), "result": "ok"]
                                    self.captureLog.append(entry); self.js("addCaptureLog(\(self.json(entry)))")
                                    self.statusText("📸 Couche \(layer)")
                                } catch {
                                    let entry: [String: Any] = ["layer": layer, "time": ISO8601DateFormatter().string(from: Date()), "result": "error"]
                                    self.captureLog.append(entry); self.js("addCaptureLog(\(self.json(entry)))")
                                    self.errorStatus(error)
                                }
                            }
                        }
                        self.lastLayer = layer
                    }
                case .failure(let error): self.errorStatus(error)
                }
                DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
                    self?.pollPrinter(host: host, port: port, espHost: espHost, every: every, skip: skip, stopAfter: stopAfter, delay: delay)
                }
            }
        }
    }

    private func requestLocalNetworkAccess(host: String, port: Int) {
        permissionBrowser?.cancel()
        permissionConnection?.cancel()
        let parameters = NWParameters.tcp
        parameters.includePeerToPeer = true
        let browser = NWBrowser(for: .bonjour(type: "_http._tcp", domain: nil), using: parameters)
        browser.stateUpdateHandler = { _ in }
        browser.browseResultsChangedHandler = { _, _ in }
        browser.start(queue: .main)
        permissionBrowser = browser
        if let networkPort = NWEndpoint.Port(rawValue: UInt16(clamping: port)) {
            let connection = NWConnection(host: NWEndpoint.Host(host), port: networkPort, using: .tcp)
            connection.stateUpdateHandler = { [weak self, weak connection] state in
                if case .ready = state { connection?.cancel(); self?.permissionConnection = nil }
                if case .failed = state { connection?.cancel(); self?.permissionConnection = nil }
            }
            connection.start(queue: .main)
            permissionConnection = connection
        }
    }

    private func testPrinter(host: String, port: Int, attempt: Int, name: String, model: String) {
        if attempt == 1 {
            requestLocalNetworkAccess(host: host, port: port)
            statusText("Demande d’accès au réseau local…")
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { [weak self] in
                self?.testPrinter(host: host, port: port, attempt: 2, name: name, model: model)
            }
            return
        }
        printer.snapshotUsingSystemNetwork(host: host, port: port) { [weak self] result in
            DispatchQueue.main.async {
                guard let self else { return }
                switch result {
                case .success(let snapshot):
                    self.permissionBrowser?.cancel(); self.permissionBrowser = nil
                    self.permissionConnection?.cancel(); self.permissionConnection = nil
                    let cleanHost = self.cleanHost(host)
                    let key = "\(cleanHost):\(port)"
                    let profile = SavedPrinter(host: cleanHost, port: port, name: name.isEmpty ? model : name, model: model)
                    self.savedPrinters[key] = profile
                    self.savePrinters()
                    self.updateCard(snapshot, profile: profile, camera: nil)
                    self.detectCamera(for: profile)
                    self.status("printerConnected")
                    self.startProfilePolling(profile)
                case .failure where attempt < 4:
                    self.statusText("Autorisation du réseau local en cours… nouvelle tentative \(attempt + 1)/4.")
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
                        self?.testPrinter(host: host, port: port, attempt: attempt + 1, name: name, model: model)
                    }
                case .failure(let error):
                    self.permissionBrowser?.cancel(); self.permissionBrowser = nil
                    self.permissionConnection?.cancel(); self.permissionConnection = nil
                    self.errorStatus(error)
                }
            }
        }
    }

    private func startProfilePolling(_ profile: SavedPrinter) {
        let key = "\(profile.host):\(profile.port)"
        guard !statusPollers.contains(key) else { return }
        statusPollers.insert(key)
        pollProfile(profile)
    }

    private func pollProfile(_ profile: SavedPrinter) {
        let key = "\(profile.host):\(profile.port)"
        guard statusPollers.contains(key) else { return }
        printer.snapshotUsingSystemNetwork(host: profile.host, port: profile.port) { [weak self] result in
            DispatchQueue.main.async {
                guard let self, self.statusPollers.contains(key) else { return }
                if case .success(let snapshot) = result { self.updateCard(snapshot, profile: profile, camera: nil) }
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
                    self?.pollProfile(profile)
                }
            }
        }
    }

    private func loadSavedPrinters() {
        guard let data = UserDefaults.standard.data(forKey: "savedPrinters"),
              let profiles = try? JSONDecoder().decode([SavedPrinter].self, from: data) else { return }
        for profile in profiles {
            savedPrinters["\(profile.host):\(profile.port)"] = profile
            js("ensurePrinterCard(\(json(["key": "\(profile.host):\(profile.port)", "host": profile.host, "port": profile.port, "name": profile.name, "model": profile.model])))")
            startProfilePolling(profile)
            detectCamera(for: profile)
        }
    }

    private func savePrinters() {
        if let data = try? JSONEncoder().encode(Array(savedPrinters.values)) {
            UserDefaults.standard.set(data, forKey: "savedPrinters")
        }
    }

    private func removePrinter(key: String) {
        statusPollers.remove(key)
        savedPrinters.removeValue(forKey: key)
        savePrinters()
        js("removePrinterCard(\(json(key)))")
    }

    private func cleanHost(_ host: String) -> String {
        host.trimmingCharacters(in: .whitespacesAndNewlines)
            .replacingOccurrences(of: "http://", with: "")
            .replacingOccurrences(of: "https://", with: "")
            .split(separator: "/").first.map(String.init) ?? host
    }

    private func updateCard(_ snapshot: PrinterSnapshot, profile: SavedPrinter, camera: String?) {
        let key = "\(profile.host):\(profile.port)"
        js("updatePrinterCard(\(json(["key": key, "host": profile.host, "port": profile.port, "name": profile.name, "model": profile.model, "state": snapshot.state, "file": snapshot.filename, "layer": snapshot.layer.map { $0 as Any } ?? NSNull(), "totalLayers": snapshot.totalLayers.map { $0 as Any } ?? NSNull(), "progress": snapshot.progress.map { $0 as Any } ?? NSNull(), "camera": camera ?? NSNull()])))")
    }

    private func detectCamera(for profile: SavedPrinter) {
        let webcamList = "http://\(profile.host):\(profile.port)/server/webcams/list"
        let candidates = [
            "http://\(profile.host):8080/?action=stream",
            "http://\(profile.host):8080/webcam/?action=stream",
            "http://\(profile.host):\(profile.port)/webcam/?action=stream"
        ]
        DispatchQueue.global(qos: .utility).async { [weak self] in
            let listProcess = Process(); listProcess.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
            listProcess.arguments = ["--silent", "--max-time", "3", "--fail", webcamList]
            let listPipe = Pipe(); listProcess.standardOutput = listPipe
            do {
                try listProcess.run(); listProcess.waitUntilExit()
                let data = listPipe.fileHandleForReading.readDataToEndOfFile()
                if let root = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let result = root["result"] as? [String: Any],
                   let webcams = result["webcams"] as? [[String: Any]],
                   let stream = webcams.first(where: { ($0["enabled"] as? Bool) != false })?["stream_url"] as? String,
                   !stream.isEmpty {
                    let url = stream.hasPrefix("http") ? stream : "http://\(profile.host):\(profile.port)\(stream.hasPrefix("/") ? "" : "/")\(stream)"
                    DispatchQueue.main.async { self?.js("setPrinterCamera(\(self?.json(["key": "\(profile.host):\(profile.port)", "url": url]) ?? "null"))") }
                    return
                }
            } catch {}
            for candidate in candidates {
                let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/bin/curl")
                process.arguments = ["--silent", "--max-time", "2", "--range", "0-64", "--output", "/dev/null", "--write-out", "%{http_code}", candidate]
                let pipe = Pipe(); process.standardOutput = pipe
                do {
                    try process.run(); process.waitUntilExit()
                    let code = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
                    if code.hasPrefix("2") {
                        DispatchQueue.main.async { self?.js("setPrinterCamera(\(self?.json(["key": "\(profile.host):\(profile.port)", "url": candidate]) ?? "null"))") }
                        return
                    }
                } catch {}
            }
        }
    }

    private func importPhotos() {
        let panel = NSOpenPanel(); panel.allowsMultipleSelection = true; panel.canChooseDirectories = true; panel.allowedContentTypes = [.image]
        guard panel.runModal() == .OK else { return }
        var found: [URL] = []
        for url in panel.urls {
            var isDir: ObjCBool = false; FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir)
            if isDir.boolValue {
                found += ((try? FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: [.contentTypeKey])) ?? []).filter { (try? $0.resourceValues(forKeys: [.contentTypeKey]).contentType?.conforms(to: .image)) == true }
            } else { found.append(url) }
        }
        photos = found.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
        js("setPhotoCount(\(photos.count))")
    }

    private func export(options: TimelapseOptions) {
        guard !photos.isEmpty else { status("importFirst"); return }
        let panel = NSSavePanel(); panel.allowedContentTypes = [.mpeg4Movie]; panel.nameFieldStringValue = "timelapse.mp4"
        guard panel.runModal() == .OK, let destination = panel.url else { return }
        let source = photos; js("setExporting(true)")
        Task {
            do {
                let logo = Bundle.main.url(forResource: "Hackman3DLayerShot", withExtension: "png")
                try await TimelapseMaker.create(images: source, destination: destination, options: options, logoURL: logo) { value in DispatchQueue.main.async { self.js("setProgress(\(value))") } }
                status("exportDone")
            } catch { errorStatus(error) }
            js("setExporting(false)")
        }
    }

    private func timelapseOptions(_ body: [String: Any]) -> TimelapseOptions {
        let resolution = body["resolution"] as? String ?? "1080"
        let aspect = body["aspect"] as? String ?? "16:9"
        let long = resolution == "4k" ? 3840 : 1920
        let dims: (Int, Int)
        switch aspect {
        case "9:16": dims = (long == 3840 ? 2160 : 1080, long)
        case "4:3": dims = (long, long * 3 / 4)
        case "1:1": dims = (long, long)
        default: dims = (long, long * 9 / 16)
        }
        return TimelapseOptions(
            fps: body["fps"] as? Int ?? 30, width: dims.0, height: dims.1,
            fill: (body["framing"] as? String ?? "fit") == "fill",
            zoom: body["zoom"] as? Double ?? 1, panX: body["panX"] as? Double ?? 0,
            panY: body["panY"] as? Double ?? 0, rotation: body["rotation"] as? Int ?? 0,
            mirror: body["mirror"] as? Bool ?? false, fade: body["fade"] as? Bool ?? false,
            addLogo: body["addLogo"] as? Bool ?? false,
            removeDuplicates: body["removeDuplicates"] as? Bool ?? false,
            removeBlurred: body["removeBlurred"] as? Bool ?? false
        )
    }

    private func serialPorts() -> [String] {
        let directory = (try? FileManager.default.contentsOfDirectory(atPath: "/dev")) ?? []
        return directory.filter { $0.hasPrefix("cu.usbmodem") || $0.hasPrefix("cu.usbserial") || $0.hasPrefix("cu.wchusbserial") || $0.hasPrefix("cu.SLAB_USBtoUART") }.map { "/dev/\($0)" }.sorted()
    }

    private func scanWiFi() {
        if locationManager.authorizationStatus == .notDetermined {
            locationManager.requestWhenInUseAuthorization()
            statusText("Autorisez la localisation, puis cliquez de nouveau sur Rechercher. Elle sert uniquement à afficher les noms Wi-Fi.")
            return
        }
        statusText("Recherche des réseaux Wi-Fi…")
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            var names: Set<String> = []
            let interface = CWWiFiClient.shared().interface()
            if let current = interface?.ssid(), !current.isEmpty { names.insert(current) }
            do {
                let networks = try interface?.scanForNetworks(withSSID: nil) ?? []
                for network in networks {
                    if let ssid = network.ssid, !ssid.isEmpty { names.insert(ssid) }
                }
                DispatchQueue.main.async {
                    self.js("setWiFiNetworks(\(self.json(names.sorted())))")
                    self.statusText(names.isEmpty ? "Aucun réseau trouvé." : "\(names.count) réseau(x) trouvé(s).")
                }
            } catch {
                DispatchQueue.main.async {
                    self.js("setWiFiNetworks(\(self.json(Array(names).sorted())))")
                    self.statusText("macOS a limité la recherche Wi-Fi. Activez la localisation pour LayerShot si la liste reste vide.")
                }
            }
        }
    }

    private func retrieveWiFiPassword(ssid: String) {
        guard !ssid.isEmpty else { statusText("Sélectionnez d’abord un réseau Wi-Fi."); return }
        statusText("Demande d’accès au Trousseau macOS…")
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let process = Process(); let output = Pipe(); let errors = Pipe()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/security")
            process.arguments = ["find-generic-password", "-D", "AirPort network password", "-a", ssid, "-w"]
            process.standardOutput = output; process.standardError = errors
            do {
                try process.run(); process.waitUntilExit()
                let password = String(data: output.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
                DispatchQueue.main.async {
                    guard let self else { return }
                    if process.terminationStatus == 0, !password.isEmpty {
                        self.js("setWiFiPassword(\(self.json(password)))")
                        self.statusText("Mot de passe récupéré depuis le Trousseau.")
                    } else {
                        self.statusText("Mot de passe introuvable ou accès au Trousseau refusé.")
                    }
                }
            } catch {
                DispatchQueue.main.async { self?.errorStatus(error) }
            }
        }
    }

    private func flash(port: String) {
        guard !port.isEmpty else { statusText("Branchez l’ESP32 puis cliquez sur Détecter."); return }
        guard let tool = Bundle.main.url(forResource: "esptool", withExtension: nil),
              let boot = Bundle.main.url(forResource: "Hackman3DLayerShot.ino.bootloader", withExtension: "bin"),
              let partitions = Bundle.main.url(forResource: "Hackman3DLayerShot.ino.partitions", withExtension: "bin"),
              let app = Bundle.main.url(forResource: "Hackman3DLayerShot.ino", withExtension: "bin") else {
            statusText("Les fichiers du firmware sont absents de cette version."); return
        }
        statusText("Installation du firmware… ne débranchez pas la carte.")
        js("setFlashing(true)")
        let process = Process(); let pipe = Pipe()
        process.executableURL = tool
        process.arguments = ["--chip", "esp32c3", "--port", port, "--baud", "460800", "write-flash", "0x0", boot.path, "0x8000", partitions.path, "0x10000", app.path]
        process.standardOutput = pipe; process.standardError = pipe
        process.terminationHandler = { [weak self] task in
            let output = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            DispatchQueue.main.async {
                self?.js("setFlashing(false)")
                if task.terminationStatus == 0 { self?.statusText("Firmware installé. L’ESP32 redémarre.") }
                else { self?.statusText("Échec du flashage : \(output.suffix(500))") }
            }
        }
        do { try process.run() } catch { js("setFlashing(false)"); errorStatus(error) }
    }

    private func exportDiagnostics(host: String, port: Int, espHost: String) {
        let panel = NSSavePanel(); panel.allowedContentTypes = [.json]; panel.nameFieldStringValue = "LayerShot-diagnostic.json"
        guard panel.runModal() == .OK, let destination = panel.url else { return }
        let report: [String: Any] = ["app": "Hackman3D LayerShot", "version": Bundle.main.infoDictionary?["CFBundleShortVersionString"] ?? "",
          "date": ISO8601DateFormatter().string(from: Date()), "macOS": ProcessInfo.processInfo.operatingSystemVersionString,
          "printer": ["host": host, "port": port], "espHost": espHost, "serialPorts": serialPorts(), "captures": captureLog]
        do { try JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted, .sortedKeys]).write(to: destination); statusText("Diagnostic exporté.") }
        catch { errorStatus(error) }
    }

    private func update(_ s: PrinterSnapshot) { js("updatePrinter(\(json(["state": s.state, "file": s.filename, "layer": s.layer.map { $0 as Any } ?? NSNull(), "progress": s.progress.map { $0 as Any } ?? NSNull()])))") }
    private func status(_ key: String) { js("setStatus(t('\(key)'))") }
    private func statusText(_ text: String) { js("setStatus(\(json(text)))") }
    private func errorStatus(_ error: Error) {
        if let urlError = error as? URLError, urlError.code == .notConnectedToInternet {
            statusText("Accès au réseau local refusé. Ouvrez Réglages Système › Confidentialité et sécurité › Réseau local, puis autorisez LayerShot.")
        } else if let urlError = error as? URLError, urlError.code == .timedOut {
            statusText("Délai dépassé. Vérifiez l’adresse IP, le port et que le Mac est sur le même réseau que l’imprimante.")
        } else {
            statusText(error.localizedDescription)
        }
    }
    private func js(_ code: String) { webView?.evaluateJavaScript(code) }
    private func json(_ value: Any) -> String { guard let data = try? JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed]), let result = String(data: data, encoding: .utf8) else { return "null" }; return result }
}
