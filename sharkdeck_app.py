import time
import asyncio
import board
import digitalio
from circuitpython_nrf24l01.rf24 import RF24

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Button, Input, RichLog
from textual.worker import Worker, get_current_worker
from textual.reactive import reactive

# ==========================================
# 1. HARDWARE INITIALIZATION (SHARKDECK)
# ==========================================
try:
    # Hardware SPI Mapping from PCB Image
    CE_PIN = digitalio.DigitalInOut(board.PI8)   # Pin 2 / 7
    CSN_PIN = digitalio.DigitalInOut(board.PI7)  # Pin 5
    spi = board.SPI()

    radio = RF24(spi, CSN_PIN, CE_PIN)
    radio.address_width = 5
    radio.channel = 76
    radio.data_rate = 1  # 1 Mbps
    radio.pa_level = 0   # Max Power (0 dBm)
    RADIO_HARDWARE_AVAILABLE = True
except Exception as e:
    # Fallback to prevent app crash if testing code directly on a PC
    RADIO_HARDWARE_AVAILABLE = False
    RADIO_ERROR_MSG = str(e)

ADDRESSES = [b"1Node", b"2Node"]

# ==========================================
# 2. MODERN CYBERDECK TUI APP
# ==========================================
class SharkdeckRFApp(App):
    """A premium, keyboard-driven Terminal UI for the Sharkdeck RF Toolkit."""

    TITLE = "🦈 SHARKDECK RF TOOLKIT 🦈"
    SUB_TITLE = "v2.0 Beta - NRF24L01 Controller"

    # Custom CSS variables inside the script for sleek cyberpunk look
    CSS = """
    Screen {
        background: #0d1117;
    }
    #sidebar {
        width: 18;
        background: #161b22;
        border-right: tall #58a6ff;
        padding: 1 0;
    }
    .nav-btn {
        width: 100%;
        margin: 0 0 1 0;
        background: #21262d;
        color: #c9d1d9;
        border: none;
    }
    .nav-btn:focus {
        background: #58a6ff;
        color: #ffffff;
        text-style: bold;
    }
    #main-container {
        padding: 1 2;
    }
    .module-card {
        border: solid #30363d;
        background: #161b22;
        padding: 1 2;
        height: 100%;
    }
    .title-banner {
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }
    .warning-banner {
        color: #ff7b72;
        text-style: bold;
        margin-bottom: 1;
    }
    RichLog {
        background: #010409;
        border: round #30363d;
        color: #7ee787;
    }
    Input {
        background: #21262d;
        border: round #30363d;
        color: #ffffff;
    }
    Input:focus {
        border: tall #58a6ff;
    }
    .action-btn {
        background: #238636;
        color: white;
    }
    .action-btn:focus {
        background: #2ea44f;
    }
    .stop-btn {
        background: #da3637;
        color: white;
    }
    .stop-btn:focus {
        background: #f85149;
    }
    .row {
        height: auto;
        margin-bottom: 1;
    }
    .row Static {
        width: auto;
        content-align: left middle;
        padding: 1 1 0 0;
    }
    """

    # Global Key Bindings for Keyboard Navigation
    BINDINGS = [
        ("t,T", "switch_mode('tx')", "Transmit Mode"),
        ("r,R", "switch_mode('rx')", "Receive Mode"),
        ("j,J", "switch_mode('jam')", "Jammer Test"),
        ("q,Q,ctrl+c", "quit", "Exit System"),
    ]

    # Reactive variables to automatically update TUI states refreshingly
    jam_packet_count = reactive(0)
    jam_speed = reactive(0)

    def compose(self) -> ComposeResult:
        """Builds the layout structure optimized for 480x320 view."""
        yield Header(show_clock=True)
        with Horizontal():
            # Navigation Sidebar
            with Vertical(id="sidebar"):
                yield Button("[T] TRANSMIT", id="btn-nav-tx", classes="nav-btn")
                yield Button("[R] RECEIVE", id="btn-nav-rx", classes="nav-btn")
                yield Button("[J] JAM TEST", id="btn-nav-jam", classes="nav-btn")
                yield Static("\n[⚡] HW STATUS:", classes="title-banner")
                if RADIO_HARDWARE_AVAILABLE:
                    yield Static(" [🟢] ONLINE\n Channel: 76\n Power: MAX")
                else:
                    yield Static(" [🔴] OFFLINE\n SPI Error")

            # Content Deck Panels
            with Container(id="main-container"):
                # PANEL 1: TRANSMITTER
                with Vertical(id="panel-tx", classes="module-card"):
                    yield Static("📡 PACKET TRANSMITTER MODULE", classes="title-banner")
                    yield Horizontal(
                        Static("Payload Message: "),
                        Input(value="Sharkdeck Data Ping", id="tx-input"),
                        classes="row"
                    )
                    yield Button("🚀 Send Payload Sequence", id="btn-tx-start", classes="action-btn")
                    yield RichLog(id="tx-log")

                # PANEL 2: RECEIVER
                with Vertical(id="panel-rx", classes="module-card"):
                    yield Static("👁️ RF CHANNEL SNIFFER / RECEIVER", classes="title-banner")
                    yield Static("Listening Feed (Decoded UTF-8 Lines):")
                    yield RichLog(id="rx-log")

                # PANEL 3: JAMMER / CONGESTION TEST
                with Vertical(id="panel-jam", classes="module-card"):
                    yield Static("⚠️ RF SPECTRAL CONGESTION TESTBENCH", classes="warning-banner")
                    yield Horizontal(
                        Static("Target Channel (0-125): "),
                        Input(value="76", id="jam-channel-input"),
                        classes="row"
                    )
                    yield Horizontal(
                        Button("⚡ START PACKET FLOOD", id="btn-jam-start", classes="action-btn"),
                        Button("🛑 STOP FLOOD", id="btn-jam-stop", classes="stop-btn"),
                        classes="row"
                    )
                    yield Static("\n📊 REAL-TIME EMISSION METRICS:")
                    self.lbl_jam_stats = Static("System Status: Idle / Standby")
                    yield self.lbl_jam_stats

        yield Footer()

    def on_mount(self) -> None:
        """Set up initial view properties when screen initiates."""
        self.action_switch_mode("tx")
        if not RADIO_HARDWARE_AVAILABLE:
            self.query_one("#tx-log", RichLog).write(f"[⚠️ HW ERROR]: {RADIO_ERROR_MSG}")

    # ==========================================
    # 3. INTERFACE NAVIGATION LOGIC
    # ==========================================
    def action_switch_mode(self, mode: str) -> None:
        """Switches visibility panels seamlessly based on sidebar commands."""
        self.query_one("#panel-tx").display = (mode == "tx")
        self.query_one("#panel-rx").display = (mode == "rx")
        self.query_one("#panel-jam").display = (mode == "jam")

        # Reset tracking colors on focus paths
        self.query_one("#btn-nav-tx").variant = "primary" if mode == "tx" else "default"
        self.query_one("#btn-nav-rx").variant = "primary" if mode == "rx" else "default"
        self.query_one("#btn-nav-jam").variant = "primary" if mode == "jam" else "default"

        # Stop active asynchronous listen hooks when jumping off the Receiver page
        if mode != "rx":
            self.stop_worker_by_group("receiver_stream")
        if mode != "jam":
            self.stop_worker_by_group("jammer_stream")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button execution bindings."""
        btn_id = event.button.id
        if btn_id == "btn-nav-tx": self.action_switch_mode("tx")
        elif btn_id == "btn-nav-rx": self.action_switch_mode("rx")
        elif btn_id == "btn-nav-jam": self.action_switch_mode("jam")

        # Hardware Operations Actions
        elif btn_id == "btn-tx-start": self.run_transmitter_sequence()
        elif btn_id == "btn-rx-start": self.run_receiver_stream()
        elif btn_id == "btn-jam-start": self.run_jammer_flood()
        elif btn_id == "btn-jam-stop": self.stop_jammer_flood()

    # ==========================================
    # 4. BACKGROUND HARDWARE WORKERS
    # ==========================================
    def run_transmitter_sequence(self) -> None:
        """Fires a burst payload stream running safely via background threads."""
        logger = self.query_one("#tx-log", RichLog)
        payload_text = self.query_one("#tx-input", Input).value

        if not RADIO_HARDWARE_AVAILABLE:
            logger.write("❌ Cannot Transmit: Missing Hardware Connection Mapping.")
            return

        logger.write(f"🔄 Initializing TX pipe for text: '{payload_text}'")

        # Threaded worker wrapper ensures UI remains responsive while hitting hardware
        def tx_worker():
            radio.open_tx_pipe(ADDRESSES[0])
            radio.listen = False
            for i in range(5):
                out_msg = f"{payload_text} #{i+1}"
                success = radio.send(out_msg.encode('utf-8'))
                if success:
                    self.call_from_thread(logger.write, f" [🟢 ACK] Sent: {out_msg}")
                else:
                    self.call_from_thread(logger.write, f" [🔴 FAIL] Drops: {out_msg}")
                time.sleep(0.5)
            self.call_from_thread(logger.write, "🏁 Sequence Complete.")

        self.run_worker(tx_worker, thread=True, group="tx_stream", exclusive=True)

    def run_receiver_stream(self) -> None:
        """Continuously streams raw airwaves packet data straight to UI box."""
        logger = self.query_one("#rx-log", RichLog)
        if not RADIO_HARDWARE_AVAILABLE:
            logger.write("❌ Receiver Offline: Checking Hardware Pins.")
            return

        logger.write("📡 Scanning airwaves for incoming nodes...")

        def rx_worker():
            radio.open_rx_pipe(1, ADDRESSES[0])
            radio.listen = True
            worker = get_current_worker()

            while not worker.is_cancelled:
                if radio.any():
                    raw_data = radio.read()
                    try:
                        decoded = raw_data.decode('utf-8').strip("\x00")
                        self.call_from_thread(logger.write, f"📥 Received: {decoded}")
                    except Exception:
                        self.call_from_thread(logger.write, f"📥 Raw Bytes: {raw_data.hex()}")
                time.sleep(0.05)

        self.run_worker(rx_worker, thread=True, group="receiver_stream", exclusive=True)

    def run_jammer_flood(self) -> None:
        """Floods the spectrum bypassing ACK wait sequences for raw high-speed metrics."""
        if not RADIO_HARDWARE_AVAILABLE:
            self.lbl_jam_stats.update("❌ Jammer Error: Missing physical radio unit.")
            return

        try:
            target_chan = int(self.query_one("#jam-channel-input", Input).value)
            radio.channel = max(0, min(target_chan, 125))
        except ValueError:
            radio.channel = 76

        self.lbl_jam_stats.update(f"⚡ FLOOD ACTIVE ON FREQUENCY {2400 + radio.channel}MHz...")

        def jam_worker():
            radio.open_tx_pipe(ADDRESSES[0])
            radio.auto_ack = False  # Bypasses checking intervals to optimize processing speeds
            radio.listen = False

            payload = b"\xFF" * 32
            packets_sent = 0
            start_time = time.time()
            worker = get_current_worker()

            while not worker.is_cancelled:
                radio.send(payload, ask_no_ack=True)
                packets_sent += 1

                if packets_sent % 1500 == 0:
                    elapsed = time.time() - start_time
                    pps = int(packets_sent / elapsed)
                    # Safely push text updates backward onto main UI thread
                    self.call_from_thread(
                        self.lbl_jam_stats.update,
                        f"🔥 Status: ACTIVE FLOODING\n📦 Packets Flooded: {packets_sent:,}\n📊 Congestion Rate: ~{pps:,} pkts/sec"
                    )

            # Clean exit reset rules
            radio.auto_ack = True
            radio.power = False

        self.run_worker(jam_worker, thread=True, group="jammer_stream", exclusive=True)

    def stop_worker_by_group(self, group: str) -> None:
        """Cancel every running worker that belongs to the given group."""
        for worker in list(self.workers):
            if worker.group == group:
                worker.cancel()

    def stop_jammer_flood(self) -> None:
        """Cancels background worker and gracefully releases airwave control."""
        self.stop_worker_by_group("jammer_stream")
        self.lbl_jam_stats.update("🛑 Jammer safely disarmed. Transceiver standard idle standby.")

    def action_quit(self) -> None:
        """Ensures that the radio hardware shuts off completely upon exiting to protect the system."""
        if RADIO_HARDWARE_AVAILABLE:
            try:
                radio.power = False
            except Exception:
                pass
        self.exit()

# ==========================================
# 5. EXECUTION ENTRY POINT
# ==========================================
if __name__ == "__main__":
    app = SharkdeckRFApp()
    app.run()
