#!/bin/env python

from litex_boards.targets.sipeed_tang_nano_9k import main
from litex_boards.targets.sipeed_tang_nano_9k import BaseSoC as _BaseSoC
from litex_boards.platforms.sipeed_tang_nano_9k import Platform

from litex.soc.integration.builder import Builder

import migen
import amaranth

#
#

from wrapper import Wrapper

class BaseSoC(_BaseSoC):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_wrapper()

    def add_wrapper(self):
        self.submodules.wrapper = Wrapper(platform=self.platform)
        self.wrapper.connect_domain('sys')

    def xx_add_dram_dma(self, name, reader=True, with_csr=True, fifo_buffered=False, with_events=False):

        port = self.get_dram_port()

        if reader:
            dma = LiteDRAMDMAReader(port, with_csr=with_csr, fifo_buffered=fifo_buffered)
        else:
            dma = LiteDRAMDMAWriter(port, with_csr=with_csr, fifo_buffered=fifo_buffered)
        setattr(self.submodules, name, dma)

        if with_events:
            # Add an EventManager to handle interrupts
            dma.ev = EventManager()
            dma.submodules += dma.ev
            dma.ev.done = EventSourceProcess(edge="rising")
            dma.ev.finalize()

            # Connect the 'done' interrupt
            done = dma._done.status[0]
            self.comb += dma.ev.done.trigger.eq(done)
            self.irq.add(name, use_loc_if_exists=True)

        return dma

    def add_wb(self, name, origin, size):
        # Export a Wishbone bus region to the Amaranth code

        from litex.soc.interconnect.wishbone import Interface
        from litex.soc.integration.soc import SoCRegion
        from modules import Bus

        wb = Interface()
        region = SoCRegion(origin=origin, size=size, cached=False)
        self.bus.add_slave(name=name, slave=wb, region=region)

        bus = Bus()
        self.wrapper.add_module(bus)

        more = [
            # Signals in LiteX but not Amaranth Wishbone bus
            ("cti", 3, migen.DIR_M_TO_S),
            ("bte", 2, migen.DIR_M_TO_S),
            ("err", 1, migen.DIR_S_TO_M)
        ]
        def addr(a):
            s = migen.Signal(a.nbits)
            self.comb += a.eq(migen.Cat(0, 0, s))
            return s
        mapping = {
            # Amaranth wb uses all 32 bits, LiteX drops the last 2
            'adr' : addr,
        }
        iface = self.wrapper.iface(bus.decoder.bus, add=more, mapping=mapping)
        self.comb += wb.connect(iface)
        return wb

#
#

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=Platform, description="LiteX SoC on Tang Nano 9K.")
    parser.add_target_argument("--flash",                action="store_true",      help="Flash Bitstream.")
    parser.add_target_argument("--sys-clk-freq",         default=27e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--bios-flash-offset",    default="0x0",            help="BIOS offset in SPI Flash.")
    parser.add_target_argument("--with-spi-sdcard",      action="store_true",      help="Enable SPI-mode SDCard support.")
    parser.add_target_argument("--with-video-terminal",  action="store_true",      help="Enable Video Terminal (HDMI).")
    parser.add_target_argument("--prog-kit",             default="openfpgaloader", help="Programmer select from Gowin/openFPGALoader.")
    parser.add_target_argument("--dot",  help="generator Stream graph of module")
    args = parser.parse_args()

    args.toolchain = 'apicula'
    args.cpu_type = 'serv'

    soc = BaseSoC(
        toolchain           = args.toolchain,
        sys_clk_freq        = args.sys_clk_freq,
        bios_flash_offset   = int(args.bios_flash_offset, 0),
        with_video_terminal = args.with_video_terminal,
        **parser.soc_argdict,
    )

    platform = soc.platform
    from audio_selector import _System, get_resources

    mod = _System(freq=args.sys_clk_freq)

    io = get_resources(platform, lang="LiteX")
    soc.platform.add_extension(io)

    # Add the connectors from the tang nano dock to the platform
    from tang_nano_dock import TangNanoDock
    for name, idx, pins in TangNanoDock.raw_connectors:
        print(name, idx, pins)
        assert name == "pmod"
        parts = pins.split()
        assert len(parts) == 10
        # chop the middle 2 pins out : not present in the LiteX maps
        pins = " ".join(parts[:4] + parts[-4:])
        platform.add_connector((f"{name}{idx}", pins))

    platform.wrapper = soc.wrapper
    mod.platform = platform

    soc.wrapper.add_module(mod)
    mod.do_connect(platform=None)


    if args.with_spi_sdcard:
        soc.add_spi_sdcard()

    #if False:
    #    fifo_buffered = False
    #    dma_rd = soc.add_dram_dma("dma_rd", reader=True, fifo_buffered=fifo_buffered, with_events=True)
    #    dma_wr = soc.add_dram_dma("dma_wr", reader=False, fifo_buffered=fifo_buffered, with_events=True)

    #pads_layout = [("clk", 1), ("cs_n", 1), ("mosi", 1), ("miso", 1)]
    #pads = migen.Record(pads_layout)
    #for name, width in pads_layout:
    #    setattr(pads, name, migen.Signal(width))
    #soc.add_spi_master(data_width=32, spi_clk_freq=1e6, pads=pads)

    # Add a Wishbone bus 
    # Add a Wishbone interface to the Amaranth code
    #engine_base = 0xb0000000
    #soc.add_constant("ENGINE_ADDRESS", engine_base)
    #wb = soc.add_wb(name="engine", origin=engine_base, size=0x10000)

    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)

    if args.load:
        prog = soc.platform.create_programmer(kit=args.prog_kit)
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

    if args.flash:
        prog = soc.platform.create_programmer(kit=args.prog_kit)
        prog.flash(0, builder.get_bitstream_filename(mode="flash", ext=".fs")) # FIXME
        # Axternal SPI programming not supported by gowin 'programmer_cli' now!
        # if needed, use openFPGALoader or Gowin programmer GUI
        if args.prog_kit == "openfpgaloader":
            prog.flash(int(args.bios_flash_offset, 0), builder.get_bios_filename(), external=True)

    if args.dot:
        from streams import dot
        dot_path = "/tmp/tangnano.dot"
        png_path = args.dot
        dot.graph(mod, dot_path, png_path)

#
#

if __name__ == "__main__":
    main()

# FIN
