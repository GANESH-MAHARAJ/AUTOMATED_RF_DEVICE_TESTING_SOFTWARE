import pyvisa
rm = pyvisa.ResourceManager()
resources = rm.list_resources()
print("Resources found:", resources)

for res in resources:
    try:
        instr = rm.open_resource(res)
        idn = instr.query("*IDN?")
        print(f"{res}: {idn}")
        instr.close()
    except Exception as e:
        print(f"{res}: {e}")

