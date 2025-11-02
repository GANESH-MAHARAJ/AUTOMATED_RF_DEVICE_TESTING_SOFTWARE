import time
import threading
import pyvisa
from pyvisa.constants import Parity, StopBits

# User configuration for each channel
channels_config = {
    1: {"enabled": True, "start": 1.0, "step": 1.0, "end": 20.0, "duration": 1},
    2: {"enabled": False, "start": 0.0, "step": 0.5, "end": 5.0, "duration": 1},
    3: {"enabled": True, "start": 1.0, "step": 2.0, "end": 20.0, "duration": 2},
    4: {"enabled": False, "start": 1.5, "step": 0.5, "end": 3.0, "duration": 1},
}

def connect_to_ngp800():
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    print("Available VISA resources:", resources)

    for res in resources:
        if "USB" in res or "ASRL" in res:
            try:
                instr = rm.open_resource(res)

                if res.startswith("ASRL"):  # Serial settings
                    instr.baud_rate = 115200  # Try 9600 if needed
                    instr.data_bits = 8
                    instr.stop_bits = StopBits.one
                    instr.parity = Parity.none
                    instr.timeout = 2000
                    instr.write_termination = '\n'
                    instr.read_termination = '\n'

                idn = instr.query("*IDN?")
                if "NGP800" in idn or "ROHDE" in idn.upper():
                    print(f"Connected to: {idn.strip()}")
                    return instr
                instr.close()
            except Exception as e:
                print(f"Could not open resource {res}: {e}")
    
    raise Exception("NGP800 not found. Please check the connection.")

def voltage_step_thread(inst, lock, channel, start, step, end, duration):
    voltage = start
    while voltage <= end:
        with lock:
            print(f"[Channel {channel}] Setting voltage to {voltage} V")
            inst.write(f"INST:NSEL {channel}")
            inst.write(f"VOLT {voltage}")
            inst.write("OUTP ON")
        time.sleep(duration)
        voltage += step

    with lock:
        print(f"[Channel {channel}] Sequence done. Turning OFF.")
        inst.write(f"INST:NSEL {channel}")
        inst.write("OUTP OFF")

def main():
    try:
        inst = connect_to_ngp800()
        lock = threading.Lock()
        threads = []

        for ch, cfg in channels_config.items():
            if cfg["enabled"]:
                t = threading.Thread(
                    target=voltage_step_thread,
                    args=(inst, lock, ch, cfg["start"], cfg["step"], cfg["end"], cfg["duration"])
                )
                t.start()
                threads.append(t)

        # Wait for all threads to finish
        for t in threads:
            t.join()

    except Exception as e:
        print("Error:", e)
    finally:
        try:
            inst.close()
            print("Disconnected from device.")
        except:
            pass

if __name__ == "__main__":
    main()
