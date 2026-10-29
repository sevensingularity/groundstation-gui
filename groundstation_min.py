import sys, csv, time, random
from datetime import datetime
import pyqtgraph as pg
from serial.tools import list_ports
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QTabWidget, QPlainTextEdit, QListWidget, QComboBox

STYLE = """
QWidget { background-color: #09090b; color: white; font-size: 14px; }
QLabel { background-color: #18181b; border: 1px solid #27272a; border-radius: 12px; padding: 12px; }
QPushButton { background-color: #18181b; border: 1px solid #27272a; border-radius: 8px; padding: 8px 18px; }
QPushButton:disabled { color: #52525b; }
QPlainTextEdit { background-color: #18181b; }
"""
GRAPHS = {"Altitude (m)": "#6366f1", "Temperature (C)": "#10b981", "Pressure (hPa)": "#06b6d4", "Battery (V)": "#f59e0b"}
TITLES = ["Packets", "Elapsed", "Altitude", "Temperature", "Pressure", "Battery"]


class GroundStation(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ground Station - Idle")
        self.resize(1180, 820)
        self.setStyleSheet(STYLE)
        self.times, self.history, self.curves = [], {name: [] for name in GRAPHS}, {}
        self.cards = {title: QLabel(f"{title}\n--") for title in TITLES}
        self.log_view = QPlainTextEdit(readOnly=True)
        self.timer = QTimer(timeout=self.update_data)

        live, cards, grid = QWidget(), QHBoxLayout(), QGridLayout()
        for card in self.cards.values():
            cards.addWidget(card)
        for i, (name, color) in enumerate(GRAPHS.items()):
            plot = pg.PlotWidget(title=name, background="#18181b")
            self.curves[name] = plot.plot(pen=pg.mkPen(color, width=2))
            grid.addWidget(plot, i // 2, i % 2)
        box = QVBoxLayout(live)
        box.addLayout(cards)
        box.addLayout(grid)

        tabs = QTabWidget()
        tabs.addTab(live, "Live")
        self.ports_list, self.baud_box, self.notice = QListWidget(), QComboBox(), QLabel()
        self.baud_box.addItems(["9600", "19200", "38400", "57600", "115200"])
        ports = QWidget()
        ports_layout = QVBoxLayout(ports)
        ports_layout.addWidget(self.ports_list)
        ports_layout.addWidget(self.baud_box)
        tabs.addTab(ports, "Ports")
        tabs.addTab(self.log_view, "Log")

        self.start_button = QPushButton("Start", clicked=self.start_stream)
        self.stop_button = QPushButton("Stop", clicked=self.stop_stream, enabled=False)
        buttons = QHBoxLayout()
        buttons.addWidget(self.notice)
        buttons.addStretch()
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.stop_button)

        root = QVBoxLayout(self)
        root.addLayout(buttons)
        root.addWidget(tabs)
        self.known = set()
        self.port_timer = QTimer(timeout=self.refresh_ports, interval=1000)
        self.port_timer.start()
        self.refresh_ports()
        self.notice.setText("Waiting for a device...")

    def refresh_ports(self):
        ports = {port.device: port.description for port in list_ports.comports()}
        if set(ports) == self.known:
            return
        for device in set(ports) - self.known:
            self.notice.setText(f"Device connected: {device}")
        for device in self.known - set(ports):
            self.notice.setText(f"Device unplugged: {device}")
        self.known = set(ports)
        self.ports_list.clear()
        self.ports_list.addItems([f"{device}  -  {text}" for device, text in ports.items()])

    def start_stream(self):
        self.times, self.history = [], {name: [] for name in GRAPHS}
        for curve in self.curves.values():
            curve.setData([], [])
        filename = f"telemetry_{datetime.now():%Y%m%d_%H%M%S}.csv"
        self.log_file = open(filename, "w", newline="")
        self.writer = csv.writer(self.log_file)
        self.writer.writerow(["timestamp", "packet", "elapsed_s", "altitude_m", "temperature_c", "pressure_hpa", "battery_v"])
        self.log_view.setPlainText(f"Logging to {filename}")
        self.start_time = time.time()
        self.timer.start(1000)
        self.setWindowTitle("Ground Station - Receiving")
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_stream(self):
        self.timer.stop()
        self.log_file.close()
        self.setWindowTitle("Ground Station - Stopped")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def update_data(self):
        elapsed = time.time() - self.start_time
        data = [500 + random.uniform(-5, 5), 25 + random.uniform(-0.5, 0.5), 1013 + random.uniform(-2, 2), 3.7 + random.uniform(-0.05, 0.05)]
        self.times.append(elapsed)
        packet = len(self.times)
        texts = [str(packet), f"{elapsed:.0f} s", f"{data[0]:.1f} m", f"{data[1]:.1f} C", f"{data[2]:.1f} hPa", f"{data[3]:.2f} V"]
        for (title, card), text in zip(self.cards.items(), texts):
            card.setText(f"{title}\n{text}")
        for name, number in zip(self.history, data):
            self.history[name].append(number)
            self.curves[name].setData(self.times, self.history[name])
        row = [datetime.now().isoformat(timespec="seconds"), packet, round(elapsed, 1)] + [round(n, 3) for n in data]
        self.writer.writerow(row)
        self.log_file.flush()
        self.log_view.appendPlainText(", ".join(map(str, row)))


app = QApplication(sys.argv)
window = GroundStation()
window.show()
sys.exit(app.exec())