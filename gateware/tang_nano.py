#!/usr/bin/env python

import subprocess

from amaranth import *
from amaranth.build import *

from audio_selector import System, get_resources

from amaranth_boards.tang_nano_9k import TangNano9kPlatform

#
#   Add PMOD connectors from Dock board

class TangNanoDock(TangNano9kPlatform):
 
    connectors = [
        Connector("pmod", 0, "28 26 39 37 - - 27 25 36 38"),
        Connector("pmod", 1, "42 35 34 30 - - 41 40 33 29"),
        Connector("pmod", 2, "69 57 55 53 - - 68 56 54 51"),
        Connector("pmod", 3, "86 84 82 80 - - 63 85 83 81"),
        Connector("pmod", 4, "77 75 73 71 - - 79 76 74 72"),
        Connector("pmod", 5, "48 31 -  -  - - 70 49 32 -"),
    ]

    def __init__(self, *args, **kwargs):
        TangNano9kPlatform.__init__(self, *args, toolchain='Apicula', **kwargs)
        self.device = self.part

    def toolchain_program(self, products, name):
        # the default platform doesn't have the -f (flash) flag set
        with products.extract("{}.fs".format(name)) as bitstream_filename:
            subprocess.check_call(["openFPGALoader", "-f", "-b", "tangnano9k", bitstream_filename])

    def get_pll(self, freq=48e6):
        assert 0, "TODO"
        # use the LiteX PLL calculations
        # https://github.com/enjoy-digital/litex/blob/master/litex/soc/cores/clock/gowin_gw1n.py
        from litex.soc.cores.clock import gowin_gw1n
        pll = gowin_gw1n.GW1NPLL(devicename="a", device=self.part)
        pll.clkin_freq = 27e6
        clockout = "xx" # clockout output signal
        pll.clkouts = { 
            'a' : (clockout, freq, 0, 0),
        }
        return pll.compute_config()

#
#

def ext_clock(freq, Platform, ck_name="ckext"):
    # Override the on-board clock with an external one
    class _Platform(Platform):
        default_clk = ck_name
        ck_freq = freq

    return _Platform()

#
#

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dot", help="generate Stream graph")
    parser.add_argument("--prog", action="store_true", help="generate Stream graph")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--freq", type=float, default=27e6*2)

    args = parser.parse_args()

    freq = args.freq
    # external clock
    ext_freq = 48e3 * 512 # External MCK from I2S pin "72"
    ext_freq = 48e3 * 1024 # External Xtal on PMOD pin "38" "29" "51"
    freq = ext_freq
    platform = ext_clock(freq, TangNanoDock)

    r = get_resources(platform)
    platform.add_resources(r)

    dut = System(freq)
    # TODO : how are the clock constraints passed to Amaranth?
    #platform.add_clock_constraint(s, freq)

    platform.build(dut, do_program=args.prog, verbose=args.verbose)

    # Generate DOT graph of the Amaranth Streams
    if args.dot:
        from streams import dot
        dot_path = "/tmp/wifi.dot"
        png_path = args.dot
        dot.graph(dut, dot_path, png_path)

#   FIN
