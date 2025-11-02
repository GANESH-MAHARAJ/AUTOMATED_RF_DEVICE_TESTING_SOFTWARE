import sys
import time
import threading
import pyvisa
from pyvisa.constants import Parity, StopBits
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,QTextEdit,QHeaderView,QTableWidget,QTabWidget,
    QVBoxLayout, QHBoxLayout, QComboBox, QGridLayout, QMessageBox, QStackedLayout, QTableWidgetItem,QFileDialog,
)
import pyqtgraph as pg
import random
from PyQt6.QtGui import QColor
from PyQt6.QtCore import QThread, QObject, pyqtSignal,Qt, pyqtSignal,QObject, pyqtSignal,QTimer,pyqtSlot,QEventLoop 
# from i_power_meter_gui import ControlScreen as PowerControlScreen
from i_exg_n5173B import ControlScreen as RFControlScreen


class MultiInstrumentConnectScreen(QWidget):
    def __init__(self, on_all_connected):
        super().__init__()
        self.on_all_connected = on_all_connected

        self.ngp800_instr = None
        self.exg_instr = None
        self.nrx_instr = None

        self.init_ui()

    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def init_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Connect to all instruments below:"))

        # NGP800
        self.ngp800_status = QLabel("NGP800: Not connected")
        self.ngp800_button = QPushButton("Connect NGP800")
        self.ngp800_button.clicked.connect(self.connect_ngp800)
        layout.addWidget(self.ngp800_status)
        layout.addWidget(self.ngp800_button)

        # EXG
        self.exg_status = QLabel("EXG Signal Generator: Not connected")
        self.exg_button = QPushButton("Connect EXG")
        self.exg_button.clicked.connect(self.connect_exg)
        layout.addWidget(self.exg_status)
        layout.addWidget(self.exg_button)

        # NRX
        self.nrx_status = QLabel("NRX Power Meter: Not connected")
        self.nrx_button = QPushButton("Connect NRX Power Meter")
        self.nrx_button.clicked.connect(self.connect_nrx)
        layout.addWidget(self.nrx_status)
        layout.addWidget(self.nrx_button)

        self.setLayout(layout)

    def connect_ngp800(self):
        self.log("Scanning for NGP800...")
        self.ngp800_status.setText("NGP800: Scanning...")
        QApplication.processEvents()
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.log(f"Resources found: {resources}")
            for res in resources:
                if "USB" in res or "ASRL" in res:
                    try:
                        self.log(f"Trying: {res}")
                        instr = rm.open_resource(res)
                        if res.startswith("ASRL"):
                            instr.baud_rate = 115200
                            instr.data_bits = 8
                            instr.stop_bits = StopBits.one
                            instr.parity = Parity.none
                            instr.timeout = 2000
                            instr.write_termination = '\n'
                            instr.read_termination = '\n'
                        instr.timeout = 2000
                        idn = instr.query("*IDN?").strip()
                        self.log(f"IDN for {res}: {idn}")
                        if "NGP800" in idn or "ROHDE" in idn.upper():
                            self.ngp800_instr = instr
                            self.ngp800_status.setText(f"Connected to: {idn}")
                            self.ngp800_button.setEnabled(False)
                            self.check_all_connected()
                            return
                        instr.close()
                    except Exception as e:
                        self.log(f"Error connecting to {res}: {e}")
            self.ngp800_status.setText("NGP800 not found.")
        except Exception as e:
            self.log(f"NGP800 VISA error: {e}")
            self.ngp800_status.setText(f"Error: {e}")

    def connect_exg(self):
        self.log("Scanning for EXG Signal Generator...")
        self.exg_status.setText("EXG: Scanning...")
        QApplication.processEvents()
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.log(f"Resources found: {resources}")
            for res in resources:
                try:
                    self.log(f"Trying: {res}")
                    instr = rm.open_resource(res)
                    instr.timeout = 2000
                    idn = instr.query("*IDN?").strip()
                    self.log(f"IDN for {res}: {idn}")
                    if "N5173B" in idn:
                        self.exg_instr = instr
                        self.exg_status.setText(f"Connected to: {idn}")
                        self.exg_button.setEnabled(False)
                        self.check_all_connected()
                        return
                    else:
                        instr.close()
                except Exception as e:
                    self.log(f"Error connecting to {res}: {e}")
            self.exg_status.setText("EXG not found.")
        except Exception as e:
            self.log(f"EXG VISA error: {e}")
            self.exg_status.setText(f"Error: {e}")

    def connect_nrx(self):
        self.log("Scanning for NRX Power Meter...")
        self.nrx_status.setText("NRX: Scanning...")
        QApplication.processEvents()
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.log(f"Resources found: {resources}")
            for res in resources:
                try:
                    self.log(f"Trying: {res}")
                    instr = rm.open_resource(res)
                    instr.timeout = 2000
                    idn = instr.query("*IDN?").strip()
                    if "NRX" in idn:
                        self.nrx_instr_type = "NRX"
                    elif "NRP2" in idn:
                        self.nrx_instr_type = "NRP2"
                    else:
                        self.nrx_instr_type = "UNKNOWN"

                    self.log(f"IDN for {res}: {idn}")
                    if "NRX" in idn or "NRP2" in idn or "Rohde & Schwarz" in idn:
                        self.nrx_instr = instr
                        self.nrx_instr.device_type = self.nrx_instr_type

                        self.nrx_status.setText(f"Connected to: {idn}")
                        self.nrx_button.setEnabled(False)
                        self.check_all_connected()
                        return
                    else:
                        instr.close()
                except Exception as e:
                    self.log(f"Error connecting to {res}: {e}")
            self.nrx_status.setText("NRX not found.")
        except Exception as e:
            self.log(f"NRX VISA error: {e}")
            self.nrx_status.setText(f"Error: {e}")

    def check_all_connected(self):
        if self.ngp800_instr and self.exg_instr and self.nrx_instr:
            self.log("All instruments connected.")
            self.on_all_connected(self.ngp800_instr, self.exg_instr, self.nrx_instr)

class SweepWorker(QObject):
    update_plot = pyqtSignal(object, list, list)
    log_msg = pyqtSignal(str)
    finished = pyqtSignal()
    start_work = pyqtSignal()
    plot_ready = pyqtSignal(str)
    plot_data_signal = pyqtSignal(object, list, list)
    plot_init_signal = pyqtSignal(object, object)  # plot_widget, plot_data_item




    def __init__(self, instrument, vg_chan, vd_chan,
             vg_values, vd_values, vg_dur, vd_dur,
             stop_event, pause_event,
             vg_max=None, vd_max=None, curr_max=None,
             rf_instr=None, pm_instr=None,  plot_target=None):
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
        self.rf_instr = rf_instr
        self.pm_instr = pm_instr
        self.plot_target = plot_target
        

        self._plot_items = []  # Prevent PlotDataItem from being garbage collected

    @pyqtSlot()
    def run(self):
        self.log_msg.emit("SweepWorker started (RF only mode)")

        try:
            self.instrument.write(f"INST:NSEL {self.vd_chan}")
            self.instrument.write("MEAS:CURR?")
            current = float(self.instrument.read())

            rf_freq = None
            power_in = None
            live_power = None

            if self.rf_instr:
                try:
                    rf_freq = float(self.rf_instr.query("FREQ?").strip())
                    power_in = float(self.rf_instr.query("POW?").strip())
                except Exception as e:
                    self.log_msg.emit(f"[WARNING] RF read failed: {e}")

            if self.pm_instr:
                try:
                    time.sleep(0.5)
                    if hasattr(self.pm_instr, "device_type") and self.pm_instr.device_type == "NRP2":
                        response = self.pm_instr.query("READ?").strip()
                    else:
                        response = self.pm_instr.query("MEAS:POW?").strip()
                    live_power = float(response)
                except Exception as e:
                    self.log_msg.emit(f"[WARNING] Power meter read failed: {e}")

            timestamp = time.strftime("%H:%M:%S")
            self.log_msg.emit(
                f"[RECORD] {timestamp}, Vg={self.app.latest_vg}, Vd={self.app.latest_vd}, I={current:.8f} A, "
                f"Freq={rf_freq}, PowerIN={power_in}, Power={live_power}"
            )

            self.log_msg.emit(f"Measured current: {current:.8f} A")

        except Exception as e:
            self.log_msg.emit(f"[ERROR] Exception in SweepWorker: {e}")

        self.finished.emit()

class RFSweepWorker(QObject):
    finished = pyqtSignal()
    log_msg = pyqtSignal(str)
    update_plot = pyqtSignal(object, list, list)

    def __init__(self, app, rf_powers, vg_chan, vd_chan, vg_values, vd_values, vg_dur, vd_dur):
        super().__init__()
        self.app = app
        self.rf_powers = rf_powers
        self.vg_chan = vg_chan
        self.vd_chan = vd_chan
        self.vg_values = vg_values
        self.vd_values = vd_values
        self.vg_dur = vg_dur
        self.vd_dur = vd_dur

    def run(self):
        for rf_power in self.rf_powers:
            if self.app.stop_event.is_set():
                break
            try:
                self.app.exg_instr.write("OUTP OFF")
                self.app.exg_instr.write(f"POW {rf_power} dBm")
                self.app.exg_instr.write("OUTP ON")
                self.log_msg.emit(f"RF Power set to {rf_power} dBm")
                time.sleep(1)
            except Exception as e:
                self.log_msg.emit(f"Error setting RF power: {e}")
                break

            self.app.stop_event.clear()

            # Create sweep worker
            plot_target = self.app.rf_plot_widgets.get(rf_power)
            worker = SweepWorker(
                
                self.app.instrument, self.vg_chan, self.vd_chan,
                self.vg_values, self.vd_values, self.vg_dur, self.vd_dur,
                self.app.stop_event, self.app.pause_event,
                vg_max=self.app.vg_max, vd_max=self.app.vd_max, curr_max=self.app.curr_max,
                rf_instr=self.app.exg_instr, pm_instr=self.app.nrx_instr,
                plot_target=plot_target
            )
            worker.app = self.app

            worker.plot_data_signal.connect(self.app.safe_update_plot)
            worker.plot_init_signal.connect(self.app.safe_add_plot_item)

            thread = QThread()
            thread.setObjectName(f"SweepThread-{rf_power}")
            worker.moveToThread(thread)

            # Connect signals
            worker.update_plot.connect(self.update_plot)
            worker.log_msg.connect(self.log_msg)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            # Qt event loop to wait for this specific sweep iteration
            loop = QEventLoop()

            def on_done():
                self.app.rf_control_screen.rf_output_off()
                loop.quit()
                # Safe to call plot after loop quit
                QTimer.singleShot(0, self.app.plot_pae_vs_powerin)


            worker.finished.connect(on_done)
            worker.plot_ready.connect(self.app.archive_plot_signal)

            thread.started.connect(worker.run)
            thread.start()
            self.log_msg.emit(f"Started thread: {thread.objectName()}")
            self.log_msg.emit("SweepWorker thread started")

            loop.exec()  #  This runs the event loop and waits for quit()
            thread.wait()

            if self.app.stop_event.is_set():
                self.log_msg.emit("Sweep interrupted. Exiting remaining steps.")
                break

        self.finished.emit()

class NGP800IVSweepApp(QWidget):
    update_plot = pyqtSignal(object, list, list)  # name, x, y
    reset_ui = pyqtSignal()
    rf_sweep_finished = pyqtSignal()
    archive_plot_signal = pyqtSignal(str)



    def __init__(self):
        super().__init__()
        self.setWindowTitle("RF_Power_Sweep")
        self.update_plot.connect(self.handle_update_plot)
        self.reset_ui.connect(self.handle_reset_ui)
        self.archive_plot_signal.connect(self.archive_current_plot)


        self.rf_plot_widgets = {}  # Dict to hold RF Power => PlotWidget
        self.rf_sweep_worker = None  # already there, just reusing


        self.stack = QStackedLayout()
        self.setLayout(self.stack)

        self.connect_screen = MultiInstrumentConnectScreen(self.on_all_connected)

        self.stack.addWidget(self.connect_screen)

        self.instrument = None
        self.exg_instr = None
        self.nrx_instr = None


        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_paused = False
        self.setup_records_ui()
 
    def archive_current_plot(self, rf_power_label):
        pass
    def safe_add_plot_item(self, plot_widget, plot_data_item):
        try:
            if plot_widget is not None and plot_data_item is not None:
                plot_widget.addItem(plot_data_item)
        except Exception as e:
            self.log(f"[ERROR] Failed to safely add plot item: {e}")


    def on_all_connected(self, ngp800, exg, nrx):
        self.instrument = ngp800
        self.exg_instr = exg
        self.nrx_instr = nrx
        self.nrx_instr_type = getattr(nrx, "device_type", "UNKNOWN")
        
        # Set RF control screen instrument before loading GUI
        self.rf_control_screen = RFControlScreen(self)
        self.rf_control_screen.set_instrument(self.exg_instr)
        

        QTimer.singleShot(4000, self.setup_config_ui)



    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_widget.append(f"[{timestamp}] {message}")

        if not hasattr(self, "first_gain_value"):
            self.first_gain_value = None

        if message.startswith("[RECORD]"):
            parts = message.replace("[RECORD]", "").strip().split(",")
            time_str = parts[0].strip()
            try:
                vg_str = parts[1].split("=")[1].strip()
                vd_str = parts[2].split("=")[1].strip()
                curr_str = parts[3].split("=")[1].split()[0].strip()

                vg = float(vg_str) if vg_str != "N/A" else 0.0
                vd = float(vd_str) if vd_str != "N/A" else 0.0
                curr = float(curr_str) if curr_str != "N/A" else 0.0
            except Exception as e:
                self.log(f"[ERROR] Failed to parse Vg/Vd/Current: {e}")
                return  # or set defaults

            freq = parts[4].split("=")[1] if len(parts) > 4 else "N/A"
            power_out = parts[6].split("=")[1] if len(parts) > 6 else "N/A"
            power_in = parts[5].split("=")[1] if len(parts) > 5 else "N/A"

            try:
                pout_dbm = float(power_out)
                pin_dbm = float(power_in)

                # Adjusted values
                pin_actual = pin_dbm - self.input_loss_db + self.input_gain_db
                pout_actual = pout_dbm + self.output_loss_db

                # Convert to Watts
                pout_w = 10 ** (pout_actual / 10) * 0.001
                pin_w = 10 ** (pin_actual / 10) * 0.001

                pin_mw_str = f"{pin_w * 1000:.8f}"
                pout_mw_str = f"{pout_w * 1000:.8f}"


                pin_w_str = f"{pin_w:.8f}"
                pout_w_str = f"{pout_w:.8f}"


                denominator = vd * curr
                pae = (pout_w - pin_w) * 100 / denominator if denominator > 0 else -1
                gain = pout_actual - pin_actual

                if self.first_gain_value is None and isinstance(gain, (int, float)):
                    self.first_gain_value = gain

                if self.first_gain_value is not None and isinstance(gain, (int, float)):
                    compression = self.first_gain_value - gain
                    compression_str = f"{compression:.8f}"
                else:
                    compression_str = "N/A"


                # String formats
                pin_actual_str = f"{pin_actual:.8f}"
                pout_actual_str = f"{pout_actual:.8f}"
                pae_str = f"{pae:.8f}"
                gain_str = f"{gain:.8f}"
            except:
                pin_actual_str = pout_actual_str = pae_str = gain_str = compression_str = "N/A"
                pin_mw_str = pout_mw_str = "N/A"

            row = self.records_table.rowCount()
            self.records_table.insertRow(row)
            self.records_table.setItem(row, 0, QTableWidgetItem(time_str))
            self.records_table.setItem(row, 1, QTableWidgetItem(f"{vg}"))
            self.records_table.setItem(row, 2, QTableWidgetItem(f"{vd}"))
            self.records_table.setItem(row, 3, QTableWidgetItem(f"{curr:.8f}"))
            self.records_table.setItem(row, 4, QTableWidgetItem(freq))
            self.records_table.setItem(row, 5, QTableWidgetItem(power_in))
            self.records_table.setItem(row, 6, QTableWidgetItem(power_out))
            self.records_table.setItem(row, 7, QTableWidgetItem(pin_actual_str))   # PowerIN (actual)
            self.records_table.setItem(row, 8, QTableWidgetItem(pout_actual_str))  # PowerOUT (actual)
            self.records_table.setItem(row, 9, QTableWidgetItem(pin_mw_str))        # NEW: Pin_actual (mW)
            self.records_table.setItem(row, 10, QTableWidgetItem(pout_mw_str))      # NEW: Pout_actual (mW)
            self.records_table.setItem(row, 11, QTableWidgetItem(gain_str))        # GAIN (dB)
            self.records_table.setItem(row, 12, QTableWidgetItem(compression_str)) # Compression
            self.records_table.setItem(row, 13, QTableWidgetItem(pae_str))         # PAE (%)


    def handle_update_plot(self, plot_data, x_vals, y_vals):
        pass

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


        self.records_table = QTableWidget()
        self.records_table.setColumnCount(14)
        self.records_table.setHorizontalHeaderLabels([
            "Timestamp", "Vgate (V)", "Vdrain (V)", "Current (A)",
            "RF Freq (Hz)", "PowerIN (dBm)", "PowerOUT (dBm)",
            "PowerIN (actual)", "PowerOUT (actual)",
            "Pin_actual (mW)", "Pout_actual (mW)",
            "GAIN (dB)", "Compression","PAE (%)"
        ])


        header = self.records_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)



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
        main_layout = QHBoxLayout()
        self.config_widget.setLayout(main_layout)
        

        # === Center Panel for Config UI ===
        center_widget = QWidget()
        center_layout = QVBoxLayout()
        center_widget.setLayout(center_layout)
        main_layout.addWidget(center_widget, stretch=8)  # ~80% width

        # Replace original layout reference with center_layout
        layout = center_layout

        self.stack.addWidget(self.config_widget)
        self.stack.setCurrentWidget(self.config_widget)

        rf_layout = QGridLayout()

        rf_layout.addWidget(QLabel("RF Frequency:"), 0, 0)
        self.rf_freq_input = self.rf_control_screen.freq_input
        self.rf_freq_unit = self.rf_control_screen.freq_unit
        rf_layout.addWidget(self.rf_freq_input, 0, 1)
        rf_layout.addWidget(self.rf_freq_unit, 0, 2)

        rf_layout.addWidget(QLabel("RF Power Start:"), 1, 0)
        rf_layout.addWidget(self.rf_control_screen.power_start, 1, 1)
        rf_layout.addWidget(QLabel("Step:"), 1, 2)
        rf_layout.addWidget(self.rf_control_screen.power_step, 1, 3)

        rf_layout.addWidget(QLabel("End:"), 2, 0)
        rf_layout.addWidget(self.rf_control_screen.power_end, 2, 1)
        rf_layout.addWidget(QLabel("Duration (s):"), 2, 2)
        rf_layout.addWidget(self.rf_control_screen.power_dur, 2, 3)

        layout.addLayout(rf_layout)

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

        grid = QGridLayout()
    
        # RF path calibration inputs
        grid.addWidget(QLabel("Input Loss (dB):"), 0, 0)
        self.input_loss_input = QLineEdit("0")
        grid.addWidget(self.input_loss_input, 0, 1)

        grid.addWidget(QLabel("Input Gain (dB):"), 0, 2)
        self.input_gain_input = QLineEdit("0")
        grid.addWidget(self.input_gain_input, 0, 3)

        grid.addWidget(QLabel("Output Loss (dB):"), 0, 4)
        self.output_loss_input = QLineEdit("0")
        grid.addWidget(self.output_loss_input, 0, 5)


        # Single Vd input
        grid.addWidget(QLabel("Vdrain (V):"), 1, 0)
        self.vd_input = QLineEdit()

        self.vd_input.setPlaceholderText("e.g. 5")
        grid.addWidget(self.vd_input, 1, 1)

        # Single Vg input
        grid.addWidget(QLabel("Vgate (V):"), 2, 0)
        self.vg_input = QLineEdit()
        self.vg_input.setPlaceholderText("e.g. 2")
        grid.addWidget(self.vg_input, 2, 1)

        layout.addLayout(grid)

        # Buttons layout
        btn_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Sweep")
        self.pause_resume_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")

        self.emergency_stop_button = QPushButton("EMERGENCY STOP")
        self.emergency_stop_button.setStyleSheet(
            "background-color: red; color: white; font-weight: bold; font-size: 14px;"
        )
        self.emergency_stop_button.clicked.connect(self.emergency_stop_all)


        self.pause_resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        self.set_vg_vd_button = QPushButton("Set Vg & Vd")
        self.set_vg_vd_button.clicked.connect(self.set_vg_vd_once)
        btn_layout.addWidget(self.set_vg_vd_button)


        btn_layout.addWidget(self.run_button)
        btn_layout.addWidget(self.pause_resume_button)
        btn_layout.addWidget(self.stop_button)
        btn_layout.addWidget(self.emergency_stop_button)

        layout.addLayout(btn_layout)

        # --- New tab widget to store past RF sweep plots ---
        
        self.history_tabs = QTabWidget()
        layout.addWidget(QLabel("All RF Power Sweep Plots: "))
        layout.addWidget(self.history_tabs)


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


    def emergency_stop_all(self):
        self.log("EMERGENCY STOP: Aborting sweep and turning off all devices.")
        if self.rf_control_screen:
            self.rf_control_screen.rf_output_off()

        self.stop_event.set()  # <-- CRUCIAL to stop SweepWorker.run()
        try:
            if self.instrument:
                try:
                    if self.instrument:
                        for ch in range(1, 5):
                            self.instrument.write(f"INST:NSEL {ch}")
                            self.instrument.write("OUTP OFF")
                        self.log("All NGP800 channels turned OFF.")
                except Exception as e:
                    self.log(f"Failed to turn off NGP800 channels: {e}")

            if self.exg_instr:
                self.exg_instr.write("OUTP OFF")
            if self.nrx_instr:
                self.nrx_instr.write("OUTP OFF")
            self.log("Emergency stop complete: All outputs OFF and sweep aborted.")
        except Exception as e:
            self.log(f"Emergency stop error: {e}")

    def set_vg_vd_once(self):
        try:
            vg = float(self.vg_input.text())
            vd = float(self.vd_input.text())
            vg_chan = self.vg_chan_combo.currentText().replace("CH", "")
            vd_chan = self.vd_chan_combo.currentText().replace("CH", "")

            # 💡 Check limits before applying voltages
            if self.vg_max is not None and vg > self.vg_max:
                QMessageBox.warning(self, "Limit Error", "Vgate exceeds maximum limit.")
                return
            if self.vd_max is not None and vd > self.vd_max:
                QMessageBox.warning(self, "Limit Error", "Vdrain exceeds maximum limit.")
                return

            if self.instrument:
                # Set Vgate
                self.instrument.write(f"INST:NSEL {vg_chan}")
                self.instrument.write(f"VOLT {vg}")
                self.instrument.write("OUTP ON")
                self.log(f"Set Vgate to {vg} V on channel {vg_chan}")

                # Set Vdrain
                self.instrument.write(f"INST:NSEL {vd_chan}")
                self.instrument.write(f"VOLT {vd}")
                self.instrument.write("OUTP ON")
                self.log(f"Set Vdrain to {vd} V on channel {vd_chan}")
        except Exception as e:
            QMessageBox.warning(self, "Set Error", f"Failed to set voltages: {e}")


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
        if self.rf_control_screen:
            self.rf_control_screen.rf_output_off()


        try:
            # Turn off all channels (1 to 4)
            for ch in range(1, 5):
                self.instrument.write(f"INST:NSEL {ch}")
                self.instrument.write("OUTP OFF")
            self.log("All channels turned OFF.")
        except Exception as e:
            self.log(f"Failed to turn off channels: {e}")
            
        self.reset_ui.emit()


    def run_sweep_threaded(self):
        try:
            vg_value = float(self.vg_input.text())
            vd_value = float(self.vd_input.text())
            self.latest_vg = vg_value
            self.latest_vd = vd_value

            vg_values = [vg_value]
            vd_values = [vd_value]
            vg_dur = 1.0  # use a fixed or configurable duration
            vd_dur = 1.0


            # RF Power Sweep setup
            rf_start, rf_step, rf_end, rf_dur = self.rf_control_screen.get_rf_power_sweep_values()
            try:
                freq = float(self.rf_freq_input.text())
                unit = self.rf_freq_unit.currentText()
                mult = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
                freq_hz = freq * mult[unit]
                self.exg_instr.write(f"FREQ {freq_hz} Hz")
                self.log(f"RF Frequency set to {freq_hz} Hz")
            except Exception as e:
                QMessageBox.warning(self, "RF Frequency Error", f"Failed to set frequency: {e}")
                return

            if None in [rf_start, rf_step, rf_end, rf_dur]:
                QMessageBox.warning(self, "Input Error", "Invalid RF sweep values.")
                return
            rf_powers = self.frange(rf_start, rf_end, rf_step)

            # RF Power Sweep Values
            try:
                rf_start = float(self.rf_control_screen.power_start.text())
                rf_step = float(self.rf_control_screen.power_step.text())
                rf_end = float(self.rf_control_screen.power_end.text())
                rf_dur = float(self.rf_control_screen.power_dur.text())
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Please enter valid RF power sweep values.")
                return

            rf_powers = self.frange(rf_start, rf_end, rf_step)


        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numeric values for all fields.")
            return

        try:
            self.input_loss_db = float(self.input_loss_input.text())
            self.input_gain_db = float(self.input_gain_input.text())
            self.output_loss_db = float(self.output_loss_input.text())
        except ValueError:
            QMessageBox.warning(self, "Calibration Error", "Please enter valid numeric values for input/output losses/gains.")
            return

        # Clear previous records
        self.records_table.setRowCount(0)
        self.first_gain_value = None  # Reset first gain for new compression calculation


        self.stop_event.clear()
        self.pause_event.clear()
        self.is_paused = False
        self.pause_resume_button.setText("Pause")
        self.pause_resume_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.run_button.setEnabled(False)

        vg_chan = self.vg_chan_combo.currentText().replace("CH", "")
        vd_chan = self.vd_chan_combo.currentText().replace("CH", "")


        self.rf_plot_widgets.clear()
        self.history_tabs.clear()

        # === Create single tab for combined plot (PowerOUT, PAE, GAIN vs PowerIN) ===
        self.combined_plot_tab = QWidget()
        combined_layout = QVBoxLayout(self.combined_plot_tab)

        if hasattr(self, "combined_plot_widget"):
            self.combined_plot_widget.clear()

        self.combined_plot_widget = pg.PlotWidget(title="PAE, PowerOUT, and GAIN vs PowerIN")
        self.combined_plot_widget.setLabel("bottom", "PowerIN (actual)")
        self.combined_plot_widget.setLabel("left", "PowerOUT (dBm), PAE (%)")
        self.combined_plot_widget.showGrid(x=True, y=True)
        self.combined_plot_widget.addLegend()

        combined_layout.addWidget(self.combined_plot_widget)
        self.history_tabs.addTab(self.combined_plot_tab, "Combined Graph")

        # Additional plot tabs: PAE vs Pin, Pout_actual vs Pin_actual, Gain vs Pin
        self.pae_plot_widget = pg.PlotWidget(title="PAE vs PowerIN")
        self.pae_plot_widget.setLabel("bottom", "PowerIN (actual)")
        self.pae_plot_widget.setLabel("left", "PAE (%)")
        self.pae_plot_widget.showGrid(x=True, y=True)
        self.pae_plot_tab = QWidget()
        pae_layout = QVBoxLayout(self.pae_plot_tab)
        pae_layout.addWidget(self.pae_plot_widget)
        self.history_tabs.addTab(self.pae_plot_tab, "PAE vs Pin")

        self.pout_plot_widget = pg.PlotWidget(title="PowerOUT (actual) vs PowerIN (actual)")
        self.pout_plot_widget.setLabel("bottom", "PowerIN (actual)")
        self.pout_plot_widget.setLabel("left", "PowerOUT (actual)")
        self.pout_plot_widget.showGrid(x=True, y=True)
        self.pout_plot_tab = QWidget()
        pout_layout = QVBoxLayout(self.pout_plot_tab)
        pout_layout.addWidget(self.pout_plot_widget)
        self.history_tabs.addTab(self.pout_plot_tab, "Pout vs Pinactual")

        self.gain_plot_widget = pg.PlotWidget(title="GAIN vs PowerIN")
        self.gain_plot_widget.setLabel("bottom", "PowerIN (actual)")
        self.gain_plot_widget.setLabel("left", "GAIN (dB)")
        self.gain_plot_widget.showGrid(x=True, y=True)
        self.gain_plot_tab = QWidget()
        gain_layout = QVBoxLayout(self.gain_plot_tab)
        gain_layout.addWidget(self.gain_plot_widget)
        self.history_tabs.addTab(self.gain_plot_tab, "GAIN vs Pin")

        self.rf_sweep_thread = QThread()
        self.rf_sweep_worker = RFSweepWorker(
            self, rf_powers, vg_chan, vd_chan, vg_values, vd_values, vg_dur, vd_dur
        )
        self.rf_sweep_worker.moveToThread(self.rf_sweep_thread)

        self.rf_sweep_worker.finished.connect(self.rf_sweep_thread.quit)
        self.rf_sweep_worker.finished.connect(self.rf_sweep_worker.deleteLater)
        self.rf_sweep_thread.finished.connect(self.rf_sweep_thread.deleteLater)
        self.rf_sweep_worker.log_msg.connect(self.log)
        self.rf_sweep_worker.update_plot.connect(self.handle_update_plot)

        self.rf_sweep_thread.started.connect(self.rf_sweep_worker.run)


        self.rf_sweep_thread.start()

    def safe_update_plot(self, plot_widget, x_vals, y_vals):
        try:
            if plot_widget is not None:
                items = plot_widget.listDataItems()
                if items:
                    # Always update the last added plot line
                    items[-1].setData(x_vals, y_vals)
        except Exception as e:
            self.log(f"[ERROR] Failed to update plot safely: {e}")


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

    def plot_pae_vs_powerin(self):
        pin_vals, pout_vals, gain_vals, pae_vals = [], [], [], []

        for row in range(self.records_table.rowCount()):
            try:
                pin = float(self.records_table.item(row, 7).text())  # PowerIN actual
                pout = float(self.records_table.item(row, 8).text()) # PowerOUT actual
                gain = float(self.records_table.item(row, 11).text())
                pae = float(self.records_table.item(row, 13).text())


                pin_vals.append(pin)
                pout_vals.append(pout)
                gain_vals.append(gain)
                pae_vals.append(pae)
            except Exception:
                continue

        if not pin_vals:
            self.log("No valid data found for plotting combined graph.")
            return

        # Clear and set up single Y-axis plot
        self.combined_plot_widget.clear()
        self.combined_plot_widget.setTitle("PAE, PowerOUT, GAIN vs PowerIN")
        self.combined_plot_widget.setLabel("bottom", "PowerIN (actual)")
        self.combined_plot_widget.setLabel("left", "Value (dBm / %)")
        self.combined_plot_widget.addLegend()
        self.combined_plot_widget.showGrid(x=True, y=True)

        # Plot all 3 on the same axis
        self.combined_plot_widget.plot(pin_vals, pout_vals, pen=pg.mkPen("b", width=2), name="PowerOUT (dBm)", symbol="o",symbolSize=6)
        self.combined_plot_widget.plot(pin_vals, pae_vals, pen=pg.mkPen("g", width=2), name="PAE (%)", symbol="x",symbolSize=6)
        self.combined_plot_widget.plot(pin_vals, gain_vals, pen=pg.mkPen("r", width=2), name="GAIN", symbol="t",symbolSize=6)

        self.log("Plotted combined graph: PowerOUT, PAE, and GAIN vs PowerIN")

        # Plot PAE vs PowerIN
        self.pae_plot_widget.clear()
        self.pae_plot_widget.plot(pin_vals, pae_vals, pen=pg.mkPen("m", width=2), symbol="x", name="PAE",symbolSize=6)

        # Plot PowerOUT vs PowerIN
        self.pout_plot_widget.clear()
        self.pout_plot_widget.plot(pin_vals, pout_vals, pen=pg.mkPen("c", width=2), symbol="o", name="Pout_actual",symbolSize=6)

        # Plot GAIN vs PowerIN
        self.gain_plot_widget.clear()
        self.gain_plot_widget.plot(pin_vals, gain_vals, pen=pg.mkPen("y", width=2), symbol="t", name="Gain",symbolSize=6)


    def closeEvent(self, event):
        self.log("Closing application: performing full emergency shutdown.")
        self.stop_event.set()

        try:
            if self.rf_control_screen:
                self.rf_control_screen.rf_output_off()
            if self.instrument:
                for ch in range(1, 5):
                    self.instrument.write(f"INST:NSEL {ch}")
                    self.instrument.write("OUTP OFF")
                self.log("NGP800: All channels turned OFF.")
            if self.exg_instr:
                self.exg_instr.write("OUTP OFF")
                self.log("EXG Signal Generator: Output turned OFF.")
            if self.nrx_instr:
                self.nrx_instr.write("OUTP OFF")
                self.log("NRX Power Meter: Output turned OFF.")
        except Exception as e:
            self.log(f"[ERROR] Exception during close shutdown: {e}")

        try:
            if hasattr(self, "rf_sweep_thread") and self.rf_sweep_thread:
                if self.rf_sweep_thread.isRunning():
                    self.log("Waiting for RF sweep thread to quit...")
                    self.rf_sweep_thread.quit()
                    self.rf_sweep_thread.wait()  # <-- make sure thread fully exits
                self.rf_sweep_worker = None
                self.rf_sweep_thread = None
        except Exception as e:
            self.log(f"[ERROR] Exception while terminating RF sweep thread: {e}")

    
        self.log("Application closed safely. All outputs OFF.")
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = NGP800IVSweepApp()
    window.resize(850, 600)
    window.show()
    try:
        sys.exit(app.exec())
    finally:
        del window


