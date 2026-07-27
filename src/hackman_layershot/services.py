import concurrent.futures, ipaddress, json, os, platform, re, shutil, socket, subprocess, sys, tempfile, time, urllib.error, urllib.parse, urllib.request, uuid
from pathlib import Path

def hidden_subprocess_kwargs():
    if platform.system() == "Windows":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}

def asset_path(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return root / "assets" / name

def latest_layershot_release():
    return request_json(
        "https://api.github.com/repos/HackMan3D/Hackman3D-LayerShot/releases/latest",
        timeout=5)

def latest_firmware_catalog():
    return request_json(
        "https://raw.githubusercontent.com/HackMan3D/"
        "Hackman3D-LayerShot/main/firmware-manifest.json",
        timeout=6)

def download_firmware_url(url, cache_key):
    """Download and cache a firmware binary from the official GitHub catalog."""
    parsed = urllib.parse.urlsplit(str(url))
    if (parsed.scheme != "https" or
            parsed.hostname not in ("github.com", "objects.githubusercontent.com")):
        raise ValueError("The firmware URL is not an official GitHub download.")
    safe_key = re.sub(r"[^A-Za-z0-9._-]", "-", str(cache_key))
    destination = (
        Path(tempfile.gettempdir()) / "hackman3d-layershot-firmware" /
        f"{safe_key}.bin")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 100000:
        return destination
    partial = destination.with_suffix(".download")
    if platform.system() == "Darwin":
        subprocess.run(
            ["/usr/bin/curl", "--location", "--fail", "--silent",
             "--show-error", "--output", str(partial), str(url)],
            check=True, timeout=90)
    else:
        with urllib.request.urlopen(str(url), timeout=90) as response:
            with open(partial, "wb") as output:
                shutil.copyfileobj(response, output)
    if not partial.exists() or partial.stat().st_size < 100000:
        raise RuntimeError("The downloaded firmware file is incomplete.")
    partial.replace(destination)
    return destination

def download_release_asset(tag, name):
    """Download an official legacy firmware asset into the system cache."""
    safe_tag = re.sub(r"[^A-Za-z0-9._-]", "", str(tag))
    safe_name = Path(name).name
    if not safe_tag or not safe_name.lower().endswith(".bin"):
        raise ValueError("The selected firmware version is invalid.")
    url = (
        "https://github.com/HackMan3D/Hackman3D-LayerShot/releases/download/"
        f"{urllib.parse.quote(safe_tag)}/{urllib.parse.quote(safe_name)}")
    return download_firmware_url(url, f"{safe_tag}-{safe_name}")

def request_json(url, method="GET", payload=None, timeout=4, form=False,
                 allow_text=False):
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
                            raw = response.read()
                        try:
                            return json.loads(raw)
                        except json.JSONDecodeError:
                            if allow_text:
                                return {"message": raw.strip()}
                            raise
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
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            if allow_text:
                return {"message": raw.decode(errors="replace").strip()}
            raise

def normalize_host(host):
    value = host.strip()
    if not value:
        raise ValueError("The network address is empty.")
    parsed = urllib.parse.urlsplit(value if "://" in value else f"http://{value}")
    if not parsed.hostname:
        raise ValueError("The network address is invalid.")
    return parsed.hostname, parsed.port

def _absolute_camera_url(host, port, value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    return f"http://{host}:{port}/" + value.lstrip("/")

def printer_camera_info(host, port):
    """Return the enabled Moonraker webcam without mistaking Fluidd for video."""
    hostname, address_port = normalize_host(host)
    moonraker_port = address_port or port
    base = f"http://{hostname}:{moonraker_port}"
    response = request_json(base + "/server/webcams/list", timeout=3)
    webcams = response.get("result", {}).get("webcams", [])
    webcams = sorted(
        webcams,
        key=lambda webcam: (
            webcam.get("name") != "LayerShot Camera",
            ":8000" not in str(webcam.get("stream_url") or ""),
        ))
    for webcam in webcams:
        if not webcam.get("enabled", True):
            continue
        stream_url = _absolute_camera_url(
            hostname, moonraker_port, webcam.get("stream_url"))
        if not stream_url:
            continue
        parsed_stream = urllib.parse.urlsplit(stream_url)
        if (parsed_stream.port == 8000
                and not _creality_root_has_viewer(hostname)):
            stream_url = f"http://{hostname}:8000/?layershot_player=1"
        return {
            "configured": True,
            "name": webcam.get("name") or "Camera",
            "service": webcam.get("service") or "",
            "stream_url": stream_url,
            "snapshot_url": _absolute_camera_url(
                hostname, moonraker_port, webcam.get("snapshot_url")),
            "source": webcam.get("source") or "",
            "uid": webcam.get("uid") or "",
        }
    return {
        "configured": False,
        "name": "",
        "service": "",
        "stream_url": "",
        "snapshot_url": "",
        "source": "",
        "uid": "",
    }

def _creality_root_has_viewer(host):
    """Return whether Creality serves its own WebRTC viewer page."""
    url = f"http://{host}:8000/"
    if platform.system() == "Darwin":
        command = [
            "/usr/bin/curl", "--silent", "--show-error", "--fail",
            "--connect-timeout", "2", "--max-time", "3", url,
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=4)
        html = result.stdout if result.returncode == 0 else ""
    else:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                html = response.read(65536).decode("utf-8", errors="replace")
        except Exception:
            html = ""
    return (
        "RTCPeerConnection" in html
        and "/call/webrtc_local" in html)

def _creality_webrtc_available(host):
    """Detect Creality's local WebRTC server used by K2/SparkX cameras."""
    if _creality_root_has_viewer(host):
        return True
    if platform.system() == "Darwin":
        result = subprocess.run(
            [
                "/usr/bin/curl", "--silent", "--output", "/dev/null",
                "--write-out", "%{http_code}", "--connect-timeout", "2",
                "--max-time", "3",
                f"http://{host}:8000/call/webrtc_local",
            ],
            capture_output=True, text=True, timeout=4)
        return result.returncode == 0 and result.stdout.strip() == "200"
    else:
        try:
            with urllib.request.urlopen(
                    f"http://{host}:8000/call/webrtc_local",
                    timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

def configure_printer_camera(host, port):
    """Register Creality's existing WebRTC stream in Moonraker.

    This only writes a database webcam entry. It does not modify printer
    configuration files, install services, or restart Klipper.
    """
    hostname, address_port = normalize_host(host)
    moonraker_port = address_port or port
    if not _creality_webrtc_available(hostname):
        raise RuntimeError(
            "The Creality video service is not responding. Check that the "
            "camera is enabled in the printer settings and physically connected.")
    response = request_json(
        f"http://{hostname}:{moonraker_port}/server/webcams/list", timeout=3)
    webcams = response.get("result", {}).get("webcams", [])
    existing = next(
        (webcam for webcam in webcams
         if webcam.get("name") == "LayerShot Camera"
         and webcam.get("source") == "database"),
        None)
    payload = {
        "name": "LayerShot Camera",
        "location": "printer",
        "service": "iframe",
        "enabled": True,
        "stream_url": f"http://{hostname}:8000/",
        "snapshot_url": "",
        "target_fps": 15,
        "target_fps_idle": 5,
        "aspect_ratio": "16:9",
    }
    if existing and existing.get("uid"):
        payload["uid"] = existing["uid"]
    result = request_json(
        f"http://{hostname}:{moonraker_port}/server/webcams/item",
        method="POST", payload=payload, timeout=5)
    webcam = result.get("result", {}).get("webcam")
    if not isinstance(webcam, dict):
        raise RuntimeError("Moonraker did not confirm the camera configuration.")
    return printer_camera_info(hostname, moonraker_port)

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
            virtual_active = bool(virtual_sd.get("is_active"))
            file_position = virtual_sd.get("file_position") or 0
            file_size = virtual_sd.get("file_size") or 0
            if (stats.get("state") in (None, "", "standby")
                    and (virtual_active or (
                        file_size and 0 < file_position < file_size))):
                stats["state"] = "preparing"
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
    # Determine the active IPv4 address without relying on Unix-only commands.
    # A UDP connect selects a route but sends no packet.
    for target in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(target)
                addresses.add(probe.getsockname()[0])
        except OSError:
            pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            addresses.add(info[4][0])
    except OSError:
        pass
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
        elif platform.system() == "Windows":
            output = subprocess.check_output(
                ["ipconfig"], text=True, errors="ignore",
                stderr=subprocess.DEVNULL, timeout=4,
                **hidden_subprocess_kwargs())
            addresses.update(re.findall(
                r"(?:IPv4[^:]*|IP Address[^:]*):\s*([0-9]+(?:\.[0-9]+){3})",
                output, flags=re.IGNORECASE))
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

def local_network_configuration():
    """Return the active LAN address, gateway and netmask.

    LayerShot currently scans /24 home networks, which covers the Creality
    printers and consumer routers it supports.  The gateway is read from the
    host OS so a preferred ESP address also works on routers using .254.
    """
    networks = _local_ipv4_networks()
    if not networks:
        raise RuntimeError("No active private IPv4 network was detected.")
    network = networks[0]
    local_ip = None
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("1.1.1.1", 80))
            candidate = ipaddress.ip_address(probe.getsockname()[0])
            if candidate in network:
                local_ip = str(candidate)
    except OSError:
        pass
    gateway = None
    try:
        if platform.system() == "Darwin":
            output = subprocess.check_output(
                ["/sbin/route", "-n", "get", "default"],
                text=True, stderr=subprocess.DEVNULL, timeout=2)
            match = re.search(r"gateway:\s*([0-9]+(?:\.[0-9]+){3})", output)
        elif platform.system() == "Windows":
            output = subprocess.check_output(
                ["route", "print", "-4", "0.0.0.0"],
                text=True, errors="ignore", stderr=subprocess.DEVNULL,
                timeout=4, **hidden_subprocess_kwargs())
            match = re.search(
                r"^\s*0\.0\.0\.0\s+0\.0\.0\.0\s+"
                r"([0-9]+(?:\.[0-9]+){3})\s+"
                r"([0-9]+(?:\.[0-9]+){3})",
                output, flags=re.MULTILINE)
            if match and not local_ip:
                local_ip = match.group(2)
        else:
            output = subprocess.check_output(
                ["ip", "route", "show", "default"], text=True,
                stderr=subprocess.DEVNULL, timeout=2)
            match = re.search(r"\bvia\s+([0-9]+(?:\.[0-9]+){3})", output)
        if match:
            gateway = match.group(1)
    except Exception:
        pass
    if not gateway:
        raise RuntimeError("The local network gateway could not be detected.")
    return {
        "local_ip": local_ip or "",
        "network": str(network),
        "gateway": gateway,
        "netmask": str(network.netmask),
        "dns": gateway,
    }

def ipv4_address_is_available(address):
    """Return True when an address does not answer the local conflict probes."""
    ping = (["ping", "-n", "1", "-w", "250", address]
            if platform.system() == "Windows"
            else ["ping", "-c", "1", "-W", "250", address])
    try:
        if subprocess.run(
                ping, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=1, **hidden_subprocess_kwargs()).returncode == 0:
            return False
    except Exception:
        pass
    for port in (80, 443, 4408, 7125):
        try:
            with socket.create_connection((address, port), timeout=.12):
                return False
        except OSError:
            pass
    return True

def find_available_ipv4_addresses(limit=12):
    """Find LAN addresses that are unused at scan time.

    This is deliberately a conservative availability test (ICMP plus common
    LayerShot/printer ports). A router-side DHCP reservation remains the only
    way to guarantee that another client will never receive the address later.
    """
    configuration = local_network_configuration()
    network = ipaddress.ip_network(configuration["network"])
    excluded = {
        configuration["local_ip"], configuration["gateway"],
        str(network.network_address), str(network.broadcast_address),
    }
    preferred = list(range(200, 250)) + list(range(20, 200))
    candidates = [
        str(network.network_address + suffix)
        for suffix in preferred
        if suffix < network.num_addresses - 1
        and str(network.network_address + suffix) not in excluded
    ]

    available = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        for address, is_available in zip(
                candidates, executor.map(ipv4_address_is_available, candidates)):
            if is_available:
                available.append(address)
                if len(available) >= limit:
                    break
    return configuration, available

def _open_moonraker_port(host):
    for port in (4408, 7125, 80):
        try:
            if platform.system() == "Darwin":
                response = request_json(
                    f"http://{host}:{port}/server/info", timeout=.8)
                if isinstance(response.get("result"), dict):
                    return port
                continue
            with socket.create_connection((host, port), timeout=.18):
                return port
        except Exception:
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
    printer_info = {}
    try:
        printer_info = request_json(
            base + "/printer/info", timeout=1.2).get("result", {})
    except Exception:
        pass
    identity = " ".join([
        hostname, result.get("hostname", ""), result.get("software_version", ""),
        json.dumps(system, ensure_ascii=False),
        json.dumps(printer_info, ensure_ascii=False),
        json.dumps(result, ensure_ascii=False),
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
    name = hostname or result.get("hostname") or printer_info.get("hostname") or model
    generic_names = {
        "", "klipper", "moonraker", "fluidd", "mainsail", "localhost",
        "creality", "crealityos", "buildroot",
    }
    if str(name).strip().lower() in generic_names and model != "Other Moonraker / Klipper":
        name = model
    if not name or str(name).strip().lower() in generic_names:
        name = f"Klipper {host}"
    return {
        "name": name, "model": model, "host": host, "port": port,
        "version": result.get("moonraker_version", ""),
        "components": components,
    }

def discover_printers(seed_printers=()):
    seed_by_host = {}
    for seed in seed_printers:
        if isinstance(seed, dict):
            host = str(seed.get("host", "")).strip()
            if host:
                seed_by_host[host] = seed
        else:
            host = str(seed).strip()
            if host:
                seed_by_host[host] = {}
    hosts = list(seed_by_host)
    # Saved addresses and the ARP table are especially important on macOS:
    # unsigned/ad-hoc applications can be denied raw subnet sockets even though
    # the system-network fallback used by request_json remains available.
    hosts.extend(_arp_addresses())
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
                printer = future.result()
                saved = seed_by_host.get(printer["host"], {})
                if saved:
                    saved_model = saved.get("model")
                    detected_model = printer["model"]
                    if saved_model and detected_model == "Other Moonraker / Klipper":
                        printer["model"] = saved_model
                    saved_name = saved.get("name")
                    if (detected_model != "Other Moonraker / Klipper"
                            and saved_name in (saved_model, "Klipper", "K2 Plus", "K2")):
                        printer["name"] = detected_model
                    elif saved_name:
                        printer["name"] = saved["name"]
                printers.append(printer)
            except Exception:
                pass
    return sorted(printers, key=lambda printer: tuple(int(x) for x in printer["host"].split(".")))

_esp_address_cache = {}
_bonjour_esp_cache = (0.0, [])

def _bonjour_layershot_hosts():
    """Return LayerShot HTTP hosts advertised through Bonjour on macOS."""
    global _bonjour_esp_cache
    if platform.system() != "Darwin":
        return []
    cached_at, cached_hosts = _bonjour_esp_cache
    if cached_hosts and time.monotonic() - cached_at < 15:
        return list(cached_hosts)
    try:
        process = subprocess.run(
            ["/usr/bin/dns-sd", "-B", "_http._tcp", "local."],
            capture_output=True, timeout=1, **hidden_subprocess_kwargs())
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b""
    except Exception:
        return []
    else:
        output = process.stdout or b""
    if isinstance(output, bytes):
        output = output.decode(errors="replace")
    aliases = []
    for line in output.splitlines():
        match = re.search(
            r"_http\._tcp\.\s+(hackman-layershot[^\s]*)\s*$",
            line, re.IGNORECASE)
        if match:
            aliases.append(match.group(1).rstrip(".") + ".local")
    aliases = list(dict.fromkeys(aliases))
    hosts = []
    # `gethostbyname()` and curl do not always inherit multicast-DNS
    # resolution from an ad-hoc signed bundle. Ask Bonjour for the A record
    # explicitly and prefer its numeric address.
    for alias in aliases:
        try:
            process = subprocess.run(
                ["/usr/bin/dns-sd", "-G", "v4", alias],
                capture_output=True, timeout=1, **hidden_subprocess_kwargs())
        except subprocess.TimeoutExpired as error:
            address_output = error.stdout or b""
        except Exception:
            address_output = b""
        else:
            address_output = process.stdout or b""
        if isinstance(address_output, bytes):
            address_output = address_output.decode(errors="replace")
        addresses = re.findall(
            rf"{re.escape(alias)}\.?\s+(\d+(?:\.\d+){{3}})\s+",
            address_output, re.IGNORECASE)
        hosts.extend(addresses)
        hosts.append(alias)
    hosts = list(dict.fromkeys(hosts))
    _bonjour_esp_cache = (time.monotonic(), hosts)
    return hosts

def _arp_addresses():
    try:
        command = ["/usr/sbin/arp", "-a"] if platform.system() == "Darwin" else ["arp", "-a"]
        output = subprocess.check_output(
            command, text=True, stderr=subprocess.DEVNULL, timeout=2,
            **hidden_subprocess_kwargs())
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
    requested_identity = cache_key.rstrip(".")
    named_layershot = requested_identity.startswith(
        "hackman-layershot") and not re.fullmatch(
            r"\d+(?:\.\d+){3}", requested_identity)
    cached = _esp_address_cache.get(cache_key)
    candidates = [cached] if cached else []
    bonjour_hosts = _bonjour_layershot_hosts()
    if platform.system() == "Darwin":
        for alias in (hostname, "hackman-layershot.local",
                      *bonjour_hosts, "espressif.lan"):
            try:
                cache_output = subprocess.check_output(
                    ["/usr/bin/dscacheutil", "-q", "host", "-a", "name", alias],
                    text=True, stderr=subprocess.DEVNULL, timeout=3)
                candidates.extend(re.findall(
                    r"ip_address:\s*(\d+(?:\.\d+){3})", cache_output))
            except Exception:
                pass
    # The ad-hoc macOS network helper can reach local IP addresses but may not
    # inherit multicast-DNS resolution. Resolve .local in the main application
    # process first, then give the helper the resulting numeric address.
    for alias in (hostname, "hackman-layershot.local", *bonjour_hosts):
        try:
            resolved = socket.gethostbyname(alias)
            if resolved:
                candidates.append(resolved)
        except OSError:
            pass
    candidates.append(hostname)
    # DHCP can change the address remembered by the desktop app. Always fall
    # back to the LayerShot host aliases and the current ARP table, even when
    # the saved value was an old numeric address.
    candidates.extend([
        "hackman-layershot.local",
    ])
    candidates.extend(bonjour_hosts)
    candidates.extend(_arp_addresses())
    for candidate in dict.fromkeys(x for x in candidates if x):
        base = f"http://{candidate}" + (f":{port}" if port else "")
        try:
            status = request_json(base + "/status", timeout=1)
            if status.get("name") == "Hackman3D LayerShot":
                status_hostname = str(status.get("hostname", "")).lower().rstrip(".")
                if (named_layershot and status_hostname
                        and status_hostname != requested_identity):
                    continue
                _esp_address_cache[cache_key] = candidate
                return base, status
        except Exception:
            continue
    raise ConnectionError("Hackman3D LayerShot ESP32 was not found on the local network.")

def esp_post(host, endpoint, payload=None):
    base, _ = _esp_base(host)
    return request_json(
        f"{base}/{endpoint.lstrip('/')}",
        method="POST", payload=payload or {}, timeout=5, form=True,
        allow_text=True)

def esp_status(host):
    base, status = _esp_base(host)
    status["_resolved_address"] = urllib.parse.urlsplit(base).hostname
    return status

def discover_esps(seed_hosts=()):
    candidates = [str(host).strip() for host in seed_hosts if str(host).strip()]
    candidates.extend(_bonjour_layershot_hosts())
    candidates.extend(_arp_addresses())
    # macOS can deny raw subnet sockets to an ad-hoc signed app. Bonjour and
    # ARP provide a fast, reliable candidate list there. Windows/Linux keep
    # the subnet fallback for routers that suppress multicast discovery.
    if platform.system() != "Darwin":
        for network in _local_ipv4_networks():
            candidates.extend(str(host) for host in network.hosts())
    candidates = list(dict.fromkeys(candidates))

    def probe(host):
        if platform.system() != "Darwin":
            try:
                with socket.create_connection((host, 80), timeout=.18):
                    pass
            except OSError:
                return None
        try:
            status = request_json(f"http://{host}/status", timeout=1)
            if status.get("name") != "Hackman3D LayerShot":
                return None
            status["_resolved_address"] = status.get("ip") or host
            return status
        except Exception:
            return None

    found = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as executor:
        for status in executor.map(probe, candidates):
            if status:
                found.append(status)
    unique = {
        status["_resolved_address"]: status for status in found
    }
    return sorted(
        unique.values(),
        key=lambda status: tuple(
            int(part) for part in status["_resolved_address"].split(".")))

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
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profiles"], text=True,
            **hidden_subprocess_kwargs())
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
            ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
            text=True, **hidden_subprocess_kwargs())
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
