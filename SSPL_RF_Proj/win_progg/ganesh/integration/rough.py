import sys
import time
import threading
import pyvisa
from pyvisa.constants import Parity, StopBits
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QGridLayout, QMessageBox,
    QStackedLayout, QTableWidget, QTableWidgetItem, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal, QTimer
import pyqtgraph as pg
import random
from PyQt6.QtGui import QColor

# EXG Signal Generator Components (simplified)
class RFSignalController:
    def __init__(self):
        self.instrument = None
        self.freq_hz = 0.0
        self.power_dbm = 0.0

    def connect(self):
        rm = pyvisa.ResourceManager()
        for res in rm.list_resources():
            try:
                inst = rm.open_resource(res)
                idn = inst.query("*IDN?")
                if "N5173B" in idn:
                    self.instrument = inst
                    return True
            except Exception:
                continue
        return False

    def set_rf_output(self, freq_hz, power_dbm):
        if self.instrument:
            self.instrument.write(f"FREQ {freq_hz}")
            self.instrument.write(f"POW {power_dbm}DBM")
            self.instrument.write("OUTP ON")
            self.freq_hz = freq_hz
            self.power_dbm = power_dbm

    def get_current_frequency(self):
        return self.freq_hz


# Power Meter Reader Component (simplified)
class PowerMeterReader:
    def __init__(self):
        self.instrument = None

    def connect(self):
        rm = pyvisa.ResourceManager()
        for res in rm.list_resources():
            try:
                inst = rm.open_resource(res, timeout=2000)
                idn = inst.query("*IDN?").strip()
                if "NRX" in idn or "Rohde & Schwarz" in idn:
                    self.instrument = inst
                    return True
                else:
                    inst.close()
            except Exception:
                continue
        return False

    def read_power_dbm(self):
        if self.instrument:
            try:
                return float(self.instrument.query("MEAS:POW?").strip())
            except:
                return None
        return None


# Main IV Sweep Application (extends previous code)
class NGP800IVSweepApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IV Sweep with RF Signal and Power Meter")

        self.rf_controller = RFSignalController()
        self.power_reader = PowerMeterReader()
        self.rm = pyvisa.ResourceManager()
        self.instrument = None

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        self.init_connect_screen()

    def init_connect_screen(self):
        self.connect_layout = QVBoxLayout()
        self.conn_status = QLabel("Connect to instruments")
        self.connect_btn = QPushButton("Connect All")
        self.connect_btn.clicked.connect(self.connect_all)
        self.connect_layout.addWidget(self.conn_status)
        self.connect_layout.addWidget(self.connect_btn)
        self.layout.addLayout(self.connect_layout)

    def connect_all(self):
        status = []
        if self.connect_power_supply():
            status.append("NGP800 Connected")
        else:
            status.append("NGP800 Not Found")

        if self.rf_controller.connect():
            status.append("EXG Connected")
        else:
            status.append("EXG Not Found")

        if self.power_reader.connect():
            status.append("Power Meter Connected")
        else:
            status.append("Power Meter Not Found")

        self.conn_status.setText("\n".join(status))
        if self.instrument and self.rf_controller.instrument and self.power_reader.instrument:
            self.setup_main_ui()

    def connect_power_supply(self):
        try:
            for res in self.rm.list_resources():
                if "USB" in res or "ASRL" in res:
                    inst = self.rm.open_resource(res)
                    if res.startswith("ASRL"):
                        inst.baud_rate = 115200
                        inst.data_bits = 8
                        inst.stop_bits = StopBits.one
                        inst.parity = Parity.none
                        inst.write_termination = '\n'
                        inst.read_termination = '\n'
                    idn = inst.query("*IDN?")
                    if "NGP800" in idn:
                        self.instrument = inst
                        return True
        except Exception:
            return False
        return False

    def setup_main_ui(self):
        self.records = []
        self.plot = pg.PlotWidget(title="IV Sweep")
        self.layout.addWidget(self.plot)

        self.run_button = QPushButton("Run Sweep")
        self.run_button.clicked.connect(self.run_sweep)
        self.layout.addWidget(self.run_button)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Vg (V)", "Vd (V)", "Current (A)", "RF Freq (Hz)", "Power (dBm)"
        ])
        self.layout.addWidget(self.table)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.layout.addWidget(self.log_box)

    def log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.append(f"[{timestamp}] {msg}")

    def run_sweep(self):
        self.log("Starting sweep...")
        vg_values = [1, 2, 3]
        vd_values = [0.5, 1.0, 1.5]

        for vg in vg_values:
            self.instrument.write(f"INST:NSEL 1")
            self.instrument.write(f"VOLT {vg}")
            self.instrument.write("OUTP ON")
            time.sleep(1)
            for vd in vd_values:
                self.instrument.write(f"INST:NSEL 2")
                self.instrument.write(f"VOLT {vd}")
                self.instrument.write("OUTP ON")
                time.sleep(1)
                self.instrument.write("MEAS:CURR?")
                current = float(self.instrument.read())

                rf_freq = self.rf_controller.get_current_frequency()
                power = self.power_reader.read_power_dbm()
                timestamp = time.strftime("%H:%M:%S")

                row = [timestamp, vg, vd, current, rf_freq, power]
                self.records.append(row)
                row_idx = self.table.rowCount()
                self.table.insertRow(row_idx)
                for col, val in enumerate(row):
                    self.table.setItem(row_idx, col, QTableWidgetItem(str(val)))

                self.plot.plot([vd], [current], pen=None, symbol='o')

        self.log("Sweep complete.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NGP800IVSweepApp()
    window.show()
    sys.exit(app.exec())
