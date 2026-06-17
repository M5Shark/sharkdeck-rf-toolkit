#!/usr/bin/env python3
# ==========================================================
# Sharkdeck GPIO LED Tool
#
# Turn an LED on/off/blink on any GPIO pin, via Adafruit
# Blinka (board + digitalio). Plain numbered menu - type a
# number and press Enter.
#
# Wiring (active-high):
#     GPIO pin --> [220-330 ohm resistor] --> LED(+) anode
#     LED(-) cathode --> GND
#
# Free GPIO pins on the Sharkdeck header: PI5, PI6, PI11, PI12
# (PI7/PI8 are taken by the NRF24L01; RX0/TX0 are the UART.)
#
# Usage:
#     python3 led_tool.py            # uses default pin PI5
#     python3 led_tool.py PI6        # use a specific pin
# ==========================================================
import sys
import time

# ANSI colours (harmless if the terminal ignores them)
C = {
    "cyan": "\033[1;36m", "green": "\033[1;32m", "red": "\033[1;31m",
    "yellow": "\033[1;33m", "dim": "\033[2m", "reset": "\033[0m", "bold": "\033[1m",
}


def c(text, colour):
    return f"{C.get(colour, '')}{text}{C['reset']}"


# Free GPIO pins on the Sharkdeck header: PI5, PI6, PI11, PI12
# (PI7/PI8 are used by the NRF24L01; RX0/TX0 are the UART.)
DEFAULT_PIN = "PI5"


def get_pin_name():
    """Pin from argv[1], else prompt, else default."""
    if len(sys.argv) > 1:
        return sys.argv[1].strip().upper()
    entered = input(f"  GPIO pin name [{DEFAULT_PIN}]: ").strip().upper()
    return entered or DEFAULT_PIN


def setup_led(pin_name):
    """Return a configured digitalio output, or None on failure."""
    import board
    import digitalio

    if not hasattr(board, pin_name):
        avail = sorted(n for n in dir(board) if n[:1].isalpha() and n.isupper())
        print(c(f"  Pin '{pin_name}' not found on this board.", "red"))
        print(c("  Available pin names:", "dim"))
        print("   " + ", ".join(avail))
        return None

    led = digitalio.DigitalInOut(getattr(board, pin_name))
    led.direction = digitalio.Direction.OUTPUT
    led.value = False
    return led


def blink(led):
    raw = input("  blink count (blank = until Ctrl+C): ").strip()
    delay = input("  delay seconds [0.5]: ").strip()
    delay = float(delay) if delay.replace(".", "", 1).isdigit() else 0.5
    print(c("  Blinking...  Ctrl+C to stop.", "cyan"))
    try:
        if raw.isdigit():
            for _ in range(int(raw)):
                led.value = True
                time.sleep(delay)
                led.value = False
                time.sleep(delay)
        else:
            while True:
                led.value = not led.value
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        led.value = False
        print(c("\n  Blink stopped.", "yellow"))


def main():
    print(c("\n  ============================================", "cyan"))
    print(c("        SHARKDECK  -  GPIO LED TOOL", "cyan"))
    print(c("  ============================================", "cyan"))

    pin_name = get_pin_name()
    try:
        led = setup_led(pin_name)
    except Exception as e:  # noqa: BLE001
        print(c(f"  GPIO init failed: {e}", "red"))
        sys.exit(1)
    if led is None:
        sys.exit(1)

    print("  Controlling pin " + c(pin_name, "green") + " (starts OFF).\n")

    try:
        while True:
            state = c("ON", "green") if led.value else c("OFF", "dim")
            print(f"  LED is currently: {state}")
            print(c("  [1]", "green") + " Turn ON")
            print(c("  [2]", "red") + " Turn OFF")
            print(c("  [3]", "yellow") + " Blink")
            print(c("  [0]", "cyan") + " Quit")
            choice = input(c("\n  select > ", "bold")).strip()

            if choice == "1":
                led.value = True
                print(c("  LED ON", "green"))
            elif choice == "2":
                led.value = False
                print(c("  LED OFF", "dim"))
            elif choice == "3":
                blink(led)
            elif choice in ("0", "q", "Q"):
                break
            else:
                print(c("  unknown option.", "dim"))
            print()
    finally:
        led.value = False
        led.deinit()
        print(c("  LED off, GPIO released. Bye.\n", "cyan"))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n  Interrupted. Exiting.", "yellow"))
        sys.exit(0)
