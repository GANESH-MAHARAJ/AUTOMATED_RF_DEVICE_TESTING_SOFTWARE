import pyvisa
import time

rm = pyvisa.ResourceManager("@py")
paths = ["/dev/usbtmc0"]

for path in paths:
    try:
        inst = rm.open_resource(path)
        inst.clear()
        time.sleep(0.1)
        idn = inst.query("*IDN?").strip()
        print(f"Device at {path} responded: {idn}")
    except Exception as e:
        print(f"Error communicating with {path}: {e}")
