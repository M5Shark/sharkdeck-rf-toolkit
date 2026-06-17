#!/usr/bin/env python3
# ==========================================================
# Sharkdeck RF Toolkit - plain terminal (CLI) edition
#
# A simple numbered-menu interface for the NRF24L01. No TUI,
# no keyboard navigation: just type a number and press Enter.
# Built for consoles where a full-screen TUI can't capture keys.
#
#   python3 sharkdeck_cli.py
# ==========================================================
import time
import sys

# ----------------------------------------------------------
# Hardware init (Sharkdeck pinout). Falls back to OFFLINE so
# the menu still runs on a PC or before the radio is wired.
# ----------------------------------------------------------
try:
    import board
    import digitalio
    from circuitpython_nrf24l01.rf24 import RF24

    CE_PIN = digitalio.DigitalInOut(board.PI8)   # CE
    CSN_PIN = digitalio.DigitalInOut(board.PI7)  # CSN
    spi = board.SPI()

    radio = RF24(spi, CSN_PIN, CE_PIN)
    radio.address_width = 5
    radio.channel = 76
    radio.data_rate = 1   # 1 Mbps
    radio.pa_level = 0    # Max power (0 dBm)
    RADIO_OK = True
    RADIO_ERR = ""
except Exception as e:  # noqa: BLE001
    RADIO_OK = False
    RADIO_ERR = str(e)
    radio = None

ADDRESSES = [b"1Node", b"2Node"]

# ANSI colours (safe on most terminals; ignore if unsupported)
C = {
    "cyan": "\033[1;36m", "green": "\033[1;32m", "red": "\033[1;31m",
    "yellow": "\033[1;33m", "blue": "\033[1;34m", "dim": "\033[2m",
    "reset": "\033[0m", "bold": "\033[1m",
}


def c(text, colour):
    return f"{C.get(colour, '')}{text}{C['reset']}"


def banner():
    print(c("\n  ============================================", "cyan"))
    print(c("        SHARKDECK RF TOOLKIT  -  CLI", "cyan"))
    print(c("        NRF24L01 Controller (v2.0)", "dim"))
    print(c("  ============================================", "cyan"))
    if RADIO_OK:
        print("   HW: " + c("ONLINE", "green") +
              f"   ch={radio.channel}  ({2400 + radio.channel} MHz)")
    else:
        print("   HW: " + c("OFFLINE", "red") + "  " + c(RADIO_ERR, "dim"))
    print()


def menu():
    print(c("  [1]", "green") + " Transmit payload")
    print(c("  [2]", "green") + " Receive / sniff")
    print(c("  [3]", "yellow") + " Congestion test (JAMMER)")
    print(c("  [4]", "blue") + " Show / change channel")
    print(c("  [0]", "red") + " Quit")
    return input(c("\n  select > ", "bold")).strip()


# ----------------------------------------------------------
# 1. Transmit
# ----------------------------------------------------------
def do_transmit():
    if not RADIO_OK:
        print(c("  Cannot transmit - radio OFFLINE.", "red"))
        return
    msg = input("  message to send [Sharkdeck Data Ping]: ").strip() \
        or "Sharkdeck Data Ping"
    radio.open_tx_pipe(ADDRESSES[0])
    radio.listen = False
    print(c(f"  Sending 5 packets: '{msg}'", "cyan"))
    for i in range(5):
        out = f"{msg} #{i + 1}"
        ok = radio.send(out.encode("utf-8"))
        tag = c("ACK ", "green") if ok else c("FAIL", "red")
        print(f"   [{tag}] {out}")
        time.sleep(0.5)
    print(c("  Done.", "green"))


# ----------------------------------------------------------
# 2. Receive
# ----------------------------------------------------------
def do_receive():
    if not RADIO_OK:
        print(c("  Cannot receive - radio OFFLINE.", "red"))
        return
    radio.open_rx_pipe(1, ADDRESSES[0])
    radio.listen = True
    print(c("  Listening...  press Ctrl+C to stop.", "cyan"))
    try:
        while True:
            if radio.any():
                raw = radio.read()
                try:
                    text = raw.decode("utf-8").strip("\x00")
                    print("   " + c("RX", "green") + f": {text}")
                except Exception:  # noqa: BLE001
                    print("   " + c("RX", "green") + f" raw: {raw.hex()}")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print(c("\n  Stopped listening.", "yellow"))
    finally:
        radio.listen = False


# ----------------------------------------------------------
# 3. Jammer / congestion test
# ----------------------------------------------------------
def do_jammer():
    if not RADIO_OK:
        print(c("  Cannot run - radio OFFLINE.", "red"))
        return
    print(c("\n  !! LEGAL WARNING !!", "red"))
    print(c("  Operating an RF jammer is ILLEGAL in most countries.", "yellow"))
    print(c("  Use only on hardware you own, inside a shielded/Faraday", "yellow"))
    print(c("  test environment. You are responsible for compliance.", "yellow"))
    if input("  type YES to continue: ").strip() != "YES":
        print(c("  Aborted.", "dim"))
        return

    ch = input(f"  target channel 0-125 [{radio.channel}]: ").strip()
    if ch.isdigit():
        radio.channel = max(0, min(int(ch), 125))

    radio.open_tx_pipe(ADDRESSES[0])
    radio.auto_ack = False
    radio.listen = False
    payload = b"\xFF" * 32
    sent = 0
    t0 = time.time()
    print(c(f"  FLOODING ch {radio.channel} ({2400 + radio.channel} MHz)."
            "  Ctrl+C to stop.", "red"))
    try:
        while True:
            radio.send(payload, ask_no_ack=True)
            sent += 1
            if sent % 1500 == 0:
                pps = int(sent / (time.time() - t0))
                print(f"   packets={sent:,}   rate=~{pps:,}/s", end="\r")
    except KeyboardInterrupt:
        print(c(f"\n  Stopped. Total packets sent: {sent:,}", "yellow"))
    finally:
        radio.auto_ack = True


# ----------------------------------------------------------
# 4. Channel
# ----------------------------------------------------------
def do_channel():
    if not RADIO_OK:
        print(c("  Radio OFFLINE - cannot change channel.", "red"))
        return
    print(f"  current channel: {radio.channel}  ({2400 + radio.channel} MHz)")
    ch = input("  new channel 0-125 (blank to keep): ").strip()
    if ch.isdigit():
        radio.channel = max(0, min(int(ch), 125))
        print(c(f"  channel set to {radio.channel}", "green"))


# ----------------------------------------------------------
# Main loop
# ----------------------------------------------------------
def main():
    banner()
    while True:
        choice = menu()
        if choice == "1":
            do_transmit()
        elif choice == "2":
            do_receive()
        elif choice == "3":
            do_jammer()
        elif choice == "4":
            do_channel()
        elif choice in ("0", "q", "Q"):
            break
        else:
            print(c("  unknown option.", "dim"))
        print()
    if RADIO_OK:
        try:
            radio.power = False
        except Exception:  # noqa: BLE001
            pass
    print(c("  Radio powered down. Bye.\n", "cyan"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n  Interrupted. Exiting.", "yellow"))
        sys.exit(0)
