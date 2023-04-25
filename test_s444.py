#!/usr/bin/env python3

from dataclasses import dataclass
from random import randint
from typing import List

import cocotb
from cocotb.handle import Force
from cocotb.triggers import ReadOnly, ReadWrite, Timer, NextTimeStep

TEST_S44_BITSTREAM_ITERS = 50
TEST_S44_LUT_MAIN_ITERS = 50


async def tick(dut):
    """
    Toggles the `clk` field on `dut`
    """
    dut.clk.value = 0
    await Timer(1, units="ns")
    dut.clk.value = 1
    await Timer(1, units="ns")


async def write_bitstream(dut, bitstream):
    """
    Writes a `bitstream` to the `shift_in` field of `dut`. Also verifies that
    the bitstream read is of the exact length by reading from `shift_out`

    `bitstream` is a list of 1s and 0s
    """
    dut.en.value = 1
    await tick(dut)
    await tick(dut)
    dut.reset.value = 1
    await tick(dut)
    dut.reset.value = 0

    # Write initial bitstream, asserting that value after reset is 0
    b = list(bitstream)
    for bit in b:
        dut.shift_in.value = bit
        await ReadWrite()
        assert dut.shift_out.value == 0
        await tick(dut)

    # Write bitstream again, asserting that the one written initially was good
    for index, bit in enumerate(b):
        dut.shift_in.value = bit
        await ReadWrite()
        assert dut.shift_out.value == bit
        await tick(dut)

    dut.en.value = 0


@cocotb.test()
async def test_s444_bitstream(dut):
    """
    Test that writing random bitstreams succeeds
    """
    for _ in range(TEST_S44_BITSTREAM_ITERS):
        await write_bitstream(
            dut,
            [
                randint(0, 1) for _ in range(3 * 1 + 3 * 16  # S444_Logic
                                             + 1 * 1  # LUT5_Mux
                                             + 2 * 2  # D_Flip_Flops
                                             )
            ])


def int_to_bs(x: int, length: int) -> List[bool]:
    """
    Converts x to a binary list, big-endian, padded with zeros
    """
    mod = 2**length
    output = []
    while mod > 1:
        mod = mod // 2
        output.append(x & mod != 0)
    return output


@dataclass
class S444LogicBitstream:
    main3: bool
    main2: bool
    feed0_3: bool
    lut0: List[bool]
    lut1: List[bool]
    lut2: List[bool]

    def to_bs(self) -> List[bool]:
        return self.lut2[::-1] + self.lut1[::-1] + self.lut0[::-1] \
            + [self.feed0_3] + [self.main2] + [self.main3]


@dataclass
class LUT5MuxBitstream:
    feed1_3: bool

    def to_bs(self) -> List[bool]:
        return [self.feed1_3]


@dataclass
class DFlipFlopsBitstream:
    dff0: int
    dff1: int

    def to_bs(self) -> List[bool]:
        return int_to_bs(self.dff1, 2) + int_to_bs(self.dff0, 2)


@dataclass
class S444Bitstream:
    s444_logic: S444LogicBitstream
    lut5_mux: LUT5MuxBitstream
    d_flip_flops: DFlipFlopsBitstream

    def to_bs(self) -> List[bool]:
        return self.d_flip_flops.to_bs() \
            + self.lut5_mux.to_bs() \
            + self.s444_logic.to_bs()


@cocotb.test()
async def test_s444_lut4_main(dut):
    """
    Create a random main LUT4 and test that it was programmed correctly
    """
    bs = S444Bitstream(
            S444LogicBitstream(
                main3=True,
                main2=True,
                feed0_3=False,
                lut0=[0] * 16,
                lut1=[0] * 16,
                lut2=[0] * 16,
            ),
            LUT5MuxBitstream(feed1_3=False, ),
            DFlipFlopsBitstream(
                dff0=1,
                dff1=2,
            ),
    )

    for _ in range(TEST_S44_LUT_MAIN_ITERS):
        lut = [randint(0, 1) for _ in range(16)]
        bs.s444_logic.lut2 = lut
        await write_bitstream(dut, bs.to_bs())
        await tick(dut)
        dut._log.debug(f"{dut.s444_logic.l2_dat.value=}")

        for i, o in enumerate(lut):
            dut.main.value = Force(i)
            await ReadOnly()
            assert dut.main_out.value == o
            await Timer(1, units="ns")


@cocotb.test()
async def test_s444_lut4_feed0(dut):
    """
    Create a random feed0 LUT4 and test that it was programmed correctly
    """
    pass


@cocotb.test()
async def test_s444_lut4_feed1(dut):
    """
    Create a random feed1 LUT4 and test that it was programmed correctly
    """
    pass
