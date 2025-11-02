import sys
import pyvisa
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QStackedLayout
from PyQt6.QtCore import Qt, QTimer

class ConnectScreen(QWidget):
    def __init__(self, switch_callback):
        super().__init__()
        self.switch_callback = switch_callback
        self.instrument = None

        self.status_label = QLabel("Click 'Connect' to search for NRX devices.")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.search_instruments)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.connect_button)
        self.setLayout(layout)

    def search_instruments(self):
        try:
            rm = pyvisa.ResourceManager("@py")
            resources = rm.list_resources()
            for res in resources:
                try:
                    inst = rm.open_resource(res, timeout=2000)
                    idn = inst.query("*IDN?").strip()
                    if "NRX" in idn or "NRP2" in idn or "Rohde & Schwarz" in idn:
                        if "NRP2" in idn:
                            inst.device_type = "NRP2"
                            inst.write("SENS:CHAN1:FUNC 'POW'")
                        else:
                            inst.device_type = "NRX"

                        self.instrument = inst
                        self.status_label.setText(f"Found NRX: {idn}")
                        self.connect_button.setEnabled(False)
                        self.switch_callback(self.instrument)
                        return
                    else:
                        inst.close()
                except Exception:
                    continue
            self.status_label.setText("No NRX devices found.")
        except Exception as e:
            self.status_label.setText(f"Error scanning devices: {e}")


class ControlScreen(QWidget):
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument

        self.reading_label = QLabel("Power: -- dBm")
        self.reading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.reading_label)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.read_power)
        # self.timer.start(1000)  # Update every 1 second
    def start_polling(self):
        self.timer.start(10000)


    def read_power(self):
        try:
            if hasattr(self.instrument, "device_type") and self.instrument.device_type == "NRP2":
                raw_reading = self.instrument.query("READ?")
            else:
                raw_reading = self.instrument.query("MEAS:POW?")

            value_dbm = float(raw_reading.strip())
            self.reading_label.setText(f"Live Power: {value_dbm:.3f} dBm")
            self.timer.start(10000)
        except Exception as e:
            self.reading_label.setText(f"Error reading power: {e}")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NRX Power Meter Reader")
        self.setFixedSize(400, 150)

        self.stack = QStackedLayout()
        self.connect_screen = ConnectScreen(self.switch_to_control)
        self.stack.addWidget(self.connect_screen)

        self.setLayout(self.stack)

    def switch_to_control(self, instrument):
        self.control_screen = ControlScreen(instrument)
        self.stack.addWidget(self.control_screen)
        self.stack.setCurrentWidget(self.control_screen)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
