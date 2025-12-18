#!/usr/bin/env python

from amaranth import *
from amaranth.build import *

from audio_selector import System, get_resources

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
    parser.add_argument("--platform", default="tangnano")

    args = parser.parse_args()

    if args.platform == "tangnano":
        from tang_nano_dock import TangNanoDock as Platform
    elif args.platform == "i9":
        from colorlight_i9_r7_2 import Colorlight_i9_R72Platform as Platform

    freq = args.freq
    # external clock
    ext_freq = 48e3 * 512 # External MCK from I2S pin "72"
    ext_freq = 48e3 * 1024 # External Xtal on PMOD pin "38" "29" "51"
    freq = ext_freq

    platform = ext_clock(freq, Platform)

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
