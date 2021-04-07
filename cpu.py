# py6502: a 6502 emulator in Python.

from enum import Enum, Flag, auto

class StatusRegister(Flag):
    SIGN       = 0x80     # Negative
    OVERFLOW   = 0x40
    UNUSED     = 0x20
    BREAK      = 0x10     # Instruction 'BRK' was called.
    DECIMAL    = 0x08
    INTERRUPT  = 0x04
    ZERO       = 0x02
    CARRY      = 0x01
    NOTHING    = 0x00

class AddressingMode(Enum):
    IMPLIED = auto()
    ACCUMULATOR = auto()
    IMMEDIATE = auto()
    ZERO_PAGE = auto()
    ZERO_PAGE_X = auto()
    ZERO_PAGE_Y = auto()
    RELATIVE = auto()
    ABSOLUTE = auto()
    ABSOLUTE_X = auto()
    ABSOLUTE_Y = auto()
    INDIRECT = auto()
    INDIRECT_X = auto()
    INDIRECT_Y = auto()

class CPU():
    def __init__(self, memory_size = 65536): # Inicialize a new CPU.
                                   # The default RAM size is 64 KiB.
        
        self.ticks = 0    # Tick count

        # When is executed an instruction, this callback will
        # be called as needed. It receives self, thus it has access
        # to everything that has happening within the CPU.

        self.callback_on_instruction = None
        self.PC = 0x0000  # Program counter
        self.SP = 0x0000  # Stack pointer
        self.A, self.X, self.Y = 0x00, 0x00, 0x00 # Registers
        self.RAM = [0x00] * memory_size
        self.STACK_BASE = 0x100
        self.STATUS = StatusRegister(0x00)

    def read_RAM(self, address):
        return self.RAM[address]

    def write_RAM(self, address, value):
        if isinstance(value, StatusRegister):
            value = value.value  # yeah, I know. Horrible.
            
        print(f"RAM[0x{address:02X}] <- 0x{value:04X}")
        self.RAM[address] = value & 0xFF  # Limit to 1 byte

    def reset_CPU(self):
        self.A, self.X, self.Y = 0x00, 0x00, 0x00
        self.SP = 0xFD

        # 6502 is "low-endian". That is, in a 16-bit,
        # the "low" byte comes first then the "high" byte.
        PC_low = self.read_RAM(0xFFFC)
        PC_high = self.read_RAM(0xFFFD)

        self.PC = (PC_high << 8) | (PC_low)

    def push_8bit(self, value):
        self.write_RAM(self.STACK_BASE + self.SP, value)
        self.SP -= 1

    def pop_8bit(self):
        self.SP += 1
        return self.read_RAM(self.STACK_BASE + self.SP)

    def push_16bit(self, value):
        value_low = value & 0x00FF
        value_high = (value & 0xFF00) >> 8

        self.push_8bit(value_high)
        self.push_8bit(value_low)
    #    self.write_RAM(self.STACK_BASE + self.SP, value_high)
    #    self.write_RAM(self.STACK_BASE + ((self.SP - 1) & 0xFF), value_low)
    #    self.SP -= 2

    def pop_16bit(self):
        value_low = self.pop_8bit()
        value_high = self.pop_8bit()
        value_high = value_high << 8

        return value_high + value_low

    def find_addressing_mode(self, opcode):
        # Given opcode, find its addressing mode.

        opcode_high = (opcode & 0xF0)>>4
        opcode_low = opcode & 0x0F

        if opcode == 0x20 or (opcode != 0x6C and opcode_high in [0x00, 0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C, 0x0E]
                                             and opcode_low  in [0x0C, 0x0D, 0x0E, 0x0F]):
            return AddressingMode.ABSOLUTE
        elif (opcode_high in [0x1, 0x3, 0x5, 0x7, 0xD, 0xF] and opcode_low in [0x0C, 0x0D, 0x0E, 0x0F]) or (opcode in [0x9C, 0x9D, 0xBC, 0xBD]):
            return AddressingMode.ABSOLUTE_X
        elif ((opcode_low in [0x9, 0xB] and opcode_high in [0x1, 0x3, 0x5, 0x7, 0xD, 0xF])
        or (opcode_low in [0x9, 0xB, 0xE, 0xF] and opcode_high in [0x9, 0xB])):
            return AddressingMode.ABSOLUTE_Y
        elif opcode_high in [0x0, 0x2, 0x4, 0x6] and opcode_low == 0xA:
            return AddressingMode.ACCUMULATOR
        elif (opcode_high in [0x0, 0x2, 0x4, 0x6] and opcode_low in [0x9, 0xB]) \
        or (opcode_high in [0x8, 0xA, 0xC, 0xE] and opcode_low in [0x0, 0x2, 0x9, 0xB]):
            return AddressingMode.IMMEDIATE
        elif (opcode_high in [0x0, 0x2, 0x4, 0x6, 0x8, 0xA, 0xC, 0xE] and opcode_low in [0x1, 0x3]):
            return AddressingMode.INDIRECT_X
        elif (opcode_high in [0x1, 0x3, 0x5, 0x7, 0x9, 0xB, 0xD, 0xF] and opcode_low in [0x1, 0x3]):
            return AddressingMode.INDIRECT_Y
        elif (opcode_high in [0x1, 0x3, 0x5, 0x7, 0x9, 0xB, 0xD, 0xF] and opcode_low == 0x00):
            return AddressingMode.RELATIVE
        elif (opcode_high in [0x0, 0x2, 0x4, 0x6, 0x8, 0xA, 0xC, 0xE] and opcode_low in [0x4, 0x5, 0x6, 0x7]):
            return AddressingMode.ZERO_PAGE
        elif (opcode_high in [0x1, 0x3, 0x5, 0x7, 0xD, 0xF] and opcode_low in [0x4, 0x5, 0x6, 0x7]) \
        or (opcode_high in [0x9, 0xB] and opcode_low in [0x4, 0x5]):
            return AddressingMode.ZERO_PAGE_X
        elif opcode in [0x96, 0x97, 0xB6, 0xB7]:
            return AddressingMode.ZERO_PAGE_Y
        
        # The default (most common) is implied addressing.
        return AddressingMode.IMPLIED
        
    def step(self):
        # Fetch
        opcode = self.read_RAM(self.PC)
        print(f"FETCH RAM[0x{self.PC:02X}] = 0x{opcode:02X}")
        self.PC += 1

        # Decode 
        opcode_high = (opcode & 0xF0)>>4
        opcode_low = opcode & 0x0F

        # Trap illegal opcodes
        # ref. https://www.masswerk.at/6502/6502_instruction_set.html                

        if opcode_low in [0x03, 0x07, 0x0B, 0x0F] or opcode in [0x80]:
            raise RuntimeError(f"Invalid opcode 0x{opcode:02X} at 0x{self.PC:02X}!")
        else:
            raise NotImplementedError(f"Instruction 0x{opcode:02X} not yet implemented!")        # Execute
    
    ## The instructions themselves
    def BRK(self):
        self.PC += 1
        # Save PC++ to stack.
        self.push_16bit(self.PC)
        # Push CPU status to stack.
        self.push_8bit(self.STATUS)
        # Read the new PC from the BRK vector
        self.PC = (self.read_RAM(0xFFFF)) << 8 | self.read_RAM(0xFFFE)

    def CLC(self):
        self.STATUS &= ~StatusRegister.CARRY

    def CLD(self):
        self.STATUS &= ~StatusRegister.DECIMAL

    def CLI(self):
        self.STATUS &= ~StatusRegister.INTERRUPT

    def CLV(self):
        self.STATUS &= ~StatusRegister.OVERFLOW
