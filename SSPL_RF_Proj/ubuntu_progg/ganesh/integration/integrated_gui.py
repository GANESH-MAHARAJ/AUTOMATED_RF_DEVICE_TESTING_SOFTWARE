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
from i_power_meter_gui import ControlScreen as PowerControlScreen
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
        self.log_msg.emit("SweepWorker started")
        
        self.log_msg.emit(f"Running in thread: {threading.current_thread().name}")

        try:
            

            self.log_msg.emit(f"Stop event at start: {self.stop_event.is_set()}")

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


                plot_data = pg.PlotDataItem(
                    x=[], y=[],
                    pen=pg.mkPen(QColor(*[random.randint(0, 255) for _ in range(3)]), width=2),
                    name=f"Vg={vg}V"
                )

                if self.plot_target:
                    self.plot_init_signal.emit(self.plot_target, plot_data)


                currents = []


                for i, vd in enumerate(self.vd_values):
                    if self.stop_event.is_set():
                        self.log_msg.emit("Sweep stopped by user during Vdrain sweep.")
                        break

                    while self.pause_event.is_set():
                        if self.stop_event.is_set():
                            self.log_msg.emit("Sweep stopped while paused.")
                            return
                        time.sleep(0.1)

                    if self.stop_event.is_set():
                        self.log_msg.emit("Sweep stopped by user.")
                        break

                    self.log_msg.emit(f"Setting Vdrain to {vd} V on channel {self.vd_chan}")
                    self.instrument.write(f"INST:NSEL {self.vd_chan}")
                    self.instrument.write(f"VOLT {vd}")
                    self.instrument.write(f"OUTP ON")

                    # Replace blocking sleep with interruptible version
                    wait_time = 0
                    while wait_time < self.vd_dur:
                        if self.stop_event.is_set():
                            self.log_msg.emit("Sweep stopped during Vdrain duration wait.")
                            return
                        time.sleep(0.1)
                        wait_time += 0.1


                    self.instrument.write("MEAS:CURR?")
                    current = float(self.instrument.read())
                    rf_freq = None
                    live_power = None

                    if self.rf_instr:
                        try:
                            rf_freq = float(self.rf_instr.query("FREQ?").strip())
                            power_in = None
                            try:
                                power_in = float(self.rf_instr.query("POW?").strip())
                            except:
                                power_in = None

                        except:
                            rf_freq = None

                    if self.pm_instr:
                        try:
                            time.sleep(0.5)
                            if hasattr(self.pm_instr, "device_type") and self.pm_instr.device_type == "NRP2":
                                response = self.pm_instr.query("READ?").strip()
                            else:
                                response = self.pm_instr.query("MEAS:POW?").strip()
                            live_power = float(response)

                        except ValueError:
                            self.log_msg.emit(f"[WARNING] Could not parse power value: {response}")
                            live_power = None
                        except Exception as e:
                            self.log_msg.emit(f"[WARNING] Power read error: {e}")
                            live_power = None


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

                    self.log_msg.emit(f"[RECORD] {timestamp}, Vg={vg}, Vd={vd}, I={current:.6f} A, Freq={rf_freq}, PowerIN={power_in}, Power={live_power}")

                    # Signal used for record logging - handled via log_msg for simplicity

                    record_signal = pyqtSignal(str, float, float, float)
                    self.log_msg.emit(f"Measured current: {current:.6f} A")
                    currents.append(current)
                    if self.plot_target:
                        self.plot_data_signal.emit(self.plot_target, self.vd_values[:i+1], currents)

                self._plot_items.append(plot_data)

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
        
        self.plot_ready.emit(f"RF {self.rf_instr.query('POW?').strip()} dBm")
        

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
            worker.plot_data_signal.connect(self.app.safe_update_plot)
            worker.plot_init_signal.connect(self.app.safe_add_plot_item)



            thread = QThread()
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
                loop.quit()  # ✅ Resume the loop when worker is done

            worker.finished.connect(on_done)
            worker.plot_ready.connect(self.app.archive_plot_signal)

            thread.started.connect(worker.run)
            thread.start()
            self.log_msg.emit("SweepWorker thread started")
            loop.exec()  # ✅ This runs the event loop and waits for quit()

            # Archive the plot BEFORE any items are cleared or reused
            # self.app.archive_plot_signal.emit(f"RF {rf_power} dBm")


        self.finished.emit()


class NGP800IVSweepApp(QWidget):
    update_plot = pyqtSignal(object, list, list)  # name, x, y
    reset_ui = pyqtSignal()
    rf_sweep_finished = pyqtSignal()
    archive_plot_signal = pyqtSignal(str)


    def __init__(self):
        super().__init__()
        self.setWindowTitle("FULL Automation")
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
        
        self.setup_config_ui()



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
                return

            freq = parts[4].split("=")[1] if len(parts) > 4 else "N/A"
            power_out = parts[6].split("=")[1] if len(parts) > 6 else "N/A"
            power_in = parts[5].split("=")[1] if len(parts) > 5 else "N/A"

            try:
                pout_dbm = float(power_out)
                pin_dbm = float(power_in)

                pin_actual = pin_dbm - self.input_loss_db + self.input_gain_db
                pout_actual = pout_dbm + self.output_loss_db

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
            self.records_table.setItem(row, 7, QTableWidgetItem(pin_actual_str))
            self.records_table.setItem(row, 8, QTableWidgetItem(pout_actual_str))
            self.records_table.setItem(row, 9, QTableWidgetItem(pin_mw_str))
            self.records_table.setItem(row, 10, QTableWidgetItem(pout_mw_str))
            self.records_table.setItem(row, 11, QTableWidgetItem(gain_str))
            self.records_table.setItem(row, 12, QTableWidgetItem(compression_str))
            self.records_table.setItem(row, 13, QTableWidgetItem(pae_str))



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
            "GAIN (dB)", "Compression", "PAE (%)"
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

        # --- RF path calibration inputs ---
        rf_calib_layout = QGridLayout()
        rf_calib_layout.addWidget(QLabel("Input Loss (dB):"), 0, 0)
        self.input_loss_input = QLineEdit("0")
        rf_calib_layout.addWidget(self.input_loss_input, 0, 1)

        rf_calib_layout.addWidget(QLabel("Input Gain (dB):"), 0, 2)
        self.input_gain_input = QLineEdit("0")
        rf_calib_layout.addWidget(self.input_gain_input, 0, 3)

        rf_calib_layout.addWidget(QLabel("Output Loss (dB):"), 0, 4)
        self.output_loss_input = QLineEdit("0")
        rf_calib_layout.addWidget(self.output_loss_input, 0, 5)

        layout.addLayout(rf_calib_layout)


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

        self.emergency_stop_button = QPushButton("EMERGENCY STOP")
        self.emergency_stop_button.setStyleSheet(
            "background-color: red; color: white; font-weight: bold; font-size: 14px;"
        )
        self.emergency_stop_button.clicked.connect(self.emergency_stop_all)


        self.pause_resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)


        btn_layout.addWidget(self.run_button)
        btn_layout.addWidget(self.pause_resume_button)
        btn_layout.addWidget(self.stop_button)
        btn_layout.addWidget(self.emergency_stop_button)


        layout.addLayout(btn_layout)

        

        # --- New tab widget to store past RF sweep plots ---
        
        self.history_tabs = QTabWidget()
        layout.addWidget(QLabel("All RF Power Sweep Plots: (ID vs VD)"))
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

        # Connect Set Limits button
        self.set_limits_button.clicked.connect(self.set_limits)

    def emergency_stop_all(self):
        self.log("EMERGENCY STOP: Aborting sweep and turning off all devices.")
        if self.rf_control_screen:
            self.rf_control_screen.rf_output_off()

        self.stop_event.set()  # <-- CRUCIAL to stop SweepWorker.run()
        try:
            if self.instrument:
                for ch in range(1, 5):
                    self.instrument.write(f"INST:NSEL {ch}")
                    self.instrument.write("OUTP OFF")
            if self.exg_instr:
                self.exg_instr.write("OUTP OFF")
            if self.nrx_instr:
                self.nrx_instr.write("OUTP OFF")
            self.log("Emergency stop complete: All outputs OFF and sweep aborted.")
        except Exception as e:
            self.log(f"Emergency stop error: {e}")

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
            # Validate inputs
            vg_start = float(self.vg_start.text())
            vg_step = float(self.vg_step.text())
            vg_end = float(self.vg_end.text())
            vg_dur = float(self.vg_dur.text())

            vd_start = float(self.vd_start.text())
            vd_step = float(self.vd_step.text())
            vd_end = float(self.vd_end.text())
            vd_dur = float(self.vd_dur.text())

            # RF Power Sweep setup
            rf_start, rf_step, rf_end, rf_dur = self.rf_control_screen.get_rf_power_sweep_values()
            try:
                freq = float(self.rf_freq_input.text())
                unit = self.rf_freq_unit.currentText()
                mult = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
                freq_hz = freq * mult[unit]
                self.exg_instr.write(f"FREQ {freq_hz} Hz")
                self.log(f"RF Frequency set to {freq_hz} Hz")

                # RF Frequency set — now assign RF path losses/gains
                try:
                    self.input_loss_db = float(self.input_loss_input.text())
                    self.input_gain_db = float(self.input_gain_input.text())
                    self.output_loss_db = float(self.output_loss_input.text())
                except ValueError:
                    QMessageBox.warning(self, "Calibration Error", "Please enter valid numeric values for input/output losses/gains.")
                    return

                if self.nrx_instr:
                    try:
                        self.nrx_instr.write(f"SENS:FREQ {freq_hz} Hz")
                        self.log(f"Power Meter Frequency set to {freq_hz} Hz")
                    except Exception as e:
                        self.log(f"[WARNING] Failed to set power meter frequency: {e}")

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

        # self.plot_widget.clear()
        # self.plot_widget.addLegend()

        self.rf_plot_widgets.clear()
        self.history_tabs.clear()

        for rf_power in rf_powers:
            

            tab = QWidget()
            layout = QVBoxLayout(tab)
            plot = pg.PlotWidget()
            plot.setLabel('left', 'Drain Current (A)')
            plot.setLabel('bottom', 'Vdrain (V)')
            plot.addLegend()
            layout.addWidget(plot)

            self.history_tabs.addTab(tab, f"RF {rf_power} dBm")
            self.rf_plot_widgets[rf_power] = plot

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
        # self.rf_sweep_worker.plot_data_signal.connect(self.safe_update_plot)

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


    def closeEvent(self, event):
        # Stop any running sweep thread
        self.stop_event.set()

        # Turn off NGP800 channels
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
