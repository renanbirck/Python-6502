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
        # TODO: find a more elegant way to do that (Logic simplification?)
        
        if opcode in [0x0C, 0x0D, 0x0E, 0x0F, 0x20, 0x2C, 0x2D, 0x2E,
                      0x2F, 0x4C, 0x4D, 0x4E, 0x4F, 0x6D, 0x6E, 0x6F,
                      0x8C, 0x8D, 0x8E, 0x8F, 0xAC, 0xAD, 0xAE, 0xAF,
                      0xCC, 0xCD, 0xCE, 0xCF, 0xEC, 0xED, 0xEE, 0xEF]:
                          return AddressingMode.ABSOLUTE
        elif opcode in [0x1C, 0x1D, 0x1E, 0x1F, 0x3C, 0x3D, 0x3E, 0x3F,
                        0x5C, 0x5D, 0x5E, 0x5F, 0x7C, 0x7D, 0x7E, 0x7F,
                        0x9C, 0x9D, 0xBC, 0xBD, 0xDC, 0xDD, 0xDE, 0xDF,
                        0xFC, 0xFD, 0xFE, 0xFF]:
                          return AddressingMode.ABSOLUTE_X
        elif opcode in [0x19, 0x1B, 0x39, 0x3B, 0x59, 0x5B, 0x79, 0x7B,
                        0x99, 0x9B, 0x9E, 0x9F, 0xB9, 0xBB, 0xBE, 0xBF,
                        0xD9, 0xDB, 0xF9, 0xFB]:
                          return AddressingMode.ABSOLUTE_Y
        elif opcode in [0x0A, 0x2A, 0x4A, 0x6A]:
                          return AddressingMode.ACCUMULATOR
        elif opcode in [0x09, 0x0B, 0x29, 0x2B, 0x49, 0x4B, 0x69, 0x6B,
                        0x80, 0x82, 0x89, 0x8B, 0xA0, 0xA2, 0xA9, 0xAB,
                        0xC0, 0xC2, 0xC9, 0xCB, 0xE0, 0xE2, 0xE9, 0xEB]:
                          return AddressingMode.IMMEDIATE
        elif opcode == 0x6C:
                          return AddressingMode.INDIRECT
        elif opcode in [0x01, 0x03, 0x21, 0x23, 0x41, 0x43, 0x61, 0x63,
                        0x81, 0x83, 0xA1, 0xA3, 0xC1, 0xC3, 0xE1, 0xE3]:
                          return AddressingMode.INDIRECT_X
        elif opcode in [0x11, 0x13, 0x31, 0x33, 0x51, 0x53, 0x71, 0x73,
                        0x91, 0x93, 0xB1, 0xB3, 0xD1, 0xD3, 0xF1, 0xF3]:
                          return AddressingMode.INDIRECT_Y
        elif opcode in [0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0]:
                          return AddressingMode.RELATIVE
        elif opcode in [0x04, 0x05, 0x06, 0x07, 0x24, 0x25, 0x26, 0x27,
                        0x44, 0x45, 0x46, 0x47, 0x64, 0x65, 0x66, 0x67,
                        0x84, 0x85, 0x86, 0x87, 0xA4, 0xA5, 0xA6, 0xA7,
                        0xC4, 0xC5, 0xC6, 0xC7, 0xE4, 0xE5, 0xE6, 0xE7]:
                          return AddressingMode.ZERO_PAGE
        elif opcode in [0x14, 0x15, 0x16, 0x17, 0x34, 0x35, 0x36, 0x37,
                        0x54, 0x55, 0x56, 0x57, 0x74, 0x75, 0x76, 0x77,
                        0x94, 0x95, 0xB4, 0xB5, 0xD4, 0xD5, 0xD6, 0xD7,
                        0xF4, 0xF5, 0xF6, 0xF7]:
                          return AddressingMode.ZERO_PAGE_X
        elif opcode in [0x96, 0x97, 0xB6, 0xB7]:
                          return AddressingMode.ZERO_PAGE_Y

        # The default (most common) is implied addressing.
        return AddressingMode.IMPLIED
    
    def decode_instruction(self, opcode):
        instruction = self.NOP
        addressing_mode = self.find_addressing_mode(opcode)
        cost = 2
        return (instruction, addressing_mode, cost)
            
    def step(self):
        # Fetch
        opcode = self.read_RAM(self.PC)
        print(f"FETCH RAM[0x{self.PC:02X}] = 0x{opcode:02X}")
        self.PC += 1

        # Decode (i.e. find which instruction, the addressing mode and its cost in ticks)
        opcode_high = (opcode & 0xF0)>>4
        opcode_low = opcode & 0x0F
        
        # Trap illegal opcodes
        # ref. https://www.masswerk.at/6502/6502_instruction_set.html                
        # TODO: we won't need this in the future, when all the instructions are implemented.
        # All the invalid instructions ought to map to NOP.
        if opcode_low in [0x03, 0x07, 0x0B, 0x0F] or opcode in [0x80]:
            raise RuntimeError(f"Invalid opcode 0x{opcode:02X} at 0x{self.PC:02X}!")
        else:
            raise NotImplementedError(f"Instruction 0x{opcode:02X} not yet implemented!") 
    
    ## The instructions themselves
    def BRK(self):
        self.PC += 1
        # Save PC++ to stack.
        self.push_16bit(self.PC)
        # Push CPU status to stack.
        self.push_8bit(self.STATUS)
        # Read the new PC from the BRK vector
        self.PC = (self.read_RAM(0xFFFF)) << 8 | self.read_RAM(0xFFFE)

    def NOP(self):
        pass
        
    def CLC(self):
        self.STATUS &= ~StatusRegister.CARRY

    def CLD(self):
        self.STATUS &= ~StatusRegister.DECIMAL

    def CLI(self):
        self.STATUS &= ~StatusRegister.INTERRUPT

    def CLV(self):
        self.STATUS &= ~StatusRegister.OVERFLOW
