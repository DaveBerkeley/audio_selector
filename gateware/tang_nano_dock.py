
import subprocess

from amaranth.build import *
from amaranth_boards.tang_nano_9k import TangNano9kPlatform

#
#   Add PMOD connectors from Dock board

class TangNanoDock(TangNano9kPlatform):
 
    raw_connectors = [
        ("pmod", 0, "28 26 39 37 - - 27 25 36 38"),
        ("pmod", 1, "42 35 34 30 - - 41 40 33 29"),
        ("pmod", 2, "69 57 55 53 - - 68 56 54 51"),
        ("pmod", 3, "86 84 82 80 - - 63 85 83 81"),
        ("pmod", 4, "77 75 73 71 - - 79 76 74 72"),
        ("pmod", 5, "48 31 -  -  - - 70 49 32 -"),
    ]

    def __init__(self, *args, **kwargs):
        self.connectors = []
        for name, idx, pins in self.raw_connectors:
            self.connectors.append(Connector(name, idx, pins))
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

#   FIN
