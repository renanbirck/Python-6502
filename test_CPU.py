import pytest, cpu

class TestCPU():

    cpu_under_test = cpu.CPU()

    def test_dump_state(self):
        self.cpu_under_test.pickle_state()

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
        # A few invalid instructions.
        self.cpu_under_test.write_RAM(0x0000, 0x80)
        self.cpu_under_test.write_RAM(0x0001, 0x80)

        # The reset vector.
        self.cpu_under_test.write_RAM(0xFFFD, 0x00)
        self.cpu_under_test.write_RAM(0xFFFC, 0x00)

        self.cpu_under_test.reset_CPU()

        with pytest.raises(RuntimeError):
            self.cpu_under_test.step()

    def test_handle_unimplemented_opcode(self):
        # A few unimplemented instructions.
        self.cpu_under_test.write_RAM(0x0000, 0x00)
        self.cpu_under_test.write_RAM(0x0001, 0x00)

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

        self.cpu_under_test.BRK()

        # The old PC, added by 1, is pushed upon the stack?
        assert self.cpu_under_test.pop_16bit() == 0x1235

        # The interrupt flag is set?
        assert (self.cpu_under_test.STATUS and cpu.StatusRegister.INTERRUPT) != 0

        # The BRK vector is read?
        assert self.cpu_under_test.PC == 0xC0CA

    def test_CL_instructions(self):
        # Test the simpler instructions (i.e. the ones that just clear flags)  

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
        
