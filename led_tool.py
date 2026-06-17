#!/usr/bin/env python3
# ==========================================================
# Sharkdeck GPIO LED Tool  (direct libgpiod edition)
#
# Turn an LED on/off/blink on any GPIO pin by talking to
# libgpiod directly - no Adafruit Blinka pin map (which
# mis-maps the Allwinner H616 and throws Errno 22).
#
# Pin addressing on this board (from `gpiodetect`):
#   gpiochip0 = banks A-I (288 lines)   offset = bank*32 + pin
#   gpiochip1 = bank L     (32 lines)   offset = pin
#   bank index: A=0 B=1 C=2 D=3 E=4 F=5 G=6 H=7 I=8
#   so PI11 = chip0 line 267, PI12 = 268
#
# Free pins on THIS board: PI11 (pin 10), PI12 (pin 12).
# Lines 261-266 (PI5..PI10) are claimed by the kernel/overlay,
# and PI7/PI8 drive the NRF24L01 - so they can't toggle an LED.
#
# Usage:
#   python3 led_tool.py            # default pin PI11
#   python3 led_tool.py PI12       # by pin name
#   python3 led_tool.py 267        # by raw gpiochip0 offset
#   python3 led_tool.py gpiochip0:267
# ==========================================================
import sys
import time

import gpiod

C = {
    "cyan": "\033[1;36m", "green": "\033[1;32m", "red": "\033[1;31m",
    "yellow": "\033[1;33m", "dim": "\033[2m", "reset": "\033[0m", "bold": "\033[1m",
}


def c(text, colour):
    return f"{C.get(colour, '')}{text}{C['reset']}"


DEFAULT_PIN = "PI11"


def parse_pin(name):
    """Map 'PI5' / '261' / 'gpiochip0:261' -> (chip_name, offset)."""
    name = name.strip().upper()
    if ":" in name:
        chip, off = name.split(":", 1)
        return chip.lower(), int(off)
    if name.isdigit():
        return "gpiochip0", int(name)
    if name.startswith("P") and len(name) >= 3:
        bank, num = name[1], name[2:]
        if not num.isdigit():
            return None
        num = int(num)
        if bank == "L":
            return "gpiochip1", num
        if "A" <= bank <= "I":
            return "gpiochip0", (ord(bank) - ord("A")) * 32 + num
    return None


def open_chip(chip_name):
    for arg in (chip_name, "/dev/" + chip_name):
        try:
            return gpiod.Chip(arg)
        except Exception:  # noqa: BLE001
            continue
    digits = "".join(ch for ch in chip_name if ch.isdigit()) or "0"
    return gpiod.Chip(digits, gpiod.Chip.OPEN_BY_NUMBER)


def get_pin_name():
    if len(sys.argv) > 1:
        return sys.argv[1]
    entered = input(f"  GPIO pin name [{DEFAULT_PIN}]: ").strip()
    return entered or DEFAULT_PIN


def blink(line):
    raw = input("  blink count (blank = until Ctrl+C): ").strip()
    delay = input("  delay seconds [0.5]: ").strip()
    delay = float(delay) if delay.replace(".", "", 1).isdigit() else 0.5
    print(c("  Blinking...  Ctrl+C to stop.", "cyan"))
    val = 0
    try:
        if raw.isdigit():
            for _ in range(int(raw)):
                line.set_value(1); time.sleep(delay)
                line.set_value(0); time.sleep(delay)
        else:
            while True:
                val ^= 1
                line.set_value(val)
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        line.set_value(0)
        print(c("\n  Blink stopped.", "yellow"))


def main():
    print(c("\n  ============================================", "cyan"))
    print(c("        SHARKDECK  -  GPIO LED TOOL", "cyan"))
    print(c("  ============================================", "cyan"))

    pin_name = get_pin_name()
    parsed = parse_pin(pin_name)
    if parsed is None:
        print(c(f"  Could not parse pin '{pin_name}'.", "red"))
        print(c("  Try a name like PI5 / PI6 / PI11 / PI12, or a number.", "dim"))
        sys.exit(1)

    chip_name, offset = parsed
    try:
        chip = open_chip(chip_name)
        line = chip.get_line(offset)
        line.request(consumer="sharkdeck-led",
                     type=gpiod.LINE_REQ_DIR_OUT, default_vals=[0])
    except Exception as e:  # noqa: BLE001
        print(c(f"  GPIO init failed on {chip_name} line {offset}: {e}", "red"))
        print(c("  Check the pin is free (not used by the radio) and the", "dim"))
        print(c("  offset is valid for this chip.", "dim"))
        sys.exit(1)

    print("  Controlling " + c(pin_name.upper(), "green") +
          f"  ({chip_name} line {offset}), starts OFF.\n")

    try:
        while True:
            state = c("ON", "green") if line.get_value() else c("OFF", "dim")
            print(f"  LED is currently: {state}")
            print(c("  [1]", "green") + " Turn ON")
            print(c("  [2]", "red") + " Turn OFF")
            print(c("  [3]", "yellow") + " Blink")
            print(c("  [0]", "cyan") + " Quit")
            choice = input(c("\n  select > ", "bold")).strip()

            if choice == "1":
                line.set_value(1)
                print(c("  LED ON", "green"))
            elif choice == "2":
                line.set_value(0)
                print(c("  LED OFF", "dim"))
            elif choice == "3":
                blink(line)
            elif choice in ("0", "q", "Q"):
                break
            else:
                print(c("  unknown option.", "dim"))
            print()
    finally:
        line.set_value(0)
        line.release()
        print(c("  LED off, GPIO released. Bye.\n", "cyan"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n  Interrupted. Exiting.", "yellow"))
        sys.exit(0)
