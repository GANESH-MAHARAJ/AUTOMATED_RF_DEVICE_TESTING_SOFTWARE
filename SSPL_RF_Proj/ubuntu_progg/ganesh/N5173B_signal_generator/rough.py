import sys
import pyvisa
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton,
    QComboBox, QLineEdit, QHBoxLayout, QMessageBox, QStackedLayout
)
from PyQt6.QtCore import Qt

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(500, 300)
        self.setWindowTitle("EXG Signal Generator Controller")
        self.instr = None
        self.freq_limit = None
        self.power_limit = None

        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)

        self.connect_screen = ConnectScreen(self)
        self.limits_screen = LimitsScreen(self)
        self.control_screen = ControlScreen(self)

        self.stacked_layout.addWidget(self.connect_screen)
        self.stacked_layout.addWidget(self.limits_screen)
        self.stacked_layout.addWidget(self.control_screen)

        self.stacked_layout.setCurrentWidget(self.connect_screen)

    def instrument_found(self, instrument):
        self.instr = instrument
        self.limits_screen.set_instrument(instrument)
        self.stacked_layout.setCurrentWidget(self.limits_screen)

    def limits_set(self, freq_limit, power_limit):
        self.freq_limit = freq_limit
        self.power_limit = power_limit
        self.control_screen.set_instrument(self.instr)
        self.control_screen.set_limits(freq_limit, power_limit)
        self.stacked_layout.setCurrentWidget(self.control_screen)



class ConnectScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()

        self.status_label = QLabel("Click 'Connect' to find instrument")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.find_instrument)

        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.connect_button)

        self.setLayout(self.layout)

    def find_instrument(self):
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()

        found = False
        for resource in resources:
            try:
                inst = rm.open_resource(resource)
                inst.timeout = 2000  # 2 seconds for quick response
                idn = inst.query("*IDN?")
                if "N5173B" in idn:
                    self.status_label.setText(f"Connected to: {idn.strip()}")
                    self.main_window.instrument_found(inst)
                    found = True
                    break
                else:
                    inst.close()
            except pyvisa.errors.VisaIOError as e:
                if e.error_code != pyvisa.constants.StatusCode.error_timeout:
                    print(f"VISA IO Error on {resource}: {e}")
            except Exception as e:
                print(f"Error on {resource}: {e}")

        if not found:
            self.status_label.setText("Instrument not found.")

class LimitsScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.instr = None
        self.init_ui()

    def set_instrument(self, instr):
        self.instr = instr

    def init_ui(self):
        layout = QVBoxLayout()

        # Frequency Limit
        freq_layout = QHBoxLayout()
        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText("Max frequency")
        self.freq_unit = QComboBox()
        self.freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        freq_layout.addWidget(QLabel("Max Frequency:"))
        freq_layout.addWidget(self.freq_input)
        freq_layout.addWidget(self.freq_unit)

        # Power Limit
        power_layout = QHBoxLayout()
        self.power_input = QLineEdit()
        self.power_input.setPlaceholderText("Max power")
        self.power_unit = QComboBox()
        self.power_unit.addItems(["dBm", "dB", "W"])
        power_layout.addWidget(QLabel("Max Power:"))
        power_layout.addWidget(self.power_input)
        power_layout.addWidget(self.power_unit)

        # Set Limits Button
        self.set_button = QPushButton("Set Limits")
        self.set_button.clicked.connect(self.set_limits)

        layout.addLayout(freq_layout)
        layout.addLayout(power_layout)
        layout.addWidget(self.set_button)

        self.setLayout(layout)

    def set_limits(self):
        try:
            freq = float(self.freq_input.text())
            freq_unit = self.freq_unit.currentText()
            power = float(self.power_input.text())
            power_unit = self.power_unit.currentText()

            freq_multipliers = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
            freq_limit_hz = freq * freq_multipliers[freq_unit]

            # Let power remain in entered unit for simplicity
            self.main_window.limits_set(freq_limit_hz, (power, power_unit))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid input: {str(e)}")




class ControlScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.instr = None
        self.rf_on = False
        self.freq_limit = None
        self.power_limit = None
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout()

        freq_layout = QHBoxLayout()
        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText("Enter frequency")
        self.freq_unit = QComboBox()
        self.freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        freq_layout.addWidget(QLabel("Frequency:"))
        freq_layout.addWidget(self.freq_input)
        freq_layout.addWidget(self.freq_unit)

        power_layout = QHBoxLayout()
        self.power_input = QLineEdit()
        self.power_input.setPlaceholderText("Enter power value")
        self.power_unit = QComboBox()
        self.power_unit.addItems(["dBm", "dB", "W"])
        power_layout.addWidget(QLabel("Power:"))
        power_layout.addWidget(self.power_input)
        power_layout.addWidget(self.power_unit)

        self.set_button = QPushButton("Set Frequency & Power")
        self.set_button.clicked.connect(self.set_values)

        self.emergency_stop_button = QPushButton("EMERGENCY STOP")
        self.emergency_stop_button.setStyleSheet(
            "background-color: red; color: white; font-weight: bold; font-size: 16px;"
        )
        self.emergency_stop_button.clicked.connect(self.emergency_stop)

        self.layout.addLayout(freq_layout)
        self.layout.addLayout(power_layout)
        self.layout.addWidget(self.set_button)
        self.layout.addWidget(self.emergency_stop_button)

        self.setLayout(self.layout)

    def set_instrument(self, instr):
        self.instr = instr
    
    def set_limits(self, freq_limit, power_limit):
        self.freq_limit = freq_limit
        self.power_limit = power_limit

    def set_values(self):
        if not self.instr:
            QMessageBox.warning(self, "Warning", "Instrument not connected.")
            return
        try:
            freq = float(self.freq_input.text())
            unit = self.freq_unit.currentText()
            freq_multiplier = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
            freq_hz = freq * freq_multiplier[unit]

            power_val = float(self.power_input.text())
            power_unit = self.power_unit.currentText()

            if freq_hz > self.freq_limit:
                QMessageBox.critical(self, "Error", f"Frequency exceeds limit ({self.freq_limit} Hz)")
                return

            if power_unit != self.power_limit[1]:
                QMessageBox.critical(self, "Error", f"Power unit must be {self.power_limit[1]}")
                return
            if power_val > self.power_limit[0]:
                QMessageBox.critical(self, "Error", f"Power exceeds limit ({self.power_limit[0]} {power_unit})")
                return

            self.instr.write(f"FREQ {freq_hz} Hz")
            self.instr.write(f"POW {power_val} {power_unit}")
            self.instr.write("OUTP ON")
            self.rf_on = True

            QMessageBox.information(self, "Success", "Frequency and Power Set Successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set values: {str(e)}")

    def emergency_stop(self):
        if not self.instr:
            QMessageBox.warning(self, "Warning", "Instrument not connected.")
            return
        try:
            self.instr.write("OUTP OFF")
            self.rf_on = False
            QMessageBox.information(self, "Emergency Stop", "RF Output turned OFF immediately!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to turn OFF RF output: {str(e)}")

    def closeEvent(self, event):
        if self.instr and self.rf_on:
            try:
                self.instr.write("OUTP OFF")
                print("RF output turned OFF on exit.")
            except Exception as e:
                print(f"Error turning off RF output on exit: {e}")
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
