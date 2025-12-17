
from amaranth import *
from amaranth.utils import bits_for
from amaranth.build import ResourceError

from streams import Stream, Join, Sink, Arbiter, Tee, Split
from streams.spi import SpiPeripheral
from streams.i2s import I2SRxClock, I2STxClock, I2SInputLR, I2SOutput
from streams.route import Router, Select
from streams.spdif import SPDIF_Tx, SPDIF_Rx
from streams.monitor import Monitor
from streams.ws2812 import LedStream
from streams.ops import Enumerate

from gpio import GpioOut, GpioIn

from ppm import StereoAbs, PPM, BarGraph

audio = 16
audio_layout = [("data", audio)]
control = 32
control_layout = [("data", control)]
left_layout = [("left", audio)]
right_layout = [("right", audio)]
stereo_layout = left_layout + right_layout
led_layout = [("addr", 8), ("r", 8), ("g", 8), ("b", 8), ]

#
#

class TR:
    # Top-level Router 
    GPIO = 0
    LED = 1
    SELECT = 2
    MONITOR = 6
    AUX = 15
    KEYS = 16

routes = [
    #TR.GPIO,
    TR.LED,
    #TR.MONITOR,
    #TR.SELECT,
    TR.AUX,
    TR.KEYS,
]

#
#

class UI(Elaboratable):

    KEY_SW = 0x01
    KEY_A  = 0x02
    KEY_B  = 0x04

    def __init__(self, chans=5):
        keys = 3
        leds = 8
        bright = 0xff
        self.nkeys = keys
        self.chans = chans
        self.bright = bright

        self.keys = Stream(layout=[("data", keys)], name="keys")
        self.i = Stream(layout=led_layout, name="i")
        self.o = Stream(layout=led_layout, name="o")

        self.key_state = Signal(keys)

        self.channel = Signal(range(chans))
        self.edit = Signal(range(chans))
        self.edit_mode = Signal()

        self.leds = leds
        self.led = Signal(range(leds+1))
        self.update = Signal()

    def elaborate(self, _):
        m = Module()

        with m.If(self.o.valid & self.o.ready):
            m.d.sync += self.o.valid.eq(0)
        with m.If(~self.i.ready):
            m.d.sync += self.i.ready.eq(1)
        with m.If(self.i.valid & self.i.ready):
            m.d.sync += self.i.ready.eq(0)
            # copy in to out, unless in edit_mode
            with m.If(~self.edit_mode):
                m.d.sync += self.o.valid.eq(1)
                m.d.sync += self.o.payload_eq(self.i.cat_payload(flags=True), flags=True)

        # Update LED output with the edit_mode state
        with m.If(self.update | self.led):
            with m.If(~self.o.valid):
                m.d.sync += [
                    self.o.valid.eq(1),
                    self.o.first.eq(self.led==0),
                    self.o.last.eq(self.led==(self.leds-1)),
                    self.o.addr.eq(self.led),
                    self.o.r.eq(0),
                    self.o.g.eq(0),
                    self.o.b.eq(0),

                    self.led.eq(self.led + 1),
                    self.update.eq(0),
                ]
                with m.If(self.led == self.channel):
                    m.d.sync += self.o.r.eq(self.bright)
                with m.If(self.led == self.edit):
                    m.d.sync += self.o.g.eq(self.bright)

                with m.If(self.led == (self.leds-1)):
                    m.d.sync += self.led.eq(0)

        with m.If((~self.keys.ready) & (self.led == 0)):
            m.d.sync += self.keys.ready.eq(1)

        key_on = Signal(self.nkeys)
        key_off = Signal(self.nkeys)
        key_diff = Signal(self.nkeys)
        m.d.comb += [
            key_on.eq(self.keys.data & ~self.key_state),
            key_off.eq(self.key_state & ~self.keys.data),
            key_diff.eq(self.key_state ^ self.keys.data),
        ]

        with m.If(self.keys.valid & self.keys.ready):
            m.d.sync += self.keys.ready.eq(0)
            m.d.sync += self.key_state.eq(self.keys.data)
            # process key input
            with m.If(self.edit_mode):
                # in edit mode
                with m.If(key_on & self.KEY_SW):
                    # enter the selection, exit edit_mode
                    m.d.sync += [
                        self.channel.eq(self.edit),
                        self.edit_mode.eq(0),
                    ]
                with m.If(key_on & self.KEY_A):
                    # change the channel
                    m.d.sync += [
                        self.update.eq(1),
                    ]
                    with m.If(self.keys.data & self.KEY_B):
                        # increment edit channel
                        with m.If(self.edit == (self.chans-1)):
                            m.d.sync += self.edit.eq(0)
                        with m.Else():
                            m.d.sync += self.edit.eq(self.edit + 1)
                    with m.Else():
                        # decrement edit channel
                        with m.If(self.edit == 0):
                            m.d.sync += self.edit.eq(self.chans - 1)
                        with m.Else():
                            m.d.sync += self.edit.eq(self.edit - 1)

            with m.Else():
                # currently in pass-thru mode
                with m.If(key_on & self.KEY_SW):
                    # switch to edit_mode
                    m.d.sync += [
                        self.edit_mode.eq(1),
                        self.edit.eq(self.channel),
                        self.update.eq(1),
                    ]

        return m

#
#

class Meter(Elaboratable):

    def __init__(self, thresholds=[]):
        self.mods = []
        self.connects = []

        led_width = 8
        bar_len = len(thresholds)
        bar_layout = [("data", led_width)]
        self.i = Stream(layout=stereo_layout, name="i")

        self.abs = StereoAbs(layout=stereo_layout)
        self.mods += [ self.abs ]
        self.connects += [ (self.i, self.abs.i) ]

        self.ppm = PPM(layout=audio_layout)
        self.mods += [ self.ppm ]
        self.connects += [ (self.abs.o, self.ppm.i) ]

        self.bars = BarGraph(iwidth=audio, owidth=led_width, thresholds=thresholds)
        self.mods += [ self.bars ]
        self.connects += [ (self.ppm.o, self.bars.i) ]

        self.enum = Enumerate(idx=[("addr", bits_for(bar_len-1))], layout=bar_layout, offset=0)
        self.mods += [ self.enum ]
        self.connects += [ (self.bars.o, self.enum.i) ]
 
        layout = self.enum.o.get_layout()
        self.o = Stream(layout=layout, name="o")
        self.connects += [ (self.enum.o, self.o) ]

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mods

        for a, b in self.connects:
            m.d.comb += Stream.connect(a, b)

        return m

#
#

class AudioSelector(Elaboratable):

    def __init__(self, freq):
        self.sys_ck = freq
        self.mods = []
        self.connects = []
        self.comb = []

        self.in_arb = Arbiter(layout=control_layout, n=2)
        self.mods += [ self.in_arb ]

        self.ci = Stream(layout=control_layout, name="ci")
        self.connects += [ (self.ci, self.in_arb.i[0]) ]

        self.spi = SpiPeripheral(width=control, last_cs=True)
        self.mods += [ self.spi ]
        self.connects += [ (self.spi.o, self.in_arb.i[1]) ]

        sink = True
        self.router = Router(layout=control_layout, addr_field="data", addrs=routes, sink=sink)
        self.mods += [ self.router ]
        self.connects += [ (self.in_arb.o, self.router.i) ]

        if TR.GPIO in routes:
            self.gpio_led = GpioOut(8, name="gpio.led")
            self.mods += [ self.gpio_led ]
            self.connects += [ (self.router.o[TR.GPIO], self.gpio_led.i) ]

        self.gpio_aux = GpioOut(4, name="gpio.aux")
        self.mods += [ self.gpio_aux ]
        self.connects += [ (self.router.o[TR.AUX], self.gpio_aux.i) ]

        if TR.SELECT in routes:
            self.gpio_select = GpioOut(4, name="gpio.select")
            self.mods += [ self.gpio_select ]
            self.connects += [ (self.router.o[TR.SELECT], self.gpio_select.i) ]

        led_device = "ws2812" # "yf923"
        self.ws2812 = LedStream(N=8, sys_ck=freq, device=led_device)
        self.mods += [ self.ws2812 ]

        self.led_arb = Arbiter(layout=led_layout, n=2)
        self.mods += [ self.led_arb ]
        led_src = self.led_arb.o
 
        self.comb += self.ws2812.connect(self.router.o[TR.LED], self.led_arb.i[0])

        self.i2s_rxck = I2SRxClock(width=32, owidth=16)
        self.mods += [ self.i2s_rxck ]

        self.i2s_txck = I2STxClock(width=16)
        self.mods += [ self.i2s_txck ]

        adcs = 4
        spdif_in = True
        selects = adcs
        if spdif_in:
            selects += 1

        self.l_select = Select(layout=[("data", audio)], n=selects, wait_last=False, sink=True)
        self.mods += [ self.l_select ]
        self.r_select = Select(layout=[("data", audio)], n=selects, wait_last=False, sink=True)
        self.mods += [ self.r_select ]

        self.i2si = []
        for i in range(adcs):
            label = f"i2s{i}"
            s = I2SInputLR(width=audio, rx_clock=self.i2s_rxck)
            self.mods += [ s ]
            setattr(self, label, s)
            self.i2si.append(s)

            self.connects += [ 
                (s.left, self.l_select.i[i]),
                (s.right, self.r_select.i[i]),
            ]

        self.join = Join(left=left_layout, right=right_layout)
        self.mods += [ self.join ]
        self.connects += [ (self.l_select.o, self.join.left, [], {"data":"left"}) ]
        self.connects += [ (self.r_select.o, self.join.right, [], {"data":"right"}) ]

        self.tee = Tee(layout=stereo_layout, n=3, wait_all=True)
        self.mods += [ self.tee ]
        self.connects += [ (self.join.o, self.tee.i), ]

        self.spdif = SPDIF_Tx(iwidth=audio)
        self.mods += [ self.spdif ]
        self.connects += [ (self.tee.o[0], self.spdif.i), ]

        self.i2so = I2SOutput(width=16, tx_clock=self.i2s_txck)
        self.mods += [ self.i2so ]
        self.connects += [ (self.tee.o[1], self.i2so.i), ]

        thresholds = [ 4, 0x10, 0x80, 0x200, 0x800, 0x1000, 0x2000, 0x4000, 0x7fff  ]
        self.meter = Meter(thresholds=thresholds)
        self.mods += [ self.meter ]
        self.connects += [ (self.tee.o[2], self.meter.i) ]
        def dim(m, si, so):
            def _dim(name, src, dst):
                with m.If(si.addr >= 4):
                    m.d.sync += [
                        so.r.eq(src),
                        so.g.eq(0),
                    ]
                with m.Else():
                    m.d.sync += [
                        so.g.eq(src),
                        so.r.eq(0),
                    ]
                return []
            return _dim
        self.connects += [
            (self.meter.o, self.led_arb.i[1], ["g","b"], {"data":"g"}, {"data":dim}),
        ]

        if TR.KEYS in routes:
            self.gpio_ui = GpioIn(3, name="gpio.ui")
            self.mods += [ self.gpio_ui ]

            key_layout = self.gpio_ui.o.get_layout()
            self.key_arb = Arbiter(layout=key_layout, n=2) 
            self.mods += [ self.key_arb ]
            self.connects += [ (self.router.o[TR.KEYS], self.key_arb.i[0]) ]
            self.connects += [ (self.gpio_ui.o, self.key_arb.i[1]) ]

            self.ui = UI()
            self.mods += [ self.ui ]
            self.connects += [ (self.key_arb.o, self.ui.keys) ]
            self.connects += [ (self.led_arb.o, self.ui.i) ]
            led_src = self.ui.o

        self.connects += [ (led_src, self.ws2812.i) ]

        if spdif_in:
            self.rx = SPDIF_Rx()
            self.mods += [ self.rx ]
            self.rx_split = Split(layout=stereo_layout)
            self.mods += [ self.rx_split ]
            # truncate 20-bit audio to 16-bit
            def to16_l(m,a,b):
                def trunc(name, src, dst):
                    s = Signal(audio)
                    m.d.comb += s.eq(src)
                    return [ dst.eq(s >> 4) ]
                return trunc
            def to16_r(m,a,b):
                def trunc(name, src, dst):
                    s = Signal(signed(audio))
                    m.d.comb += s.eq(src)
                    return [ dst.eq(s >> 4) ]
                return trunc
            self.connects += [ 
                (self.rx.audio, self.rx_split.i, ["good"], {}, {"left":to16_l,"right":to16_r}),
                (self.rx_split.left, self.l_select.i[selects-1], [], {"left":"data"}),
                (self.rx_split.right, self.r_select.i[selects-1], [], {"right":"data"}),
            ]

        if TR.MONITOR in routes:
            self.monitor = Monitor(layout=audio_layout, n=8)
            self.mods += [ self.monitor ]
            self.connects += [ (self.router.o[TR.MONITOR], self.monitor.ci) ]

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mods

        for x in self.connects:
            a, b = x[:2]
            ex = x[2:3] or ([],)
            mm = x[3:4] or ({},)
            fn = x[4:5] or ({},)
            for k,v in fn[0].items():
                fn[0][k] = v(m, a, b)
            ex, mm, fn = ex[0], mm[0], fn[0]
            print(a, b, ex, mm, [ f"{k}:{v.__name__}" for k,v in fn.items() ])
            m.d.comb += Stream.connect(a, b, exclude=ex, mapping=mm, fn=fn)

        for eq in self.comb:
            m.d.comb += eq

        # The channel selection
        m.d.comb += [
            self.l_select.select.eq(self.ui.channel),
            self.r_select.select.eq(self.ui.channel),
        ]

        if hasattr(self, "monitor"):
            mons = [
                ("spi.o", self.spi.o, {}),
                ("gpio_ui.o", self.gpio_ui.o, {}),
                ("router.i", self.router.i, {}),
                #("gpio.led.i", self.gpio_led.i, {}),
                ("i2si[0].o", self.i2si[0].left, {}),
                ("l_select.i[0]", self.l_select.i[0], {}),
                ("l_select.i[1]", self.l_select.i[1], {}),
                ("l_select.i[2]", self.l_select.i[2], {}),
                #("l_select.i[3]", self.l_select.i[3], {}),
                ("l_select.o", self.l_select.o, {}),
                #("join.o", self.join.o, {"data":"left"}),
                #("meter.o", self.meter.o, {}),
            ]

            for idx, (name, s, mm) in enumerate(mons):
                m.d.comb += self.monitor.tap(s, f"{idx}_" + name, idx, mm)

        # turning the rotational encoder can give a quadrature pulse ~ 4ms long
        debounce_freq = 1 / 4e-3
        clock_bits = bits_for(int(self.sys_ck / debounce_freq))
        counter = Signal(clock_bits)
        m.d.sync += counter.eq(counter + 1)
        # External Xtal is Fs * 1024
        # We need Fs * 128 for the SPDIF 2*clock signal
        m.d.comb += self.spdif.en.eq((counter & 0x07) == 0)
        # We need Fs * 64 for the I2S output 2*clock signal
        m.d.comb += self.i2s_txck.enable.eq((counter & 0x0f) == 0)

        self.debounce = Signal()
        m.d.sync += self.debounce.eq(counter == 0)

        # debounce (sample) clock for the UI buttons
        m.d.sync += self.gpio_ui.en.eq((counter & 0xffffffff) == 0)
 
        return m

#
#

class _System(AudioSelector):

    # Conect all the application specific io

    def elaborate(self, platform):
        m = super().elaborate(platform)

        if platform is None:
            # LiteX doesn't pass in a platform,
            # so use the Amaranth one for all the application
            # specific connections.
            platform = self.platform
            wrapper = platform.wrapper
            def from_i(s): return wrapper.from_migen(s)
            def to_o(s): return wrapper.from_amaranth(s)
        else:
            def from_i(s): return s.i
            def to_o(s): return s.o

        spi = platform.request("spi", 0)

        m.d.comb += [
            self.spi.phy.scs.eq(from_i(spi.cs)),
            self.spi.phy.sck.eq(from_i(spi.sck)),
            self.spi.phy.copi.eq(from_i(spi.copi)),
        ]

        spdif = platform.request("spdif", 0)
        m.d.comb += self.spdif.aux.eq(self.gpio_aux.o)

        if hasattr(self, "rx"):
            m.d.comb += self.rx.i.eq(spdif.rx.i)
            idx = len(self.l_select.i) - 1
            with m.If(self.ui.channel == idx):
                # spdif input to the output
                m.d.comb += spdif.tx.o.eq(spdif.rx.i)
            with m.Else():
                m.d.comb += spdif.tx.o.eq(self.spdif.o)
        else:
            m.d.comb += spdif.tx.o.eq(self.spdif.o)

        # I2S output monitor
        i2s = platform.request("i2s", 1)
        m.d.comb += [
            i2s.sck.o.eq(self.i2so.phy.sck),
            i2s.ws.o.eq(self.i2so.phy.ws),
            i2s.sd.o.eq(self.i2so.phy.sd),
        ]

        i2s = platform.request("i2s", 0)
        # connect the I2S timing to the rx_clock
        m.d.comb += [
            self.i2s_rxck.sck.eq(i2s.sck.i),
            self.i2s_rxck.ws.eq(i2s.ws.i),
        ]
        # connect the I2S data inputs
        for i, i2si in enumerate(self.i2si):
            s = getattr(i2s, f"d{i}")
            m.d.comb += i2si.i.eq(s.i)

        try:
            ws2812 = platform.request("ws2812", 0)
            m.d.comb += ws2812.o.eq(self.ws2812.o)
        except ResourceError as ex:
            print(ex)

        # connect the rotatry switch
        sw = platform.request("sw", 0)
        # invert the signals, so the switch gives 1 on press
        m.d.comb += self.gpio_ui.i.eq(~sw.i)

        if hasattr(self, "monitor"):
            s = self.monitor.o0
            sd = self.monitor.o0.data
        else:
            s = self.join.o
            sd = s.left

        test = platform.request("test", 0)
        m.d.comb += [
            test.o.eq(Cat(
                #self.spdif.o,
                #i2s.sck.i,
                #i2s.ws.i,
                #i2s.d0.i,
                #i2s.d1.i,
                #i2s.d2.i,
                #i2s.d3.i,
                #i2s.mck.i,
                s.valid,
                s.ready,
                #self.gpio_select.o,
                self.l_select.o.data,
                #s.first,
                #s.last,
                sd,
            )),
        ]

        return m

#
#

class System(_System):

    # Connect any board/platform specific io

    def elaborate(self, platform):
        m = super().elaborate(platform)

        # Connect the on-board LEDs to the GPIO
        i = 0
        leds = []
        while True:
            try:
                led = platform.request("led", i)
                leds.append(led.o)
                i += 1
            except ResourceError as ex:
                print("led error:", ex)
                break
        leds = Cat(leds)

        if hasattr(self, "gpio_led"):
            m.d.comb += leds.eq(Cat(self.gpio_led.o))
        else:
            m.d.comb += leds.eq(1 << self.l_select.select)

        return m

#
#

def get_resources(platform, lang="Amaranth"):
    from io_defs import set_platform
    from io_defs import make_i2s_o, make_spdif, make_spi, make_test
    from io_defs import make_clock, make_i2s_backplane, make_io

    set_platform(platform, lang=lang)

    try:
        family = platform.family
    except AttributeError:
        family = platform.devicename

    if family == "GW1NR-9C":
        # TangNano 9k
        pmod_spi   = ("pmod", 2)
        pmod_i2so  = ("pmod", 0)
        pmod_spdif = ("pmod", 0)
        pmod_i2si  = ("pmod", 1)
        pmod_test  = ("pmod", 4)
        pmod_sw    = ("pmod", 3) # 1V8 port

        r = []
        r += make_spi(conn=pmod_spi)
        r += make_test(conn=pmod_test)
        r += make_spdif(conn=pmod_spdif, idx=0)
        r += make_i2s_backplane(conn=pmod_i2si, idx=0)
        r += make_i2s_o(conn=pmod_i2so, idx=1)
        r += make_io("ws2812", idx=0, _pins="10", _dir="o", conn=pmod_spdif, v="3V3")
        r += make_clock(freq=49.152e6, _pin="10", name="ckext", conn=pmod_spi)
        r += make_io("sw", idx=0, _pins="4 3 2", _dir="i", conn=pmod_sw, v="1V8", pull="up")
        return r

    assert 0, (family, platform)

#   FIN
