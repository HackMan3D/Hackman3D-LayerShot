import json, os, platform, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

def asset_path(name):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return root / "assets" / name

def request_json(url, method="GET", payload=None, timeout=4):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}

def printer_status(host, port):
    base = f"http://{host}:{port}"
    info = request_json(base + "/printer/objects/query?print_stats&display_status")
    result = info.get("result", {}).get("status", {})
    return result.get("print_stats", {}), result.get("display_status", {})

def esp_post(host, endpoint, payload=None):
    data = urllib.parse.urlencode(payload or {}).encode()
    req = urllib.request.Request(
        f"http://{host.removeprefix('http://').rstrip('/')}/{endpoint.lstrip('/')}",
        data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=5) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}

def serial_ports():
    try:
        from serial.tools import list_ports
        return [p.device for p in list_ports.comports()]
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
            return subprocess.check_output(
                ["/usr/bin/security", "find-generic-password", "-D",
                 "AirPort network password", "-a", ssid, "-w"], text=True).strip()
        out = subprocess.check_output(
            ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"], text=True)
        for line in out.splitlines():
            if "Key Content" in line:
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""
