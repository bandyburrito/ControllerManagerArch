# Controller Manager

A GUI tool for Linux that shows connected game controllers and lets you test their inputs in real time — like the **Game Controllers** panel on Windows or **DS4Windows**, but for Linux.

Built with PyQt6, `evdev`, and `pyudev`. Tested on Arch Linux + KDE Plasma.

## Features

- Auto-detects connected gamepads (USB and Bluetooth)
- Recognizes 35+ controller models out of the box — DualShock 4, DualSense, Xbox 360/One/Series, Switch Pro, Joy-Cons, Steam Controller, Steam Deck, Logitech F-series, 8BitDo, and more
- Live hotplug — plug or unplug a controller and the list updates automatically
- **Input test dialog** with live visualization:
  - Analog stick positions
  - Trigger bars (LT / RT)
  - D-pad direction
  - All buttons light up when pressed
- Battery level for controllers that expose it via sysfs
- Dark theme with brand-colored cards

## Requirements

- Linux (uses `/dev/input`, evdev, udev)
- Python 3.10+
- A user account in the `input` group for live input testing (detection works without it)

## Installation

### From AUR (Arch Linux)

```sh
yay -S controller-manager
# or
paru -S controller-manager
```

### Manual install (any distro)

```sh
git clone https://github.com/bandyburrito/ControllerManagerArch.git
cd ControllerManagerArch
pip install --user -r requirements.txt
python main.py
```

### Permissions setup

For live input testing, your user must be in the `input` group:

```sh
sudo usermod -aG input $USER
```

Log out and back in for the change to take effect. You can verify with:

```sh
groups | grep input
```

Without `input` group access, controller detection still works (via `/proc/bus/input/devices`), but the input test dialog will refuse to open the device.

## Usage

Launch the app:

```sh
python main.py
```

- Connected controllers appear as cards in the main window
- Click **Test Input** on a card to open the live input tester
- Press buttons and move sticks — they light up in the dialog
- The list refreshes automatically when controllers are plugged in or removed

## Project layout

```
ControllerManagerArch/
├── main.py        # entry point
├── backend.py     # device detection, udev monitor
├── widgets.py     # custom Qt widgets (cards, sticks, triggers, etc.)
├── tester.py      # live input test dialog
└── window.py      # main window
```

## Adding new controllers

If your controller isn't recognized by friendly name, it'll still show up as a generic gamepad. To add it properly:

1. Plug in the controller
2. Find its vendor and product ID:
   ```sh
   cat /proc/bus/input/devices | grep -A1 "YourControllerName"
   ```
3. Add an entry to `KNOWN_CONTROLLERS` in [backend.py](backend.py):
   ```python
   (0xVVVV, 0xPPPP): ("Friendly Name", "brand"),
   ```
   Brand can be `playstation`, `xbox`, `nintendo`, `steam`, or `generic`.

PRs welcome at [github.com/bandyburrito/ControllerManagerArch](https://github.com/bandyburrito/ControllerManagerArch).

## Troubleshooting

**"Cannot open /dev/input/eventN: Permission denied"**
Add yourself to the `input` group — see *Permissions setup* above.

**Controller shows as "Unknown Controller"**
Your model isn't in the database yet. See *Adding new controllers* above, or [open an issue](https://github.com/bandyburrito/ControllerManagerArch/issues) with the VID/PID and a `cat /proc/bus/input/devices` excerpt.

**Bluetooth controller not appearing**
Make sure it's actually paired and connected — `bluetoothctl info <MAC>` should show `Connected: yes`. Some controllers (notably Switch Pro) need extra kernel modules or `hid-nintendo` to expose proper button mappings.

## License

MIT — see [LICENSE](LICENSE).
