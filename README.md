# 🦈 Sharkdeck RF Toolkit

A keyboard-driven, cyberpunk-styled Terminal UI (built with [Textual](https://textual.textualize.io/)) for controlling an **NRF24L01** 2.4 GHz transceiver on a Sharkdeck-class cyberdeck. Optimized for a 3.5-inch 480×320 display.

The interface provides three modules:

- **📡 Transmit** — send UTF-8 payload bursts on a chosen pipe/address.
- **👁️ Receive / Sniffer** — listen on a channel and decode incoming packets.
- **⚠️ Congestion Testbench** — a high-rate packet flood used for RF spectral/congestion testing.

---

## ⚖️ Legal Notice & Responsible Use — READ FIRST

> **This software can transmit radio energy and includes a packet-flood ("jammer") mode.**

**Operating a radio jammer is illegal in most jurisdictions**, including the United States (FCC prohibits the operation, marketing, or sale of jamming devices — 47 U.S.C. § 333), the European Union, the United Kingdom, Canada, Australia, and most other countries. Penalties can include large fines, equipment seizure, and criminal charges. The 2.4 GHz band is also shared with Wi-Fi, Bluetooth, medical, and safety-critical devices — interfering with it can cause real harm.

By using this software you agree that you will:

- Use it **only** on hardware and frequencies you own or are **explicitly authorized** to operate.
- Use the transmit and congestion-test modes **only** inside a properly shielded RF test environment (e.g. an anechoic chamber or Faraday enclosure), or under a license/authorization that permits it.
- **Never** use it to interfere with, disrupt, or deny service to any device or network you do not own or have written permission to test.
- Comply with all applicable local, national, and international radio regulations.

This project is published **for educational and authorized security-research purposes only**. The author(s) and contributors accept **no liability** for misuse or for any damage resulting from its use. **You are solely responsible for ensuring your use is legal.**

---

## ⚡ Quick install (WalnutPi / Allwinner H616, Debian bookworm)

On boards that aren't officially supported by Adafruit (e.g. the WalnutPi H616),
Blinka needs the **libgpiod v1.6 Python bindings**, which aren't in the apt repos
and must be compiled. The bundled installer does this for you — including the
Debian `site-packages` → `dist-packages` path fix — and installs the Python deps:

```bash
cd ~/sharkdeck-rf-toolkit
git pull
bash install.sh
```

When it finishes it prints `gpiod OK` and `board OK`. Then run `python3 sharkdeck_app.py`.
If you're on a fully supported board, the manual steps below also work.

## 🔧 Prerequisites

Install the Textual UI library and the hardware drivers on your Sharkdeck:

```bash
sudo apt-get update && sudo apt-get install -y python3-pip python3-gpiod
pip3 install -r requirements.txt
```

This script targets a board exposing `board`/`digitalio` via [Adafruit Blinka](https://github.com/adafruit/Adafruit_Blinka) and uses [`circuitpython-nrf24l01`](https://github.com/nRF24/CircuitPython_nRF24L01). If the radio hardware is not detected (e.g. when running on a regular PC), the app falls back to an **OFFLINE** state so the UI can still be previewed without crashing.

### Pinout (from the Sharkdeck PCB)

| Signal | Board Pin |
| ------ | --------- |
| CE     | `PI8`     |
| CSN    | `PI7`     |
| SPI    | Hardware `board.SPI()` |

Adjust these in `sharkdeck_app.py` if your wiring differs.

---

## 🖥️ Two interfaces

This repo ships **two** front-ends over the same NRF24L01 logic — pick whichever your console handles best:

| Script | Interface | When to use |
| --- | --- | --- |
| `sharkdeck_app.py` | Full-screen Textual TUI (cyberpunk UI, keyboard nav) | Modern terminal that captures key events |
| `sharkdeck_cli.py` | Plain numbered menu (type a number + Enter) | Minimal/framebuffer consoles where the TUI can't grab the keyboard. **No `textual` needed.** |

Run the CLI version:

```bash
python3 sharkdeck_cli.py
```

You'll get a menu — type `1` Transmit, `2` Receive, `3` Jammer, `4` Channel, `0` Quit, then Enter. Press `Ctrl+C` to stop receiving/flooding and return to the menu.

## 🚀 Run (TUI)

```bash
python3 sharkdeck_app.py
```

### Keyboard controls

| Key       | Action |
| --------- | ------ |
| `T`       | Transmitter view |
| `R`       | Receiver / sniffer view (auto-starts the listener) |
| `J`       | Congestion testbench view |
| `Tab` / arrows | Move focus between buttons and inputs |
| `Q`       | Disarm the radio and exit safely |

---

## 📝 Notes / Known limitations

- The receiver listener is started from the navigation logic; the `btn-rx-start` handler is referenced but there is no matching button — start receiving by switching to the **Receive** view.
- `pa_level = 0` selects **maximum** PA output. Lower it (e.g. `radio.pa_level = -18`) for bench testing.
- Tested against the Textual 0.x widget API. Pin a known-good Textual version in `requirements.txt` if widget APIs change upstream.

## 📄 License

Released under the [MIT License](LICENSE).
