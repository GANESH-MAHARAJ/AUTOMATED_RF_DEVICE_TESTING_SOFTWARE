import pyvisa

def connect_to_ngp800():
    rm = pyvisa.ResourceManager()
    resources = rm.list_resources()
    print("Available VISA resources:", resources)

    for res in resources:
        if "USB" in res or "ASRL" in res:
            try:
                instr = rm.open_resource(res)
                idn = instr.query("*IDN?")
                if "NGP800" in idn or "ROHDE" in idn.upper():
                    print(f"Connected to: {idn.strip()}")
                    return instr
            except Exception as e:
                print(f"Could not open resource {res}: {e}")
    
    raise Exception("NGP800 not found. Please check the connection.")

def set_channel_voltage(instr, channel, voltage):
    MAX_VOLTAGE = 64.0  # Upper limit in volts

    if channel not in range(1, 5):
        print("Invalid channel. Must be 1-4.")
        return

    if voltage < 0 or voltage > MAX_VOLTAGE:
        print(f"Invalid voltage. Must be between 0 and {MAX_VOLTAGE} V.")
        return

    try:
        instr.write(f"INST:NSEL {channel}")
        instr.write(f"VOLT {voltage}")
        instr.write("OUTP ON")
        print(f"Voltage set to {voltage} V on channel {channel}.")
    except Exception as e:
        print(f"Failed to set voltage: {e}")

def set_channel_current(instr, channel, current_mA):
    MAX_CURRENT = 10000  # Max current in mA = 10 A

    if channel not in range(1, 5):
        print("Invalid channel. Must be 1-4.")
        return

    if current_mA < 0 or current_mA > MAX_CURRENT:
        print(f"Invalid current. Must be between 0 and {MAX_CURRENT} mA.")
        return

    current_A = current_mA / 1000.0  # Convert mA to A
    try:
        instr.write(f"INST:NSEL {channel}")
        instr.write(f"CURR {current_A}")
        instr.write("OUTP ON")
        print(f"Current limit set to {current_mA} mA on channel {channel}.")
    except Exception as e:
        print(f"Failed to set current: {e}")

def main():
    try:
        instr = connect_to_ngp800()
    except Exception as e:
        print(e)
        return

    while True:
        try:
            mode = input("\nEnter mode: 1 for Voltage control, 2 for Current control, q to quit: ").strip()
            if mode.lower() in ['q', 'quit', 'exit']:
                break

            if mode not in ['1', '2']:
                print("Invalid choice. Enter 1 for Voltage or 2 for Current.")
                continue

            user_input = input("Enter channel (1-4) and value (V or mA), e.g. '2 5.0': ").strip()
            parts = user_input.split()
            if len(parts) != 2:
                print("Invalid input format. Use: channel value (e.g., '1 3.3')")
                continue

            ch = int(parts[0])
            val = float(parts[1])

            if mode == '1':
                set_channel_voltage(instr, ch, val)
            elif mode == '2':
                set_channel_current(instr, ch, val)

        except Exception as e:
            print(f"Error: {e}")

    instr.close()
    print("Disconnected.")

if __name__ == "__main__":
    main()
