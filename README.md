# Controller Manager

A GUI tool for Linux that shows connected game controllers and lets you test their inputs in real time — like the **Game Controllers** panel on Windows or **DS4Windows**, but for Linux.

## What it does

- Auto-detects connected gamepads (USB and Bluetooth)
- Recognizes 35+ controller models out of the box — DualShock 4, DualSense, Xbox 360/One/Series, Switch Pro, Joy-Cons, Steam Controller, Steam Deck, Logitech F-series, 8BitDo, and more
- Live hotplug — plug or unplug a controller and the list updates automatically
- **Input test dialog** with live visualization of stick positions, triggers, D-pad, and every button
- Battery level for controllers that expose it via sysfs
- Dark theme with brand-colored cards

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

For live input testing your user must be in the `input` group:

```sh
sudo usermod -aG input $USER
```

Log out and back in afterwards. Detection works without this; only the live input tester needs it.

## How it was built

Python 3.10+ with [PyQt6](https://pypi.org/project/PyQt6/) for the GUI, [`python-evdev`](https://pypi.org/project/evdev/) for reading `/dev/input/event*` devices, and [`pyudev`](https://pypi.org/project/pyudev/) for hotplug events. Tested on Arch Linux + KDE Plasma.

```
ControllerManagerArch/
├── main.py        # entry point
├── backend.py     # device detection, udev monitor
├── widgets.py     # custom Qt widgets (cards, sticks, triggers, etc.)
├── tester.py      # live input test dialog
└── window.py      # main window
```

## License

MIT — see [LICENSE](LICENSE).
