
import sys
import time
import threading
import pyvisa
from pyvisa.constants import Parity, StopBits
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QGridLayout, QMessageBox, QStackedLayout, QTableWidgetItem
)
import pyqtgraph as pg
import random
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtCore import QThread, QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QObject, pyqtSignal

class ConnectScreen(QWidget):
    def __init__(self, on_connected_callback):
        super().__init__()
        self.on_connected_callback = on_connected_callback
        self.rm = None
        self.inst = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.label = QLabel("Press 'Connect' to detect NGP800 power supply.")
        self.status_label = QLabel("Status: Not connected")
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.try_connect)

        layout.addWidget(self.label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.connect_btn)
        layout.addStretch()

        self.setLayout(layout)

    def try_connect(self):
        self.status_label.setText("Status: Scanning...")
        QApplication.processEvents()

        try:
            self.rm = pyvisa.ResourceManager()
            resources = self.rm.list_resources()
            print("Available VISA resources:", resources)

            for res in resources:
                if "USB" in res or "ASRL" in res:
                    try:
                        instr = self.rm.open_resource(res)
                        if res.startswith("ASRL"):
                            instr.baud_rate = 115200
                            instr.data_bits = 8
                            instr.stop_bits = StopBits.one
                            instr.parity = Parity.none
                            instr.timeout = 2000
                            instr.write_termination = '\n'
                            instr.read_termination = '\n'
                        idn = instr.query("*IDN?")
                        if "NGP800" in idn or "ROHDE" in idn.upper():
                            self.inst = instr
                            self.status_label.setText(f"Status: Connected to {idn.strip()}")
                            self.connect_btn.setEnabled(False)
                            self.on_connected_callback(self.inst)
                            print(f"[LOG] Connected to {idn.strip()}")
                            return
                        instr.close()
                    except Exception as e:
                        print(f"Could not open {res}: {e}")
            self.status_label.setText("Status: NGP800 not found. Please check connection.")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")


class SweepWorker(QObject):
    update_plot = pyqtSignal(object, list, list)
    log_msg = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, instrument, vg_chan, vd_chan,
             vg_values, vd_values, vg_dur, vd_dur,
             stop_event, pause_event,
             vg_max=None, vd_max=None, curr_max=None):
        super().__init__()
        self.instrument = instrument
        self.vg_chan = vg_chan
        self.vd_chan = vd_chan
        self.vg_values = vg_values
        self.vd_values = vd_values
        self.vg_dur = vg_dur
        self.vd_dur = vd_dur
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.vg_max = vg_max
        self.vd_max = vd_max
        self.curr_max = curr_max

    def run(self):
        try:
            import pyqtgraph as pg
            import random
            from PyQt6.QtGui import QColor

            for vg in self.vg_values:
                if self.stop_event.is_set():
                    break
                self.log_msg.emit(f"Setting Vgate to {vg} V on channel {self.vg_chan}")
                self.instrument.write(f"INST:NSEL {self.vg_chan}")
                self.instrument.write(f"VOLT {vg}")
                self.instrument.write(f"OUTP ON")
                # Check Vgate limit
                if self.vg_max is not None and vg > self.vg_max:
                    self.log_msg.emit(f"Vgate limit exceeded: {vg} > {self.vg_max}. Stopping sweep.")
                    self.stop_event.set()
                    break
                time.sleep(self.vg_dur)


                currents = []
                plot_data = pg.PlotDataItem(pen=pg.mkPen(QColor(*[random.randint(0, 255) for _ in range(3)]), width=2), name=f"Vg={vg}V")
                self.update_plot.emit(plot_data, [], [])

                for i, vd in enumerate(self.vd_values):
                    while self.pause_event.is_set():
                        time.sleep(0.1)
                    if self.stop_event.is_set():
                        break

                    self.log_msg.emit(f"Setting Vdrain to {vd} V on channel {self.vd_chan}")
                    self.instrument.write(f"INST:NSEL {self.vd_chan}")
                    self.instrument.write(f"VOLT {vd}")
                    self.instrument.write(f"OUTP ON")
                    time.sleep(self.vd_dur)

                    self.instrument.write("MEAS:CURR?")
                    current = float(self.instrument.read())
                    timestamp = time.strftime("%H:%M:%S")
                    # Check limits
                    if self.vd_max is not None and vd > self.vd_max:
                        self.log_msg.emit(f"Vdrain limit exceeded: {vd} > {self.vd_max}. Stopping sweep.")
                        self.stop_event.set()
                        break
                    if self.curr_max is not None and current > self.curr_max:
                        self.log_msg.emit(f"Current limit exceeded: {current} > {self.curr_max}. Stopping sweep.")
                        self.stop_event.set()
                        break

                    self.log_msg.emit(f"[RECORD] {timestamp}, Vg={vg}, Vd={vd}, I={current:.6f} A")
                    # Signal used for record logging - handled via log_msg for simplicity

                    record_signal = pyqtSignal(str, float, float, float)
                    self.log_msg.emit(f"Measured current: {current:.6f} A")
                    currents.append(current)
                    self.update_plot.emit(plot_data, self.vd_values[:i+1], currents)

        except Exception as e:
            self.log_msg.emit(f"Error: {str(e)}")
        
        # Turn off Vdrain and Vgate channels
        try:
            self.instrument.write(f"INST:NSEL {self.vg_chan}")
            self.instrument.write("OUTP OFF")
            self.instrument.write(f"INST:NSEL {self.vd_chan}")
            self.instrument.write("OUTP OFF")
            self.log_msg.emit("Turned OFF Vgate and Vdrain channels after sweep completion.")
        except Exception as e:
            self.log_msg.emit(f"Failed to turn off channels after sweep: {e}")

        self.finished.emit()

class NGP800IVSweepApp(QWidget):
    update_plot = pyqtSignal(object, list, list)  # name, x, y
    reset_ui = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NGP800 I-V Characterization")
        self.update_plot.connect(self.handle_update_plot)
        self.reset_ui.connect(self.handle_reset_ui)

        self.stack = QStackedLayout()
        self.setLayout(self.stack)

        self.connect_screen = ConnectScreen(self.on_connected)
        self.stack.addWidget(self.connect_screen)

        self.instrument = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_paused = False
        self.setup_records_ui()


    def on_connected(self, inst):
        self.instrument = inst
        self.setup_config_ui()

    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_widget.append(f"[{timestamp}] {message}")

        if message.startswith("[RECORD]"):
            try:
                parts = message.replace("[RECORD]", "").strip().split(",")
                time_str = parts[0].strip()
                vg = float(parts[1].split("=")[1])
                vd = float(parts[2].split("=")[1])
                curr = float(parts[3].split("=")[1].split()[0])

                row = self.records_table.rowCount()
                self.records_table.insertRow(row)
                self.records_table.setItem(row, 0, QTableWidgetItem(time_str))
                self.records_table.setItem(row, 1, QTableWidgetItem(f"{vg:.3f}"))
                self.records_table.setItem(row, 2, QTableWidgetItem(f"{vd:.3f}"))
                self.records_table.setItem(row, 3, QTableWidgetItem(f"{curr:.6f}"))
            except Exception as e:
                print(f"[RECORD PARSE ERROR] {e}")



    def handle_update_plot(self, plot_data, x_vals, y_vals):
        if plot_data not in self.plot_widget.listDataItems():
            self.plot_widget.addItem(plot_data)
        plot_data.setData(x_vals, y_vals)


    def handle_reset_ui(self):
        self.run_button.setEnabled(True)
        self.pause_resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.pause_event.clear()
        self.stop_event.clear()
        self.is_paused = False
        self.pause_resume_button.setText("Pause")

    def setup_records_ui(self):
        self.records_widget = QWidget()
        layout = QVBoxLayout(self.records_widget)

        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(4)
        self.records_table.setHorizontalHeaderLabels(["Timestamp", "Vgate (V)", "Vdrain (V)", "Current (A)"])
        layout.addWidget(self.records_table)

        back_button = QPushButton("Back")
        back_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.config_widget))
        layout.addWidget(back_button)

        export_button = QPushButton("Export CSV")
        export_button.clicked.connect(self.export_records_to_csv)
        layout.addWidget(export_button)

        self.stack.addWidget(self.records_widget)

    def show_records_screen(self):
        self.stack.setCurrentWidget(self.records_widget)

    def export_records_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Records as CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path:
            try:
                with open(path, 'w') as f:
                    # Write header
                    headers = [self.records_table.horizontalHeaderItem(i).text() for i in range(self.records_table.columnCount())]
                    f.write(",".join(headers) + "\n")
                    # Write table data
                    for row in range(self.records_table.rowCount()):
                        row_data = []
                        for col in range(self.records_table.columnCount()):
                            item = self.records_table.item(row, col)
                            row_data.append(item.text() if item else "")
                        f.write(",".join(row_data) + "\n")
                self.log(f"Records exported to {path}")
            except Exception as e:
                QMessageBox.warning(self, "Export Error", f"Failed to export records: {e}")


    def setup_config_ui(self):
        self.config_widget = QWidget()
        layout = QVBoxLayout()
        self.config_widget.setLayout(layout)
        self.stack.addWidget(self.config_widget)
        self.stack.setCurrentWidget(self.config_widget)

        # Channel selectors
        chan_layout = QHBoxLayout()
        self.vd_chan_combo = QComboBox()
        self.vg_chan_combo = QComboBox()
        for i in range(1, 5):
            self.vd_chan_combo.addItem(f"CH{i}")
            self.vg_chan_combo.addItem(f"CH{i}")
        chan_layout.addWidget(QLabel("Vdrain Channel:"))
        chan_layout.addWidget(self.vd_chan_combo)
        chan_layout.addSpacing(40)
        chan_layout.addWidget(QLabel("Vgate Channel:"))
        chan_layout.addWidget(self.vg_chan_combo)
        layout.addLayout(chan_layout)

        # Grid for inputs: Vd and Vg start, step, end, duration
        grid = QGridLayout()
        grid.addWidget(QLabel(""), 0, 0)  # empty corner
        grid.addWidget(QLabel("Start"), 0, 1)
        grid.addWidget(QLabel("Step"), 0, 2)
        grid.addWidget(QLabel("End"), 0, 3)
        grid.addWidget(QLabel("Duration (s)"), 0, 4)

        # Vd row
        grid.addWidget(QLabel("Vdrain (V):"), 1, 0)
        self.vd_start = QLineEdit()
        self.vd_step = QLineEdit()
        self.vd_end = QLineEdit()
        self.vd_dur = QLineEdit()
        self.vd_start.setPlaceholderText("e.g. 2")
        self.vd_step.setPlaceholderText("e.g. 3")
        self.vd_end.setPlaceholderText("e.g. 20")
        self.vd_dur.setPlaceholderText("e.g. 0.5")
        grid.addWidget(self.vd_start, 1, 1)
        grid.addWidget(self.vd_step, 1, 2)
        grid.addWidget(self.vd_end, 1, 3)
        grid.addWidget(self.vd_dur, 1, 4)

        # Vg row
        grid.addWidget(QLabel("Vgate (V):"), 2, 0)
        self.vg_start = QLineEdit()
        self.vg_step = QLineEdit()
        self.vg_end = QLineEdit()
        self.vg_dur = QLineEdit()
        self.vg_start.setPlaceholderText("e.g. 10")
        self.vg_step.setPlaceholderText("e.g. -1")
        self.vg_end.setPlaceholderText("e.g. 1")
        self.vg_dur.setPlaceholderText("e.g. 1")
        grid.addWidget(self.vg_start, 2, 1)
        grid.addWidget(self.vg_step, 2, 2)
        grid.addWidget(self.vg_end, 2, 3)
        grid.addWidget(self.vg_dur, 2, 4)

        # Max limits inputs row labels
        grid.addWidget(QLabel("Max Limit"), 3, 0)
        self.vd_max_limit = QLineEdit()
        self.vg_max_limit = QLineEdit()
        self.curr_max_limit = QLineEdit()
        self.vd_max_limit.setPlaceholderText("Max Vdrain (V)")
        self.vg_max_limit.setPlaceholderText("Max Vgate (V)")
        self.curr_max_limit.setPlaceholderText("Max Current (A)")
        grid.addWidget(self.vd_max_limit, 3, 1)
        grid.addWidget(self.vg_max_limit, 3, 2)
        grid.addWidget(self.curr_max_limit, 3, 3)

        # Set Limits button
        self.set_limits_button = QPushButton("Set Limits")
        grid.addWidget(self.set_limits_button, 3, 4)

        layout.addLayout(grid)

        # Buttons layout
        btn_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Sweep")
        self.pause_resume_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.pause_resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        btn_layout.addWidget(self.run_button)
        btn_layout.addWidget(self.pause_resume_button)
        btn_layout.addWidget(self.stop_button)
        layout.addLayout(btn_layout)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Drain Current (A)')
        self.plot_widget.setLabel('bottom', 'Vdrain (V)')
        layout.addWidget(self.plot_widget)

        # Log output
        self.log_output = QLineEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Logs will appear here...")
        layout.addWidget(QLabel("Log:"))
        self.log_box = pg.TextItem(anchor=(0, 1))  # For plot text, not needed here actually
        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setMaximumHeight(100)
        layout.addWidget(self.log_widget)

        # View Records Button
        self.view_records_button = QPushButton("View Records")
        layout.addWidget(self.view_records_button)
        self.view_records_button.clicked.connect(self.show_records_screen)

        # Connect buttons
        self.run_button.clicked.connect(self.run_sweep_threaded)
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.stop_button.clicked.connect(self.stop_sweep)
        # Initialize limits to None
        self.vd_max = None
        self.vg_max = None
        self.curr_max = None

        # Connect Set Limits button
        self.set_limits_button.clicked.connect(self.set_limits)


    def set_limits(self):
        try:
            self.vd_max = float(self.vd_max_limit.text())
            self.vg_max = float(self.vg_max_limit.text())
            self.curr_max = float(self.curr_max_limit.text())
            self.log(f"Limits set: Max Vdrain={self.vd_max}, Max Vgate={self.vg_max}, Max Current={self.curr_max}")
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric limits for Vdrain, Vgate, and Current.")
            self.vd_max = None
            self.vg_max = None
            self.curr_max = None


    def toggle_pause_resume(self):
        if not self.is_paused:
            self.pause_event.set()
            self.log("Sweep paused.")
            self.pause_resume_button.setText("Resume")
            self.is_paused = True
        else:
            self.pause_event.clear()
            self.log("Sweep resumed.")
            self.pause_resume_button.setText("Pause")
            self.is_paused = False

    def stop_sweep(self):
        self.log("Stop requested.")
        self.stop_event.set()

        try:
            # Turn off all channels (1 to 4)
            for ch in range(1, 5):
                self.instrument.write(f"INST:NSEL {ch}")
                self.instrument.write("OUTP OFF")
            self.log("All channels turned OFF.")
        except Exception as e:
            self.log(f"Failed to turn off channels: {e}")


    def run_sweep_threaded(self):
        try:
            # Validate inputs
            vg_start = float(self.vg_start.text())
            vg_step = float(self.vg_step.text())
            vg_end = float(self.vg_end.text())
            vg_dur = float(self.vg_dur.text())

            vd_start = float(self.vd_start.text())
            vd_step = float(self.vd_step.text())
            vd_end = float(self.vd_end.text())
            vd_dur = float(self.vd_dur.text())

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for all fields.")
            return

        self.stop_event.clear()
        self.pause_event.clear()
        self.is_paused = False
        self.pause_resume_button.setText("Pause")
        self.pause_resume_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)

        vg_chan = self.vg_chan_combo.currentText().replace("CH", "")
        vd_chan = self.vd_chan_combo.currentText().replace("CH", "")
        vg_values = [round(v, 6) for v in self.frange(vg_start, vg_end, vg_step)]
        vd_values = [round(v, 6) for v in self.frange(vd_start, vd_end, vd_step)]

        self.plot_widget.clear()
        self.plot_widget.addLegend()

        self.worker = SweepWorker(
            self.instrument, vg_chan, vd_chan, vg_values, vd_values, vg_dur, vd_dur,
            self.stop_event, self.pause_event,
            vg_max=self.vg_max, vd_max=self.vd_max, curr_max=self.curr_max
        )

        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.worker.update_plot.connect(self.handle_update_plot)
        self.worker.log_msg.connect(self.log)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.handle_reset_ui)

        self.thread.started.connect(self.worker.run)
        self.thread.start()

    def frange(self, start, stop, step):
        values = []
        v = start
        if step > 0:
            while v <= stop:
                values.append(round(v, 6))  # rounding here to keep consistency
                v += step
        elif step < 0:
            while v >= stop:
                values.append(round(v, 6))
                v += step
        else:
            raise ValueError("Step must not be zero")
        return values


    def closeEvent(self, event):
        if self.instrument:
            try:
                for ch in range(1, 5):
                    self.instrument.write(f"INST:NSEL {ch}")
                    self.instrument.write("OUTP OFF")
            except Exception as e:
                print(f"Error turning off channels: {e}")
        event.accept()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NGP800IVSweepApp()
    window.resize(850, 600)
    window.show()
    sys.exit(app.exec())


# === INTEGRATION GUIDE ===

# === PATCH START: Integrate Shared RF Frequency and Power Meter Reading ===
self.shared_rf_frequency = lambda: "N/A"
self.shared_power_reading = lambda: "N/A"
# === PATCH END ===

# === PATCH START: Extend Records Table Columns ===
self.records_table.setColumnCount(6)
self.records_table.setHorizontalHeaderLabels(["Timestamp", "Vgate (V)", "Vdrain (V)", "Current (A)", "RF Freq", "Power"])
# === PATCH END ===

# === PATCH START: Add RF + Power to Log Parsing ===
rf = self.shared_rf_frequency() if hasattr(self, 'shared_rf_frequency') else "N/A"
pwr = self.shared_power_reading() if hasattr(self, 'shared_power_reading') else "N/A"
self.records_table.setItem(row, 4, QTableWidgetItem(rf))
self.records_table.setItem(row, 5, QTableWidgetItem(pwr))
# === PATCH END ===
