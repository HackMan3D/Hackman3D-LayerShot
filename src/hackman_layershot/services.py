import concurrent.futures, ipaddress, json, os, platform, re, socket, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

def asset_path(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return root / "assets" / name

def request_json(url, method="GET", payload=None, timeout=4, form=False):
    # Independently distributed macOS applications signed ad hoc can be denied
    # direct local-network sockets without macOS ever displaying its permission
    # dialog. The system curl executable remains able to perform the request.
    if platform.system() == "Darwin":
        command = [
            "/usr/bin/curl", "--silent", "--show-error", "--fail",
            "--connect-timeout", str(timeout), "--max-time", str(timeout),
            "--request", method,
        ]
        if payload is not None:
            content_type = ("application/x-www-form-urlencoded" if form
                            else "application/json")
            body = (urllib.parse.urlencode(payload) if form
                    else json.dumps(payload))
            command.extend([
                "--header", f"Content-Type: {content_type}",
                "--data-binary", body,
            ])
        command.append(url)
        # launchd becomes the responsible process for this short-lived request.
        # This avoids the broken Local Network prompt seen with ad-hoc app bundles.
        with tempfile.TemporaryDirectory(prefix="layershot-network-") as folder:
            output_path = os.path.join(folder, "response.json")
            error_path = os.path.join(folder, "error.txt")
            label = f"com.hackman3d.layershot.request.{uuid.uuid4().hex}"
            command[1:1] = ["--output", output_path]
            try:
                submitted = subprocess.run(
                    ["/bin/launchctl", "submit", "-l", label, "-e", error_path,
                     "--", *command],
                    capture_output=True, text=True, timeout=2)
                if submitted.returncode:
                    raise ConnectionError(
                        submitted.stderr.strip() or "Unable to start the network request.")
                deadline = time.monotonic() + timeout + 1
                while time.monotonic() < deadline:
                    if os.path.exists(output_path) and os.path.getsize(output_path):
                        with open(output_path, encoding="utf-8") as response:
                            return json.load(response)
                    if os.path.exists(error_path) and os.path.getsize(error_path):
                        with open(error_path, encoding="utf-8") as error_file:
                            detail = error_file.read().strip()
                        if detail:
                            raise ConnectionError(detail)
                    time.sleep(0.05)
                raise TimeoutError("The printer did not answer in time.")
            finally:
                subprocess.run(
                    ["/bin/launchctl", "remove", label],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    data = None
    headers = {}
    if payload is not None:
        data = (urllib.parse.urlencode(payload) if form
                else json.dumps(payload)).encode()
        headers["Content-Type"] = ("application/x-www-form-urlencoded" if form
                                   else "application/json")
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}

def normalize_host(host):
    value = host.strip()
    if not value:
        raise ValueError("The network address is empty.")
    parsed = urllib.parse.urlsplit(value if "://" in value else f"http://{value}")
    if not parsed.hostname:
        raise ValueError("The network address is invalid.")
    return parsed.hostname, parsed.port

def printer_status(host, port):
    hostname, address_port = normalize_host(host)
    candidates = []
    for candidate in (address_port, port, 4408, 7125, 80):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    errors = []
    for candidate in candidates:
        try:
            base = f"http://{hostname}:{candidate}"
            info = request_json(
                base + "/printer/objects/query?print_stats&display_status&virtual_sdcard",
                timeout=3)
            result = info.get("result", {}).get("status")
            if not isinstance(result, dict):
                raise ValueError("Moonraker returned an unexpected response.")
            stats = result.get("print_stats", {})
            virtual_sd = result.get("virtual_sdcard", {})
            if virtual_sd.get("layer") is not None:
                stats.setdefault("info", {})["current_layer"] = virtual_sd.get("layer")
            if virtual_sd.get("layer_count"):
                stats.setdefault("info", {})["total_layer"] = virtual_sd.get("layer_count")
            return stats, result.get("display_status", {}), candidate
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
    detail = errors[-1].split(": ", 1)[-1] if errors else "Unknown network error"
    raise ConnectionError(
        f"Moonraker was not found at {hostname}. Tried ports "
        f"{', '.join(map(str, candidates))}. Last error: {detail}")

def _local_ipv4_networks():
    addresses = set()
    try:
        if platform.system() == "Darwin":
            output = subprocess.check_output(
                ["/usr/sbin/ipconfig", "getiflist"], text=True, timeout=2)
            for interface in output.split():
                try:
                    address = subprocess.check_output(
                        ["/usr/sbin/ipconfig", "getifaddr", interface],
                        text=True, stderr=subprocess.DEVNULL, timeout=1).strip()
                    if address:
                        addresses.add(address)
                except Exception:
                    pass
        else:
            output = subprocess.check_output(
                ["hostname", "-I"], text=True, stderr=subprocess.DEVNULL, timeout=2)
            addresses.update(output.split())
    except Exception:
        pass
    networks = []
    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
            if ip.version == 4 and ip.is_private and not ip.is_loopback:
                networks.append(ipaddress.ip_network(f"{ip}/24", strict=False))
        except ValueError:
            pass
    return list(dict.fromkeys(networks))

def _open_moonraker_port(host):
    for port in (4408, 7125, 80):
        try:
            with socket.create_connection((host, port), timeout=.18):
                return port
        except OSError:
            continue
    return None

def _guess_printer_model(*values):
    text = " ".join(str(value or "") for value in values).lower()
    patterns = [
        ("SparkX i7", (r"spark[\s_-]*x[\s_-]*i7", r"sparkxi7")),
        ("K2 Plus", (r"\bk2[\s_-]*plus\b", r"\bk2plus\b")),
        ("K2", (r"\bk2\b",)),
        ("K1 Max", (r"\bk1[\s_-]*max\b", r"\bk1max\b")),
        ("K1C", (r"\bk1c\b",)),
        ("K1", (r"\bk1\b",)),
        ("Ender-3 V3 Plus", (r"ender[\s_-]*3[\s_-]*v3[\s_-]*plus",)),
        ("Ender-3 V3 KE", (r"ender[\s_-]*3[\s_-]*v3[\s_-]*ke",)),
        ("Ender-3 V3 SE", (r"ender[\s_-]*3[\s_-]*v3[\s_-]*se",)),
        ("Ender-3 V3", (r"ender[\s_-]*3[\s_-]*v3",)),
        ("Hi Combo", (r"\bhi[\s_-]*combo\b",)),
        ("Hi", (r"\bcreality[\s_-]*hi\b",)),
    ]
    for model, expressions in patterns:
        if any(re.search(expression, text) for expression in expressions):
            return model
    return "Other Moonraker / Klipper"

def _describe_moonraker(host, port):
    base = f"http://{host}:{port}"
    server = request_json(base + "/server/info", timeout=1.2)
    result = server.get("result", {})
    if not isinstance(result, dict):
        raise ValueError("Invalid Moonraker response")
    hostname = ""
    system = {}
    try:
        system = request_json(base + "/machine/system_info", timeout=1.2).get("result", {}).get("system_info", {})
        hostname = system.get("hostname", "")
    except Exception:
        pass
    components = result.get("components", [])
    identity = " ".join([
        hostname, result.get("hostname", ""), result.get("software_version", ""),
        json.dumps(system, ensure_ascii=False),
    ])
    model = _guess_printer_model(identity)
    try:
        config_file = request_json(
            base + "/printer/objects/query?configfile=settings", timeout=2
        ).get("result", {}).get("status", {}).get("configfile", {})
        settings = config_file.get("settings", {})
        kinematics = settings.get("printer", {}).get("kinematics", "")
        x_max = float(settings.get("stepper_x", {}).get("position_max", 0))
        z_max = float(settings.get("stepper_z", {}).get("position_max", 0))
        if model == "Other Moonraker / Klipper":
            # Creality's Moonraker builds usually omit the commercial model
            # name. Their mechanics and advertised travel still allow a useful
            # best-effort identification.
            if kinematics == "cartesian" and 250 <= x_max <= 290 and 240 <= z_max <= 280:
                model = "SparkX i7"
            elif kinematics == "corexy" and x_max >= 330:
                model = "K2 Plus"
            elif kinematics == "corexy" and 245 <= x_max <= 285:
                model = "K2"
            elif kinematics == "corexy" and 215 <= x_max <= 235:
                model = "K1"
    except Exception:
        pass
    name = hostname or result.get("hostname") or model
    if not name or name == "Other Moonraker / Klipper":
        name = f"Klipper {host}"
    return {
        "name": name, "model": model, "host": host, "port": port,
        "version": result.get("moonraker_version", ""),
        "components": components,
    }

def discover_printers():
    hosts = []
    for network in _local_ipv4_networks():
        hosts.extend(str(host) for host in network.hosts())
    hosts = list(dict.fromkeys(hosts))
    if not hosts:
        return []
    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
        futures = {executor.submit(_open_moonraker_port, host): host for host in hosts}
        for future in concurrent.futures.as_completed(futures):
            port = future.result()
            if port:
                found.append((futures[future], port))
    printers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(_describe_moonraker, host, port) for host, port in found]
        for future in concurrent.futures.as_completed(futures):
            try:
                printers.append(future.result())
            except Exception:
                pass
    return sorted(printers, key=lambda printer: tuple(int(x) for x in printer["host"].split(".")))

_esp_address_cache = {}

def _arp_addresses():
    try:
        command = ["/usr/sbin/arp", "-a"] if platform.system() == "Darwin" else ["arp", "-a"]
        output = subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL, timeout=2)
        lines = [line for line in output.splitlines() if "incomplete" not in line.lower()]
        # Prefer the LayerShot DHCP name, then the Espressif OUI used by the
        # tested C3-Zero. This avoids trying every smart device on the LAN.
        espressif_prefixes = ("44:b1:76", "40:4c:ca", "7c:df:a1", "84:f7:03",
                              "c8:2e:18", "ec:da:3b", "f4:12:fa")
        def priority(line):
            lowered = line.lower()
            if "hackman-layershot" in lowered:
                return 0
            if any(prefix in lowered for prefix in espressif_prefixes):
                return 1
            return 2
        lines.sort(key=priority)
        addresses = []
        for line in lines:
            match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
            if not match:
                match = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", line)
            if match:
                addresses.append(match.group(1))
        return list(dict.fromkeys(addresses))
    except Exception:
        return []

def _esp_base(host):
    hostname, port = normalize_host(host)
    cache_key = hostname.lower()
    cached = _esp_address_cache.get(cache_key)
    candidates = [cached] if cached else []
    if hostname.endswith(".local"):
        candidates.extend([
            "hackman-layershot-001.lan",
            "hackman-layershot.lan",
        ])
        candidates.extend(_arp_addresses())
    candidates.append(hostname)
    for candidate in dict.fromkeys(x for x in candidates if x):
        base = f"http://{candidate}" + (f":{port}" if port else "")
        try:
            status = request_json(base + "/status", timeout=1)
            if status.get("name") == "Hackman3D LayerShot":
                _esp_address_cache[cache_key] = candidate
                return base, status
        except Exception:
            continue
    raise ConnectionError("Hackman3D LayerShot ESP32 was not found on the local network.")

def esp_post(host, endpoint, payload=None):
    base, _ = _esp_base(host)
    return request_json(
        f"{base}/{endpoint.lstrip('/')}",
        method="POST", payload=payload or {}, timeout=5, form=True)

def esp_status(host):
    base, status = _esp_base(host)
    status["_resolved_address"] = urllib.parse.urlsplit(base).hostname
    return status

def serial_ports():
    try:
        from serial.tools import list_ports
        ports = []
        for port in list_ports.comports():
            device = port.device.lower()
            if platform.system() == "Darwin":
                if port.vid is None and not any(
                        name in device for name in ("usbmodem", "usbserial", "wchusb", "slab_usb")):
                    continue
            ports.append(port.device)
        return ports
    except Exception:
        return []

def known_wifi_networks():
    try:
        if platform.system() == "Darwin":
            out = subprocess.check_output(
                ["/usr/sbin/networksetup", "-listpreferredwirelessnetworks", "en0"],
                text=True, stderr=subprocess.DEVNULL)
            return [x.strip() for x in out.splitlines()[1:] if x.strip()]
        out = subprocess.check_output(["netsh", "wlan", "show", "profiles"], text=True)
        return [x.split(":", 1)[1].strip() for x in out.splitlines() if "All User Profile" in x]
    except Exception:
        return []

def known_wifi_password(ssid):
    try:
        if platform.system() == "Darwin":
            login_keychain = str(Path.home() / "Library/Keychains/login.keychain-db")
            try:
                return subprocess.check_output(
                    ["/usr/bin/security", "find-generic-password",
                     "-s", "com.hackman3d.layershot.wifi", "-a", ssid,
                     "-w", login_keychain], text=True,
                    stderr=subprocess.DEVNULL).strip()
            except Exception:
                pass
            try:
                return subprocess.check_output(
                    ["/usr/bin/security", "find-generic-password", "-D",
                     "AirPort network password", "-a", ssid, "-w",
                     login_keychain], text=True,
                    stderr=subprocess.DEVNULL).strip()
            except Exception:
                pass
            escaped_ssid = ssid.replace("\\", "\\\\").replace('"', '\\"')
            script = (
                f'set wifiName to "{escaped_ssid}"\n'
                'set commandText to "/usr/bin/security find-generic-password '
                '-D \\"AirPort network password\\" -a " & quoted form of wifiName '
                '& " -w /Library/Keychains/System.keychain"\n'
                'do shell script commandText'
            )
            password = subprocess.check_output(
                ["/usr/bin/osascript", "-e", script], text=True,
                stderr=subprocess.DEVNULL).strip()
            if password:
                save_wifi_password(ssid, password)
            return password
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"], text=True)
        for line in out.splitlines():
            if "Key Content" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""

def save_wifi_password(ssid, password):
    if not ssid or not password:
        return False
    try:
        if platform.system() == "Darwin":
            login_keychain = str(Path.home() / "Library/Keychains/login.keychain-db")
            subprocess.run(
                ["/usr/bin/security", "add-generic-password", "-U",
                 "-s", "com.hackman3d.layershot.wifi", "-a", ssid,
                 "-w", password, login_keychain],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    except Exception:
        return False
    return False
