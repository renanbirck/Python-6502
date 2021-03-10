# py6502: a 6502 emulator in Python.

import logging, pickle
from enum import Flag

class StatusRegister(Flag):
    SIGN      = 0x80     # Negative
    OVERFLOW  = 0x40
    UNUSED    = 0x20
    BREAK     = 0x10     # Instruction 'BRK' was called.
    DECIMAL   = 0x08
    INTERRUPT = 0x04
    ZERO      = 0x02
    CARRY     = 0x01

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

    def read_RAM(self, address):
        return self.RAM[address]

    def write_RAM(self, address, value):
        print(f"RAM[0x{address:02X}] <- 0x{value:04X}")
        self.RAM[address] = value & 0xFF  # Limit to 1 byte
    
    def reset_CPU(self):
        logging.info("CPU reset.")
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

    def pickle_state(self):
        pickle.dump(self, open("cpu_state", "wb"))

    def step(self):
        # Fetch
        
        opcode = self.read_RAM(self.PC)
        print(f"FETCH RAM[0x{self.PC:02X}] = 0x{opcode:02X}")

        self.PC = self.PC + 1
        
        # Decode 

        opcode_high = (opcode & 0xF0)>>4
        opcode_low = opcode & 0x0F

        # Trap illegal opcodes
        # ref. https://www.masswerk.at/6502/6502_instruction_set.html                

        if opcode_low in [0x03, 0x07, 0x0B, 0x0F] or opcode in [0x80]:
            raise RuntimeError(f"Invalid opcode 0x{opcode:02X} at 0x{self.PC:02X}!")

        # Execute
