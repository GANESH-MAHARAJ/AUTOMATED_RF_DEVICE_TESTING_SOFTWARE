import usbtmc

try:
    instr = usbtmc.Instrument(0x0aad, 0x0180)
    print(instr.ask("*IDN?"))
    print(instr.ask("MEAS:POW?"))
except Exception as e:
    print("Error:", e)
