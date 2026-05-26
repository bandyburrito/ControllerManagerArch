"""Controller detection, identification, and udev monitoring."""

import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

import evdev
import pyudev

KNOWN_CONTROLLERS = {
    (0x054C, 0x05C4): ("DualShock 4 (v1)", "playstation"),
    (0x054C, 0x09CC): ("DualShock 4 (v2)", "playstation"),
    (0x054C, 0x0CE6): ("DualSense", "playstation"),
    (0x054C, 0x0DF2): ("DualSense Edge", "playstation"),
    (0x045E, 0x028E): ("Xbox 360 Controller", "xbox"),
    (0x045E, 0x028F): ("Xbox 360 Wireless", "xbox"),
    (0x045E, 0x02D1): ("Xbox One Controller", "xbox"),
    (0x045E, 0x02DD): ("Xbox One Controller (2015)", "xbox"),
    (0x045E, 0x02E0): ("Xbox One S (Bluetooth)", "xbox"),
    (0x045E, 0x02EA): ("Xbox One S Controller", "xbox"),
    (0x045E, 0x02FD): ("Xbox One S (Bluetooth v2)", "xbox"),
    (0x045E, 0x0B00): ("Xbox Elite Series 2", "xbox"),
    (0x045E, 0x0B12): ("Xbox Series X|S", "xbox"),
    (0x045E, 0x0B13): ("Xbox Series X|S (Bluetooth)", "xbox"),
    (0x046D, 0xC21D): ("Logitech F310", "generic"),
    (0x046D, 0xC21E): ("Logitech F510", "generic"),
    (0x046D, 0xC21F): ("Logitech F710", "generic"),
    (0x046D, 0xC216): ("Logitech Dual Action", "generic"),
    (0x28DE, 0x1142): ("Steam Controller", "steam"),
    (0x28DE, 0x1205): ("Steam Deck Controller", "steam"),
    (0x057E, 0x2009): ("Switch Pro Controller", "nintendo"),
    (0x057E, 0x2006): ("Joy-Con (L)", "nintendo"),
    (0x057E, 0x2007): ("Joy-Con (R)", "nintendo"),
    (0x057E, 0x2017): ("Switch Online SNES Controller", "nintendo"),
    (0x2DC8, 0x2002): ("8BitDo SN30 Pro+", "generic"),
    (0x2DC8, 0x6100): ("8BitDo Ultimate", "generic"),
    (0x0079, 0x0006): ("DragonRise Generic Gamepad", "generic"),
    (0x0810, 0x0001): ("Personal Comm Systems Gamepad", "generic"),
    (0x0E6F, 0x0213): ("Afterglow Gamepad", "generic"),
    (0x1532, 0x0A00): ("Razer Raiju", "generic"),
    (0x1532, 0x1007): ("Razer Raiju Tournament", "generic"),
    (0x1532, 0x1009): ("Razer Raiju Ultimate", "generic"),
    (0x0F0D, 0x00C1): ("HORI Pad", "generic"),
    (0x0F0D, 0x0092): ("HORI Pokken Controller", "generic"),
    (0x0738, 0x4716): ("Mad Catz", "generic"),
}

BUS_NAMES = {
    0x03: "USB",
    0x05: "Bluetooth",
    0x06: "Virtual",
    0x19: "I2C",
}

BRAND_COLORS = {
    "playstation": "#003087",
    "xbox": "#107C10",
    "nintendo": "#E60012",
    "steam": "#1B2838",
    "generic": "#6C63FF",
}

BRAND_ICONS = {
    "playstation": "PS",
    "xbox": "XB",
    "nintendo": "NS",
    "steam": "ST",
    "generic": "GP",
}


@dataclass
class Controller:
    name: str
    friendly_name: str
    brand: str  # playstation, xbox, nintendo, steam, generic
    path: str
    vendor: int
    product: int
    bus: int
    connection: str
    phys: str = ""
    uniq: str = ""
    battery_percent: int | None = None
    battery_status: str | None = None
    evdev_caps: dict = field(default_factory=dict)
    has_evdev: bool = False


def _battery_for_device(sysfs_path: str) -> tuple[int | None, str | None]:
    """Walk sysfs to find a battery associated with this input device."""
    ps_root = Path("/sys/class/power_supply")
    if not ps_root.exists():
        return None, None

    for ps in ps_root.iterdir():
        try:
            if (ps / "type").read_text().strip() != "Battery":
                continue
            scope = (ps / "scope").read_text().strip() if (ps / "scope").exists() else ""
            if scope != "Device":
                continue
            cap_file = ps / "capacity"
            if not cap_file.exists():
                continue
            resolved = str(ps.resolve())
            if sysfs_path and any(part in resolved for part in sysfs_path.split("/")[-4:-1]):
                pct = int(cap_file.read_text().strip())
                status = (ps / "status").read_text().strip() if (ps / "status").exists() else None
                return pct, status
        except (OSError, ValueError):
            continue
    return None, None


def _is_gamepad_proc(info: dict) -> bool:
    """Heuristic: does this /proc entry look like a gamepad?"""
    ev = info.get("ev", 0)
    key = info.get("key", 0)
    has_abs = ev & (1 << 0x03)
    has_key = ev & (1 << 0x01)
    if not (has_abs and has_key):
        return False
    gamepad_range = sum(1 << i for i in range(0x130, 0x140))
    joystick_range = sum(1 << i for i in range(0x120, 0x130))
    return bool(key & (gamepad_range | joystick_range))


def _parse_proc_devices() -> list[dict]:
    """Parse /proc/bus/input/devices."""
    try:
        text = Path("/proc/bus/input/devices").read_text()
    except OSError:
        return []

    devices, cur = [], {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if cur:
                devices.append(cur)
            cur = {}
            continue
        prefix = line[0]
        rest = line[2:].strip() if len(line) > 2 else ""
        if prefix == "I":
            for m in re.finditer(r"(\w+)=([0-9a-fA-F]+)", rest):
                cur[m.group(1).lower()] = int(m.group(2), 16)
        elif prefix == "N":
            m = re.match(r'Name="(.+)"', rest)
            if m:
                cur["name"] = m.group(1)
        elif prefix == "P":
            cur["phys"] = rest.replace("Phys=", "")
        elif prefix == "S":
            cur["sysfs"] = rest.replace("Sysfs=", "")
        elif prefix == "U":
            cur["uniq"] = rest.replace("Uniq=", "")
        elif prefix == "H":
            handlers = rest.replace("Handlers=", "").split()
            cur["handlers"] = handlers
            for h in handlers:
                if h.startswith("event"):
                    cur["event"] = f"/dev/input/{h}"
        elif prefix == "B":
            m = re.match(r"(\w+)=(.+)", rest)
            if m:
                parts = m.group(2).strip().split()
                bitmap = 0
                for i, p in enumerate(reversed(parts)):
                    bitmap |= int(p, 16) << (i * 64)
                cur[m.group(1).lower()] = bitmap
    if cur:
        devices.append(cur)
    return devices


def _identify(vid: int, pid: int, raw_name: str) -> tuple[str, str]:
    """Return (friendly_name, brand) for a controller."""
    known = KNOWN_CONTROLLERS.get((vid, pid))
    if known:
        return known
    lower = raw_name.lower()
    if "sony" in lower or "dualshock" in lower or "dualsense" in lower or "playstation" in lower:
        return raw_name, "playstation"
    if "xbox" in lower or "microsoft" in lower or "x-box" in lower:
        return raw_name, "xbox"
    if "nintendo" in lower or "switch" in lower or "joy-con" in lower or "pro controller" in lower:
        return raw_name, "nintendo"
    if "steam" in lower or "valve" in lower:
        return raw_name, "steam"
    return raw_name, "generic"


def detect_controllers() -> list[Controller]:
    """Return all connected game controllers."""
    found: list[Controller] = []
    seen: set[str] = set()

    # evdev pass — gives full capabilities if user has permissions
    try:
        for path in evdev.list_devices():
            try:
                dev = evdev.InputDevice(path)
                caps = dev.capabilities(verbose=False)
                abs_caps = caps.get(evdev.ecodes.EV_ABS, [])
                key_caps = caps.get(evdev.ecodes.EV_KEY, [])
                if not abs_caps or not key_caps:
                    continue
                key_set = set(key_caps)
                gp = set(range(0x130, 0x140))
                js = set(range(0x120, 0x130))
                if not (key_set & gp or key_set & js):
                    continue

                vid, pid, bus = dev.info.vendor, dev.info.product, dev.info.bustype
                friendly, brand = _identify(vid, pid, dev.name)
                conn = BUS_NAMES.get(bus, f"Bus 0x{bus:04x}")

                sysfs = ""
                try:
                    sysfs = str(Path(f"/sys/class/input/{Path(path).name}/device").resolve())
                except OSError:
                    pass
                batt_pct, batt_st = _battery_for_device(sysfs)

                found.append(Controller(
                    name=dev.name,
                    friendly_name=friendly,
                    brand=brand,
                    path=path,
                    vendor=vid,
                    product=pid,
                    bus=bus,
                    connection=conn,
                    phys=dev.phys or "",
                    uniq=dev.uniq or "",
                    battery_percent=batt_pct,
                    battery_status=batt_st,
                    evdev_caps=caps,
                    has_evdev=True,
                ))
                seen.add(path)
            except (PermissionError, OSError):
                continue
    except Exception:
        pass

    # /proc fallback for devices we couldn't open via evdev
    for info in _parse_proc_devices():
        ev_path = info.get("event", "")
        if ev_path in seen or not ev_path:
            continue
        if not _is_gamepad_proc(info):
            continue

        vid = info.get("vendor", 0)
        pid = info.get("product", 0)
        bus = info.get("bus", 0)
        raw_name = info.get("name", "Unknown Controller")
        friendly, brand = _identify(vid, pid, raw_name)
        conn = BUS_NAMES.get(bus, f"Bus 0x{bus:04x}")

        found.append(Controller(
            name=raw_name,
            friendly_name=friendly,
            brand=brand,
            path=ev_path,
            vendor=vid,
            product=pid,
            bus=bus,
            connection=conn,
            phys=info.get("phys", ""),
            uniq=info.get("uniq", ""),
            has_evdev=False,
        ))

    return found


class DeviceMonitor:
    """Watches udev for input device hotplug events."""

    def __init__(self, callback):
        self._cb = callback
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        ctx = pyudev.Context()
        mon = pyudev.Monitor.from_netlink(ctx)
        mon.filter_by(subsystem="input")
        mon.start()
        for dev in iter(mon.poll, None):
            if not self._running:
                break
            if dev.action in ("add", "remove"):
                self._cb()
