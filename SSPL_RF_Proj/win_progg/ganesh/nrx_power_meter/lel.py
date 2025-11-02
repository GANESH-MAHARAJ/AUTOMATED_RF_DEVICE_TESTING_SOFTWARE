import usb.core
import usb.util
import usbtmc

def find_nrx_device():
    # Find all USB devices matching Rohde & Schwarz NRX vendor/product
    # If unsure of IDs, scan all USBTMC devices
    devices = usb.core.find(find_all=True)
    for dev in devices:
        if dev.bDeviceClass == 0xFE or dev.bDeviceClass == 0:  # USBTMC class or misc
            # Check Vendor/Product IDs or other attributes
            # You can print dev.idVendor, dev.idProduct for debugging
            try:
                idn_candidate = usbtmc.Instrument(dev.idVendor, dev.idProduct).ask("*IDN?")
                if "NRX" in idn_candidate or "Rohde & Schwarz" in idn_candidate:
                    print(f"Found NRX device: {idn_candidate.strip()}")
                    return usbtmc.Instrument(dev.idVendor, dev.idProduct)
            except Exception:
                continue
    return None

instr = find_nrx_device()
if instr:
    print("Power Reading:", instr.ask("MEAS:POW?").strip())
else:
    print("No NRX device found.")
