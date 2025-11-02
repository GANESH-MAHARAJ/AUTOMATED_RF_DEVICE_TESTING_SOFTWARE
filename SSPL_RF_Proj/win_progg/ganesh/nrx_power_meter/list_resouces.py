import pyvisa

rm = pyvisa.ResourceManager()
resource_name = "USB0::0x0AAD::0x0180::INSTR"
inst = rm.open_resource(resource_name)
print(inst.query("*IDN?"))
