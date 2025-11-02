import sys
import json
import pyvisa
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QComboBox, QTextEdit, QMessageBox,
    QStackedLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from pyqtgraph import PlotWidget, plot, mkPen
import pyqtgraph as pg

class NGP800Controller(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rohde & Schwarz NGP800 Control")
        self.resize(800, 600)

        self.instr = None
        self.max_limits = {}  # {channel: (max_voltage, max_current_mA)}
        self.plot_widgets = []
        self.data_lines = []
        self.voltage_history = {ch: [] for ch in range(1, 5)}
        self.current_history = {ch: [] for ch in range(1, 5)}
        self.time_data = []
        self.time_counter = 0

        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        self.status.setFixedHeight(100)

        self.stack = QStackedLayout()
        self.layout.addLayout(self.stack)
        self.layout.addWidget(self.status)

        self.init_connect_screen()
        self.init_limits_screen()
        self.init_control_screen()
        self.init_monitor_screen()

        self.stack.setCurrentWidget(self.connect_widget)

    def log(self, msg):
        self.status.append(msg)

    def init_connect_screen(self):
        self.connect_widget = QWidget()
        layout = QVBoxLayout()

        self.connect_status_label = QLabel("Click Connect to find NGP800")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.try_connect)

        layout.addWidget(self.connect_status_label)
        layout.addWidget(self.connect_button)
        layout.addStretch()

        self.connect_widget.setLayout(layout)
        self.stack.addWidget(self.connect_widget)

    def try_connect(self):
        self.log("Searching for NGP800...")
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.log(f"Available VISA resources: {resources}")
            for res in resources:
                if "USB" in res or "ASRL" in res:
                    try:
                        instr = rm.open_resource(res)
                        idn = instr.query("*IDN?")
                        if "NGP800" in idn or "ROHDE" in idn.upper():
                            self.instr = instr
                            self.log(f"Connected to: {idn.strip()}")
                            self.connect_status_label.setText(f"Connected to: {idn.strip()}")
                            self.stack.setCurrentWidget(self.limits_widget)
                            return
                    except Exception as e:
                        self.log(f"Could not open resource {res}: {e}")
            self.log("NGP800 not found. Please check connection.")
            QMessageBox.warning(self, "Connection Failed", "NGP800 not found. Please check connection.")
        except Exception as e:
            self.log(f"Error opening VISA: {e}")
            QMessageBox.critical(self, "VISA Error", str(e))

    def init_limits_screen(self):
        self.limits_widget = QWidget()
        layout = QVBoxLayout()

        self.limit_inputs = {}

        info_label = QLabel("Set max voltage (V) and current (mA) limits for each channel (max 200 W power):")
        layout.addWidget(info_label)

        for ch in range(1, 5):
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel(f"Channel {ch}:"))
            v_edit = QLineEdit()
            v_edit.setPlaceholderText("Max Voltage (V)")
            i_edit = QLineEdit()
            i_edit.setPlaceholderText("Max Current (mA)")
            hbox.addWidget(v_edit)
            hbox.addWidget(i_edit)
            self.limit_inputs[ch] = (v_edit, i_edit)
            layout.addLayout(hbox)

        # Buttons: Save Profile, Load Profile, Set Limits, Go to Control Screen
        btn_layout = QHBoxLayout()

        self.save_profile_btn = QPushButton("Save Profile")
        self.save_profile_btn.clicked.connect(self.save_profile)
        btn_layout.addWidget(self.save_profile_btn)

        self.load_profile_btn = QPushButton("Load Profile")
        self.load_profile_btn.clicked.connect(self.load_profile)
        btn_layout.addWidget(self.load_profile_btn)

        self.set_limits_button = QPushButton("Set Limits")
        self.set_limits_button.clicked.connect(self.set_limits_clicked)
        btn_layout.addWidget(self.set_limits_button)

        self.goto_control_button = QPushButton("Go to Control Screen")
        self.goto_control_button.clicked.connect(self.goto_control_screen)
        self.goto_control_button.setEnabled(False)  # Only enable after limits set
        btn_layout.addWidget(self.goto_control_button)

        layout.addLayout(btn_layout)
        layout.addStretch()

        self.limits_widget.setLayout(layout)
        self.stack.addWidget(self.limits_widget)

    def set_limits_clicked(self):
        MAX_POWER = 200.0
        self.max_limits.clear()
        try:
            for ch, (v_edit, i_edit) in self.limit_inputs.items():
                v_max = float(v_edit.text())
                i_max = float(i_edit.text())
                if v_max <= 0 or i_max <= 0:
                    raise ValueError(f"Channel {ch}: Voltage and current must be positive")
                power = v_max * (i_max / 1000.0)
                if power > MAX_POWER:
                    raise ValueError(f"Channel {ch}: Power {power:.2f} W exceeds max {MAX_POWER} W")
                # Apply limits to instrument
                self.instr.write(f"INST:NSEL {ch}")
                self.instr.write(f"VOLT {v_max}")
                self.instr.write(f"CURR {i_max / 1000.0}")
                self.instr.write("OUTP ON")
                self.max_limits[ch] = (v_max, i_max)
                self.log(f"Set limits for channel {ch}: {v_max} V, {i_max} mA ({power:.2f} W)")

            self.goto_control_button.setEnabled(True)
            QMessageBox.information(self, "Limits Set", "Channel limits set successfully! You can now proceed to Control Screen.")
        except Exception as e:
            QMessageBox.warning(self, "Invalid Input", str(e))
            self.log(f"Error setting limits: {e}")

    def goto_control_screen(self):
        if not self.max_limits:
            QMessageBox.warning(self, "Limits Not Set", "Please set valid limits before proceeding.")
            return
        self.stack.setCurrentWidget(self.control_widget)

    def init_control_screen(self):
        self.control_widget = QWidget()
        layout = QVBoxLayout()

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Voltage Control", "Current Control"])
        layout.addWidget(QLabel("Select mode:"))
        layout.addWidget(self.mode_combo)

        hbox_channel = QHBoxLayout()
        hbox_channel.addWidget(QLabel("Channel (1-4):"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems([str(i) for i in range(1, 5)])
        hbox_channel.addWidget(self.channel_combo)
        layout.addLayout(hbox_channel)

        hbox_value = QHBoxLayout()
        hbox_value.addWidget(QLabel("Value (V or mA):"))
        self.value_edit = QLineEdit()
        hbox_value.addWidget(self.value_edit)
        layout.addLayout(hbox_value)

        self.set_value_button = QPushButton("Set Value")
        self.set_value_button.clicked.connect(self.set_value_clicked)
        layout.addWidget(self.set_value_button)

        self.monitor_button = QPushButton("Start Live Monitoring")
        self.monitor_button.clicked.connect(lambda: self.stack.setCurrentWidget(self.monitor_widget))
        layout.addWidget(self.monitor_button)

        self.control_widget.setLayout(layout)
        self.stack.addWidget(self.control_widget)

    def set_value_clicked(self):
        try:
            ch = int(self.channel_combo.currentText())
            val = float(self.value_edit.text())
            mode = self.mode_combo.currentText()

            if ch not in self.max_limits:
                QMessageBox.warning(self, "Channel Error", f"Limits not set for channel {ch}.")
                return
            max_v, max_i = self.max_limits[ch]

            if mode == "Voltage Control":
                if val < 0 or val > max_v:
                    QMessageBox.warning(self, "Value Error", f"Voltage must be between 0 and {max_v} V")
                    return
                self.instr.write(f"INST:NSEL {ch}")
                self.instr.write(f"VOLT {val}")
                self.instr.write("OUTP ON")
                self.log(f"Voltage set to {val} V on channel {ch}")
            else:
                if val < 0 or val > max_i:
                    QMessageBox.warning(self, "Value Error", f"Current must be between 0 and {max_i} mA")
                    return
                self.instr.write(f"INST:NSEL {ch}")
                self.instr.write(f"CURR {val / 1000.0}")
                self.instr.write("OUTP ON")
                self.log(f"Current limit set to {val} mA on channel {ch}")

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.log(f"Error: {e}")

    def save_profile(self):
        profile = {}
        try:
            for ch, (v_edit, i_edit) in self.limit_inputs.items():
                v = v_edit.text()
                i = i_edit.text()
                if not v or not i:
                    raise ValueError(f"Channel {ch}: Voltage and Current cannot be empty")
                profile[ch] = {"voltage": float(v), "current": float(i)}
            filename, _ = QFileDialog.getSaveFileName(self, "Save Profile", "", "JSON Files (*.json)")
            if filename:
                with open(filename, 'w') as f:
                    json.dump(profile, f, indent=4)
                self.log(f"Profile saved to {filename}")
        except Exception as e:
            QMessageBox.warning(self, "Save Profile Error", str(e))

    def load_profile(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Profile", "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    profile = json.load(f)
                for ch, limits in profile.items():
                    ch = int(ch)
                    v_edit, i_edit = self.limit_inputs[ch]
                    v_edit.setText(str(limits.get("voltage", "")))
                    i_edit.setText(str(limits.get("current", "")))
                self.log(f"Profile loaded from {filename}")
            except Exception as e:
                QMessageBox.warning(self, "Load Profile Error", str(e))

    def init_monitor_screen(self):
        self.monitor_widget = QWidget()
        layout = QVBoxLayout()

        # Back button
        back_btn = QPushButton("Back to Control Screen")
        back_btn.clicked.connect(lambda: self.stack.setCurrentWidget(self.control_widget))
        layout.addWidget(back_btn)

        # Horizontal layout for plots
        plots_layout = QHBoxLayout()

        # Left: Voltage plots stacked vertically
        volt_layout = QVBoxLayout()
        self.volt_plots = []
        self.volt_curves = []
        for ch in range(1, 5):
            pw = PlotWidget(title=f"Channel {ch} Voltage (V)")
            pw.setYRange(0, 70)
            pw.showGrid(x=True, y=True)
            self.volt_plots.append(pw)
            curve = pw.plot(pen=mkPen('r', width=2))
            self.volt_curves.append(curve)
            volt_layout.addWidget(pw)

        # Right: Current plots stacked vertically
        curr_layout = QVBoxLayout()
        self.curr_plots = []
        self.curr_curves = []
        for ch in range(1, 5):
            pw = PlotWidget(title=f"Channel {ch} Current (mA)")
            pw.setYRange(0, 11000)
            pw.showGrid(x=True, y=True)
            self.curr_plots.append(pw)
            curve = pw.plot(pen=mkPen('b', width=2))
            self.curr_curves.append(curve)
            curr_layout.addWidget(pw)

        plots_layout.addLayout(volt_layout)
        plots_layout.addLayout(curr_layout)

        layout.addLayout(plots_layout)
        self.monitor_widget.setLayout(layout)
        self.stack.addWidget(self.monitor_widget)

        # Initialize data and timer as before...
        self.data_len = 60
        self.time_data = list(range(-self.data_len+1, 1))

        self.volt_data = [[0]*self.data_len for _ in range(4)]
        self.curr_data = [[0]*self.data_len for _ in range(4)]

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(1000)

    def update_plots(self):
        if not self.instr:
            return

        for ch in range(1, 5):
            try:
                self.instr.write(f"INST:NSEL {ch}")
                volt = float(self.instr.query("MEAS:VOLT?"))
                curr = float(self.instr.query("MEAS:CURR?")) * 1000  # convert A to mA

                self.volt_data[ch-1].append(volt)
                self.volt_data[ch-1].pop(0)

                self.curr_data[ch-1].append(curr)
                self.curr_data[ch-1].pop(0)

                self.volt_curves[ch-1].setData(self.time_data, self.volt_data[ch-1])
                self.curr_curves[ch-1].setData(self.time_data, self.curr_data[ch-1])

            except Exception as e:
                self.log(f"Error updating channel {ch} data: {e}")

def main():
    app = QApplication(sys.argv)
    window = NGP800Controller()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
