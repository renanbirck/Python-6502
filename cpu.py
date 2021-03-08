# py6502: a 6502 emulator in Python.

class CPU():

    def __init__(self, memory_size = 65536): # Inicialize a new CPU. 
                                             # The default RAM size is 64 KiB.

        self.PC = 0x0000  # Program counter
        self.SP = 0x0000  # Stack pointer
        self.A, self.X, self.Y = 0x00, 0x00, 0x00 # Registers
        self.RAM = [0x00] * memory_size

    def read_RAM(self, address):
        return self.RAM[address]

    def write_RAM(self, address, value):
        self.RAM[address] = value & 0xFF  # Limit to 1 byte
    
    def reset_CPU(self):
        self.A, self.X, self.Y = 0x00, 0x00, 0x00
        self.SP = 0xFD

        # 6502 is "low-endian". That is, in a 16-bit,
        # the "low" byte comes first then the "high" byte.
        PC_low = self.read_RAM(0xFFFC)
        PC_high = self.read_RAM(0xFFFD)

        self.PC = (PC_high << 8) | (PC_low)
