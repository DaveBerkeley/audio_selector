#!/bin/env python

#   GoWin PLL for the TangNano 9k
#
#   see https://github.com/YosysHQ/apicula/blob/master/apycula/gowin_pll.py
#   for example code and constraints
#
#   GoWin doc "primitive definition and usage of Gowin clock" UG286E
#   contains details of the PLL calculations.
#   Constraints for different devices are in 
#   "GW1NRF series of FPGA Products Schematic Manual" UG294-1.3.2E
#   (and others, for different devices)

import re

from amaranth import *
from amaranth.lib.cdc import ResetSynchronizer

"""
        # Create clock domains and connect outputs
        for name in output_names:
            m.domains += ClockDomain(name)
            m.d.comb += ClockSignal(name).eq(output_map[name])
            m.submodules[f"rst_sync_{name}"] = ResetSynchronizer(
                ~pll_locked, domain=name
            )
            
            if platform is not None and hasattr(platform, 'add_period_constraint'):
                params = self.pll_params[name]
                platform.add_period_constraint(
                    output_map[name], 
                    1e9 / params['actual_freq']
                )
        
        m.d.comb += self.locked.eq(pll_locked)
        
        return m
"""

#   From https://github.com/YosysHQ/apicula/blob/master/apycula/gowin_pll.py

device_limits = {
    "GW1N-1 C6/I5": {
        "comment": "Untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 900,
        "clkout_min": 3.125,
        "clkout_max": 450,
    },
    "GW1N-1 C5/I4": {
        "comment": "Untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 320,
        "vco_max": 720,
        "clkout_min": 2.5,
        "clkout_max": 360,
    },
    "GW1NR-2 C7/I6": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 800,
        "clkout_min": 3.125,
        "clkout_max": 750,
    },
    "GW1NR-2 C6/I5": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 800,
        "clkout_min": 3.125,
        "clkout_max": 750,
    },
    "GW1NR-2 C5/I4": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 320,
        "vco_max": 640,
        "clkout_min": 2.5,
        "clkout_max": 640,
    },
    "GW1NR-4 C6/I5": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1000,
        "clkout_min": 3.125,
        "clkout_max": 500,
    },
    "GW1NR-4 C5/I4": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 320,
        "vco_max": 800,
        "clkout_min": 2.5,
        "clkout_max": 400,
    },
    "GW1NSR-4 C7/I6": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NSR-4 C6/I5": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NSR-4 C5/I4": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 320,
        "vco_max": 960,
        "clkout_min": 2.5,
        "clkout_max": 480,
    },
    "GW1NSR-4C C7/I6": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NSR-4C C6/I5": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NSR-4C C5/I4": {
        "comment": "Untested",
        "pll_name": "PLLVR",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 320,
        "vco_max": 960,
        "clkout_min": 2.5,
        "clkout_max": 480,
    },
    "GW1NR-9 C7/I6": {
        "comment": "Untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NR-9 C6/I5": {
        "comment": "tested on TangNano9K Board",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 1200,
        "clkout_min": 3.125,
        "clkout_max": 600,
    },
    "GW1NR-9 C6/I4": {
        "comment": "Untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 320,
        "vco_min": 3200,
        "vco_max": 960,
        "clkout_min": 2.5,
        "clkout_max": 480,
    },
    "GW1NZ-1 C6/I5": {
        "comment": "untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 400,
        "vco_min": 400,
        "vco_max": 800,
        "clkout_min": 3.125,
        "clkout_max": 400,
    },
    "GW2A-18 C8/I7": {
        "comment": "untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 500,
        "vco_min": 500,
        "vco_max": 1250,
        "clkout_min": 3.90625,
        "clkout_max": 625,
    },
    "GW2AR-18 C8/I7": {
        "comment": "untested",
        "pll_name": "rPLL",
        "pfd_min": 3,
        "pfd_max": 500,
        "vco_min": 500,
        "vco_max": 1250,
        "clkout_min": 3.90625,
        "clkout_max": 625,
    },
    "GW5A-25 ES": {
        "comment": "untested",
        "pll_name": "rPLL",
        "pfd_min": 19,
        "pfd_max": 800,
        "vco_min": 800,
        "vco_max": 1600,
        # The previous four parameters are taken from the datasheet (as in
        # this case from https://cdn.gowinsemi.com.cn/DS1103E.pdf), but I
        # don't know where these two come from:(
        "clkout_min": 6.25,
        "clkout_max": 1600,
    },
}

#
#

class PLL(Elaboratable):

    def __init__(self, fin, fout, limits):
        self.limits = limits
        self.config = self.calc(fin, fout, limits)
        self.params = self.instance_params(self.config, limits['device'])
        #print(self.config)

        self.clk_in = Signal()
        self.rst_in = Signal()
        self.clk_out = Signal()
        self.locked = Signal()

        self.params.update(
            i_CLKIN=self.clk_in,
            i_RESET=self.rst_in,
            o_LOCK=self.locked,
        )
        if self.config['sdiv'] == 1:
            self.params.update(o_CLKOUT=self.clk_out)
        else:
            self.params.update(o_CLKOUTD=self.clk_out)                    
        #print(self.params)

    def elaborate(self, _):
        m = Module()
        self.instance = Instance(self.limits['pll_name'], **self.params)
        m.submodules += self.instance
        return m

    @classmethod
    def calc(cls, fin, fout, limits):
        idiv_range = list(range(0, 64))
        fbdiv_range = list(range(0, 64))
        odiv_range = [ 2, 4, 8, 16, 32, 48, 64, 80, 96, 112, 128 ]
        # 1 means don't use sdiv, so use clk_out, otherwise use clk_outd 
        sdiv_range = [ 1 ] + list(range(2, 41, 2))

        def pfd_valid(f): return limits['pfd_min'] <= f <= limits['pfd_max']
        def vco_valid(f): return limits['vco_min'] <= f <= limits['vco_max']
        def clock_valid(f): return limits['clkout_min'] <= f <= limits['clkout_max']

        err_max = fin
        config = {}

        for sdiv in sdiv_range:
            for idiv in idiv_range:
                for fbdiv in fbdiv_range:
                    for odiv in odiv_range:
                        # Check the Phase Frequency Detector is within range
                        # on both inputs of the phase detector.
                        pfd = fin / (idiv + 1)
                        if not pfd_valid(pfd):
                            continue
                        pfd = fout / (fbdiv + 1)
                        if not pfd_valid(pfd):
                            continue

                        # Check VCO range
                        vco = fin * (fbdiv + 1) * odiv / (idiv + 1)
                        if not vco_valid(vco):
                            continue

                        # Check clock out range
                        ckout = fin * (fbdiv + 1) / ((idiv + 1) * sdiv)
                        if not clock_valid(ckout):
                            continue

                        err = abs(fout - ckout)
                        if err < err_max:
                            err_max = err
                            config = dict(fin=fin, 
                                        freq=fout, 
                                        ckout=ckout, 
                                        vco=vco,
                                        idiv=idiv,
                                        fbdiv=fbdiv,
                                        odiv=odiv,
                                        sdiv=sdiv,
                                        percent=100*abs(err/fout),
                                        err=err,
                            )
                            if err == 0.0:
                                return config
        return config

    @classmethod
    def instance_params(cls, params, device):
        d = dict(
            p_DEVICE=device,
            p_FCLKIN=params['fin'],
            p_IDIV_SEL=params['idiv'],
            p_FBDIV_SEL=params['fbdiv'],
            p_ODIV_SEL=params['odiv'],
            p_DYN_IDIV_SEL="false",
            p_DYN_FBDIV_SEL="false",
            p_DYN_ODIV_SEL="false",
            p_PSDA_SEL="0000",
            p_DYN_DA_EN="false",
            p_DUTYDA_SEL="1000",
            p_CLKOUT_FT_DIR=1,
            p_CLKOUTP_FT_DIR=1,
            p_CLKOUT_DLY_STEP=0,
            p_CLKOUTP_DLY_STEP=0,
            p_CLKFB_SEL="internal",
            p_CLKOUT_BYPASS="false",
            p_CLKOUTP_BYPASS="false",
            p_CLKOUTD_BYPASS="false",
            p_CLKOUTD_SRC="CLKOUT",
            p_CLKOUTD3_SRC="CLKOUT",

            i_CLKFB=0,
            i_RESET_P=0,
            i_FBDSEL=0,
            i_IDSEL=0,
            i_ODSEL=0,
            i_PSDA=0,
            i_DUTYDA=0,
            i_FDLY=0,
        )
    
        if params['sdiv'] != 1:
            d.update(p_DYN_SDIV_SEL=params['sdiv'])

        return d

#
#

def get_limits(device):
    regex = r"(GW[125][A-Z]{1,3})-[A-Z]{0,2}([0-9]{1,2})[A-Z]{1,3}[0-9]{1,3}P*N*(C[0-9]/I[0-9]|ES)"
    match = re.search(regex, device)
    if not match:
        raise Exception(f'cannot decipher the name of the device {device}.')

    key = f"{match.group(1)}-{match.group(2)} {match.group(3)}"
    device = f"{match.group(1)}"

    limits = device_limits[key]
    limits = limits.copy()
    limits['device'] = device
    return limits

if __name__ == "__main__":

    import sys

    dev = "GW1NR-LV9QN88PC6/I5"
    limits = get_limits(dev)
    #print(limits)

    fin = 27
    fin = 49.125
    for f in range(1, 200):
        params = PLL.calc(fin, f, limits)
        #print(params)
        if not params:
            print("No PLL solution found", file=sys.stderr)
            continue
        pll = PLL(fin, f, limits) 
        print(f, *[ params[field] for field in [ 'vco', 'ckout', 'percent', 'sdiv' ] ])

#   FIN
