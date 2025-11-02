import sys
import time
import threading
from threading import Event
import pyvisa
from pyvisa.constants import Parity, StopBits
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox,
    QStackedLayout, QGridLayout, QTableWidget, QTableWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
import csv
import pandas as pd

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
                            return
                        instr.close()
                    except Exception as e:
                        print(f"Could not open {res}: {e}")
            self.status_label.setText("Status: NGP800 not found. Please check connection.")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")


class AutomationScreen(QWidget):
    def __init__(self, inst, main_window):
        self.main_window = main_window

        super().__init__()
        self.inst = inst
        self.lock = threading.Lock()

        self.channels_config = {
            1: {"enabled": False, "start": 0.0, "step": 0.0, "end": 0.0, "duration": 0},
            2: {"enabled": False, "start": 0.0, "step": 0.0, "end": 0.0, "duration": 0},
            3: {"enabled": False, "start": 0.0, "step": 0.0, "end": 0.0, "duration": 0},
            4: {"enabled": False, "start": 0.0, "step": 0.0, "end": 0.0, "duration": 0},
        }

        self.threads = []
        self.running = False

        self.paused = False
        self.pause_event = Event()  # Add this Event for pause control
        self.pause_event.set()      # Initially not paused

        self.voltage_data = {ch: [] for ch in range(1, 5)}  # store (time, voltage)

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.start_time = None

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Controls grid for 4 channels
        grid = QGridLayout()
        grid.addWidget(QLabel("Enable"), 0, 0)
        grid.addWidget(QLabel("Channel"), 0, 1)
        grid.addWidget(QLabel("Start V"), 0, 2)
        grid.addWidget(QLabel("Step V"), 0, 3)
        grid.addWidget(QLabel("End V"), 0, 4)
        grid.addWidget(QLabel("Duration (s)"), 0, 5)

        self.checkboxes = {}
        self.inputs = {}

        for ch in range(1, 5):
            cb = QCheckBox()
            cb.setChecked(self.channels_config[ch]["enabled"])
            self.checkboxes[ch] = cb
            grid.addWidget(cb, ch, 0)
            grid.addWidget(QLabel(f"CH{ch}"), ch, 1)

            start_edit = QLineEdit(str(self.channels_config[ch]["start"]))
            step_edit = QLineEdit(str(self.channels_config[ch]["step"]))
            end_edit = QLineEdit(str(self.channels_config[ch]["end"]))
            dur_edit = QLineEdit(str(self.channels_config[ch]["duration"]))

            self.inputs[ch] = {
                "start": start_edit,
                "step": step_edit,
                "end": end_edit,
                "duration": dur_edit,
            }

            grid.addWidget(start_edit, ch, 2)
            grid.addWidget(step_edit, ch, 3)
            grid.addWidget(end_edit, ch, 4)
            grid.addWidget(dur_edit, ch, 5)

        main_layout.addLayout(grid)

        # Start / Stop buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start_process)

        self.pause_btn = QPushButton("Pause")      # ADD THIS
        self.pause_btn.setEnabled(False)            # Initially disabled
        self.pause_btn.clicked.connect(self.toggle_pause)  # ADD THIS

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)        # ADD THIS
        btn_layout.addWidget(self.stop_btn)

        main_layout.addLayout(btn_layout)

        # Plot visibility checkboxes
        plot_check_layout = QHBoxLayout()
        self.plot_checks = {}
        for ch in range(1, 5):
            cb = QCheckBox(f"Show CH{ch}")
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_plot_visibility)
            self.plot_checks[ch] = cb
            plot_check_layout.addWidget(cb)
        main_layout.addLayout(plot_check_layout)



        # Plot Widget
        self.plot_widget = pg.PlotWidget(title="Voltage Output Over Time")
        self.plot_widget.addLegend()
        self.plot_widget.setLabel("left", "Voltage", "V")
        self.plot_widget.setLabel("bottom", "Time", "s")

        self.plot_curves = {}
        colors = ['r', 'g', 'b', 'y']
        for ch in range(1, 5):
            pen = pg.mkPen(color=colors[ch-1], width=2)
            curve = self.plot_widget.plot([], [], pen=pen, name=f"CH{ch}")
            self.plot_curves[ch] = curve

        main_layout.addWidget(self.plot_widget)

        # Records Button
        self.records_btn = QPushButton("View Records")
        self.records_btn.clicked.connect(self.view_records)
        main_layout.addWidget(self.records_btn)


        self.setLayout(main_layout)
    
    def update_plot_visibility(self):
        for ch in range(1, 5):
            self.plot_curves[ch].setVisible(self.plot_checks[ch].isChecked())


    def toggle_pause(self):
        if not self.running:
            return
        if self.paused:
            self.paused = False
            self.pause_event.set()   # Resume all threads
            self.pause_btn.setText("Pause")
        else:
            self.paused = True
            self.pause_event.clear() # Pause all threads
            self.pause_btn.setText("Resume")


    def start_process(self):
        # Validate inputs and update channels_config
        try:
            for ch in range(1, 5):
                self.channels_config[ch]["enabled"] = self.checkboxes[ch].isChecked()
                self.channels_config[ch]["start"] = float(self.inputs[ch]["start"].text())
                self.channels_config[ch]["step"] = float(self.inputs[ch]["step"].text())
                self.channels_config[ch]["end"] = float(self.inputs[ch]["end"].text())
                self.channels_config[ch]["duration"] = float(self.inputs[ch]["duration"].text())
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers for all fields.")
            return

        self.running = True

        self.paused = False
        self.pause_event.set()  # Ensure threads start unpaused

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)  # Enable pause button now
        self.pause_btn.setText("Pause")


        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.start_time = time.time()
        # Clear previous data
        for ch in range(1, 5):
            self.voltage_data[ch] = []

        self.threads = []
        for ch, cfg in self.channels_config.items():
            if cfg["enabled"]:
                t = threading.Thread(
                    target=self.voltage_step_thread,
                    args=(ch, cfg["start"], cfg["step"], cfg["end"], cfg["duration"])
                )
                t.start()
                self.threads.append(t)

        self.timer.start(200)  # update plot every 200ms

    def stop_process(self):
        self.running = False
        self.paused = False
        self.pause_event.set()  # Unpause threads so they can exit cleanly

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)  # Disable pause button when stopped
        self.pause_btn.setText("Pause")
        self.timer.stop()

        # Wait for threads to finish
        for t in self.threads:
            t.join()

        # Turn off outputs
        with self.lock:
            for ch in range(1, 5):
                self.inst.write(f"INST:NSEL {ch}")
                self.inst.write("OUTP OFF")

    def voltage_step_thread(self, channel, start, step, end, duration):
        voltage = start
        while voltage <= end and self.running:
            self.pause_event.wait()
            with self.lock:
                self.inst.write(f"INST:NSEL {channel}")
                self.inst.write(f"VOLT {voltage}")
                self.inst.write("OUTP ON")

            elapsed = time.time() - self.start_time
            self.voltage_data[channel].append((elapsed, voltage))

            time.sleep(duration)
            voltage += step

        with self.lock:
            self.inst.write(f"INST:NSEL {channel}")
            self.inst.write("OUTP OFF")

    def update_plot(self):
        for ch in range(1, 5):
            data = self.voltage_data[ch]
            if data:
                times, volts = zip(*data)
                self.plot_curves[ch].setData(times, volts)
            else:
                if self.plot_checks[ch].isChecked():
                    self.plot_curves[ch].clear()
    def view_records(self):
        self.main_window.show_records_screen(self.voltage_data)
    def emergency_shutdown(self):
        self.running = False
        self.paused = False
        self.pause_event.set()

        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()

        for t in self.threads:
            t.join()

        with self.lock:
            for ch in range(1, 5):
                self.inst.write(f"INST:NSEL {ch}")
                self.inst.write("OUTP OFF")





class RecordsScreen(QWidget):
    def __init__(self, back_callback, voltage_data_ref):
        super().__init__()
        self.back_callback = back_callback
        self.voltage_data_ref = voltage_data_ref

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_table)
        self.timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout()

        # Channel filter checkboxes
        self.channel_checks = {}
        check_layout = QHBoxLayout()
        for ch in range(1, 5):
            cb = QCheckBox(f"CH{ch}")
            cb.setChecked(True)
            cb.stateChanged.connect(self.refresh_table)
            self.channel_checks[ch] = cb
            check_layout.addWidget(cb)
        layout.addLayout(check_layout)

        # Table widget
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Time (s)", "Voltage (V)"])
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.back_callback)
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(back_btn)
        btn_layout.addWidget(export_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def refresh_table(self):
        selected_channels = [ch for ch in range(1, 5) if self.channel_checks[ch].isChecked()]
        if not selected_channels:
            self.table.setColumnCount(0)
            self.table.setRowCount(0)
            return

        # Determine maximum number of rows (based on longest channel data)
        max_rows = max(len(self.voltage_data_ref[ch]) for ch in selected_channels)
        self.table.setRowCount(max_rows)
        self.table.setColumnCount(len(selected_channels) + 1)

        headers = ["Time (s)"] + [f"CH{ch}" for ch in selected_channels]
        self.table.setHorizontalHeaderLabels(headers)

        for row in range(max_rows):
            # Find the time from the first channel that has this row
            for ch in selected_channels:
                if row < len(self.voltage_data_ref[ch]):
                    t = self.voltage_data_ref[ch][row][0]
                    self.table.setItem(row, 0, QTableWidgetItem(f"{t:.2f}"))
                    break
            for col, ch in enumerate(selected_channels, start=1):
                if row < len(self.voltage_data_ref[ch]):
                    v = self.voltage_data_ref[ch][row][1]
                    self.table.setItem(row, col, QTableWidgetItem(f"{v:.2f}"))


    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if not path:
            return
        with open(path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Channel", "Time (s)", "Voltage (V)"])
            for ch in range(1, 5):
                if self.channel_checks[ch].isChecked():
                    for t, v in self.voltage_data_ref[ch]:
                        writer.writerow([f"CH{ch}", t, v])


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NGP800 Automation")
        self.resize(900, 600)

        self.stack = QStackedLayout()
        self.setLayout(self.stack)

        self.connect_screen = ConnectScreen(self.on_connected)
        self.stack.addWidget(self.connect_screen)

        self.automation_screen = None
        self.records_screen = None


    def on_connected(self, inst):
        self.automation_screen = AutomationScreen(inst, self)
        self.stack.addWidget(self.automation_screen)
        self.stack.setCurrentWidget(self.automation_screen)
    
    def show_records_screen(self, voltage_data):
        self.records_screen = RecordsScreen(self.show_automation_screen, voltage_data)
        self.stack.addWidget(self.records_screen)
        self.stack.setCurrentWidget(self.records_screen)

    def closeEvent(self, event):
        if self.automation_screen:
            self.automation_screen.emergency_shutdown()
        event.accept()

    def show_automation_screen(self):
        self.stack.setCurrentWidget(self.automation_screen)

def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
