import pytest
from cpu import CPU


class TestCPU():

    cpu_under_test = CPU()

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
        


