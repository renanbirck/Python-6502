# pylint: disable=C0103,E0401

import pytest
import cpu

class TestCPU():

    cpu_under_test = cpu.CPU()

    def test_read_RAM_outside_bounds(self):
        with pytest.raises(IndexError):
            self.cpu_under_test.read_RAM(0xFFFFFFFF)

    def test_RAM_RW(self):
        for i in range(0, 0x10000):
            self.cpu_under_test.write_RAM(i, i & 0xFF) # Get the lowest byte
            assert self.cpu_under_test.read_RAM(i) == (i & 0xFF)

    def test_CPU_reset(self):
        # On reset, the 6502 reads the PC from 0xFFFC and 0xFFFD.
        self.cpu_under_test.write_RAM(0xFFFD, 0xCA)
        self.cpu_under_test.write_RAM(0xFFFC, 0xFE)
        self.cpu_under_test.reset_CPU()

        assert self.cpu_under_test.A == 0x00
        assert self.cpu_under_test.X == 0x00
        assert self.cpu_under_test.Y == 0x00
        assert self.cpu_under_test.SP == 0xFD
        assert self.cpu_under_test.PC == 0xCAFE

    def test_stack_push_pop_8bit(self):

        previous_SP = self.cpu_under_test.SP
        self.cpu_under_test.push_8bit(0x42)
        self.cpu_under_test.push_8bit(0x46)
        assert self.cpu_under_test.pop_8bit() == 0x46
        assert self.cpu_under_test.pop_8bit() == 0x42
        assert self.cpu_under_test.SP == previous_SP

    def test_stack_push_pop_16bit(self):
        previous_SP = self.cpu_under_test.SP

        self.cpu_under_test.push_16bit(0xC0CA)
        self.cpu_under_test.push_16bit(0x50DA)

        assert self.cpu_under_test.pop_16bit() == 0x50DA
        assert self.cpu_under_test.pop_16bit() == 0xC0CA

        assert self.cpu_under_test.SP == previous_SP

    def test_handle_invalid_opcode(self):
        # TODO: remove those tests when all the instructions are implemented!

        # A few invalid instructions.
        self.cpu_under_test.write_RAM(0x0000, 0x82)
        self.cpu_under_test.write_RAM(0x0001, 0x82)

        # The reset vector.
        self.cpu_under_test.write_RAM(0xFFFD, 0x00)
        self.cpu_under_test.write_RAM(0xFFFC, 0x00)

        self.cpu_under_test.reset_CPU()

        with pytest.raises(NotImplementedError):
            self.cpu_under_test.step()

    def test_handle_unimplemented_opcode(self):
        # A few unimplemented instructions.
        self.cpu_under_test.write_RAM(0x0000, 0x01)
        self.cpu_under_test.write_RAM(0x0001, 0x01)

        # The reset vector.
        self.cpu_under_test.write_RAM(0xFFFD, 0x00)
        self.cpu_under_test.write_RAM(0xFFFC, 0x00)

        self.cpu_under_test.reset_CPU()

        with pytest.raises(NotImplementedError):
            self.cpu_under_test.step()

    def test_handle_invalid_RAM_write(self):
        self.cpu_under_test.write_RAM(0x0000, 0x6502)
        assert self.cpu_under_test.read_RAM(0x0000) == 0x02

    ### Instruction tests

    def test_BRK(self):
        self.cpu_under_test.write_RAM(0xFFFE, 0xCA)
        self.cpu_under_test.write_RAM(0xFFFF, 0xC0)

        self.cpu_under_test.reset_CPU()
        self.cpu_under_test.PC = 0x1234

        # Force a dummy status.
        self.cpu_under_test.STATUS = cpu.StatusRegister.OVERFLOW |  cpu.StatusRegister.ZERO

        self.cpu_under_test.BRK()

        previous_CPU_status = self.cpu_under_test.STATUS.value

        # The status was save?
        assert self.cpu_under_test.pop_8bit() == previous_CPU_status

        # The old PC, added by 1, is pushed upon the stack?
        assert self.cpu_under_test.pop_16bit() == 0x1235

        # The interrupt flag is set?
        assert (self.cpu_under_test.STATUS and cpu.StatusRegister.INTERRUPT) != 0

        # The BRK vector is read?
        assert self.cpu_under_test.PC == 0xC0CA

    # Given an instruction, find out its addressing mode.
    def test_find_addressing_mode(self):
        for opcode in [0x0C, 0x0D, 0x0E, 0x0F, 0x20, 0x2C,
                        0x2D, 0x2E, 0x2F, 0x4C, 0x4D, 0x4E,
                        0x4F, 0x6D, 0x6E, 0x6F, 0x8C, 0x8D,
                        0x8E, 0x8F, 0xAC, 0xAD, 0xAE, 0xAF,
                        0xCC, 0xCD, 0xCE, 0xCF, 0xEC, 0xED,
                        0xEE, 0xEF]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ABSOLUTE
        for opcode in [0x1C, 0x1D, 0x1E, 0x1F, 0x3C, 0x3D, 0x3E,
                       0x3F, 0x5C, 0x5D, 0x5E, 0x5F, 0x7C, 0x7D,
                       0x7E, 0x7F, 0x9C, 0x9D, 0xBC, 0xBD, 0xDC,
                       0xDD, 0xDE, 0xDF, 0xFC, 0xFD, 0xFE, 0xFF]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ABSOLUTE_X
        for opcode in [0x19, 0x1B, 0x39, 0x3B, 0x59,
                       0x5B, 0x79, 0x7B, 0x99, 0x9B,
                       0x9E, 0x9F, 0xB9, 0xBB, 0xBE,
                       0xBF, 0xD9, 0xDB, 0xF9, 0xFB]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ABSOLUTE_Y
        for opcode in [0x0A, 0x2A, 0x4A, 0x6A]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ACCUMULATOR
        for opcode in [0x09, 0x0B, 0x29, 0x2B, 0x49,
                       0x4B, 0x69, 0x6B, 0x80, 0x82,
                       0x89, 0x8B, 0xA0, 0xA2, 0xA9,
                       0xAB, 0xC0, 0xC2, 0xC9, 0xCB,
                       0xE0, 0xE2, 0xE9, 0xEB]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.IMMEDIATE
        for opcode in [0x01, 0x03, 0x21, 0x23, 0x41,
                       0x43, 0x61, 0x63, 0x81, 0x83,
                       0xA1, 0xA3, 0xC1, 0xC3, 0xE1,
                       0xE3]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.INDIRECT_X
        for opcode in [0x11, 0x13, 0x31, 0x33, 0x51,
                       0x53, 0x71, 0x73, 0x91, 0x93,
                       0xB1, 0xB3, 0xD1, 0xD3, 0xF1,
                       0xF3]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.INDIRECT_Y
        for opcode in [0x10, 0x30, 0x50, 0x70,
                       0x90, 0xB0, 0xD0, 0xF0]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.RELATIVE
        for opcode in [0x04, 0x05, 0x06, 0x07, 0x24, 0x25, 0x26, 0x27,
                       0x44, 0x45, 0x46, 0x47, 0x64, 0x65, 0x66, 0x67,
                       0x84, 0x85, 0x86, 0x87, 0xA4, 0xA5, 0xA6, 0xA7,
                       0xC4, 0xC5, 0xC6, 0xC7, 0xE4, 0xE5, 0xE6, 0xE7]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ZERO_PAGE
        for opcode in [0x14, 0x15, 0x16, 0x17, 0x34, 0x35, 0x36, 0x37,
                       0x54, 0x55, 0x56, 0x57, 0x74, 0x75, 0x76, 0x77,
                       0x94, 0x95, 0xB4, 0xB5, 0xD4, 0xD5, 0xD6, 0xD7,
                       0xF4, 0xF5, 0xF6, 0xF7]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ZERO_PAGE_X
        for opcode in [0x96, 0x97, 0xB6, 0xB7]:
            assert self.cpu_under_test.find_addressing_mode(opcode) == cpu.AddressingMode.ZERO_PAGE_Y
        assert self.cpu_under_test.find_addressing_mode(0x00) == cpu.AddressingMode.IMPLIED

    def test_decode_instruction(self):
        opcode = 0x80
        instruction, addressing_mode, cost = self.cpu_under_test.decode_instruction(opcode)
        assert instruction == self.cpu_under_test.NOP
        assert addressing_mode == cpu.AddressingMode.IMMEDIATE
        assert cost == 2

        opcode = 0x18 # CLC
        instruction, addressing_mode, cost = self.cpu_under_test.decode_instruction(opcode)
        assert instruction == self.cpu_under_test.CLC
        assert addressing_mode == cpu.AddressingMode.IMPLIED
        assert cost == 2
    
    # imp, acc don't change ea, so they are not tested.
    def test_find_effective_address_imm(self):
        # Immediate. EA <- PC+1
        PC_old = self.cpu_under_test.PC

        self.cpu_under_test.compute_effective_address(cpu.AddressingMode.IMMEDIATE)
        assert self.cpu_under_test.EA == PC_old + 1

    def test_find_effective_address_zp(self):
        # Zero-page mode. EA <- RAM[PC+1]
        
        # Inicialize the RAM that will be used for the test.
        for position in range(0, 65536):
            value = position & 0xFF
            self.cpu_under_test.write_RAM(position, value)
        
        self.cpu_under_test.PC = 0x4000  # PC <- 0x4000
        self.cpu_under_test.compute_effective_address(cpu.AddressingMode.ZERO_PAGE) # EA <- RAM[PC+1]
        assert self.cpu_under_test.EA == self.cpu_under_test.read_RAM(0x4001)
        
        
    ##### INSTRUCTION TESTS

    def test_NOP(self):
        self.cpu_under_test.NOP()

    def test_CL_instructions(self):
        # Test the simpler instructions (i.e. the ones that just clear flags).

        self.cpu_under_test.STATUS = cpu.StatusRegister.NOTHING
        self.cpu_under_test.STATUS |= cpu.StatusRegister.CARRY
        self.cpu_under_test.STATUS |= cpu.StatusRegister.DECIMAL
        self.cpu_under_test.STATUS |= cpu.StatusRegister.INTERRUPT
        self.cpu_under_test.STATUS |= cpu.StatusRegister.OVERFLOW

        self.cpu_under_test.CLC()
        assert (self.cpu_under_test.STATUS.value & cpu.StatusRegister.CARRY.value) == 0

        self.cpu_under_test.CLD()
        assert (self.cpu_under_test.STATUS.value & cpu.StatusRegister.DECIMAL.value) == 0

        self.cpu_under_test.CLI()
        assert (self.cpu_under_test.STATUS.value & cpu.StatusRegister.INTERRUPT.value) == 0

        self.cpu_under_test.CLV()
        assert (self.cpu_under_test.STATUS.value & cpu.StatusRegister.OVERFLOW.value) == 0

