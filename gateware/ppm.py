
from amaranth import *
from amaranth.utils import bits_for

from streams.stream import Stream, Split
from streams.ops import Abs, Decimate, UnaryOp, Delta, Max

from streams.ram import DualPortMemory

class Boxcar(Elaboratable):

    def __init__(self, width, depth):
        self.name = f"Boxcar({depth})"
        self.mem = DualPortMemory(width=width, depth=depth)
        self.mem.dot_dont_expand = True
        layout = [ ("data", width) ]
        self.i = Stream(layout=layout, name="i")
        self.o = Stream(layout=layout, name="o")

        delta_width = width + 1
        self.data = Signal(signed(width))
        self.prev = Signal(signed(width))
        self.delta = Signal(signed(delta_width))
        self.sum = Signal(signed(bits_for(depth) + width + 1))
        self.shift = bits_for(depth) - 1

        self.addr = Signal(range(depth))

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mem

        m.d.comb += [
            self.mem.rd.addr.eq(self.addr),
            self.mem.wr.addr.eq(self.addr),
            self.mem.wr.data.eq(self.data),
        ]

        with m.FSM(reset="IDLE"):

            with m.State("IDLE"):
                with m.If(~self.i.ready):
                    m.d.sync += self.i.ready.eq(1)

                with m.If(self.i.valid & self.i.ready):
                    # read data input
                    m.d.sync += [
                        self.i.ready.eq(0),
                        self.data.eq(self.i.data),  # latch the new data
                        self.prev.eq(self.mem.rd.data), # read the old data
                    ]
                    m.next = "WRITE"

            with m.State("WRITE"):
                m.d.sync += [
                    self.mem.wr.en.eq(1),
                    self.delta.eq(self.data - self.prev),
                ]
                m.next = "ADD"

            with m.State("ADD"):
                m.d.sync += [
                    self.mem.wr.en.eq(0),
                    self.sum.eq(self.sum + self.delta),
                    self.addr.eq(self.addr + 1),
                ]
                m.next = "OUT"

            with m.State("OUT"):
                m.d.sync += [
                    self.o.data.eq(self.sum >> self.shift),
                    self.o.valid.eq(1),
                ]
                m.next = "WAIT"

            with m.State("WAIT"):
                with m.If(self.o.valid & self.o.ready):
                    m.d.sync += [
                        self.o.valid.eq(0),
                        self.i.ready.eq(1),
                    ]
                    m.next = "IDLE"

        return m

#
#
#   'point' is the number of fractional bits used for the decay

class PeakHold(UnaryOp):

    def __init__(self, n, point=3, **kwargs):
        super().__init__(**kwargs)
        assert self.fields == ["data"]
        self.point = point
        width = self.i.get_layout()[0][1]
        self.peak = Signal(signed(width+point))
        self.peak_int = Signal(signed(width))
        self.data = Signal(signed(width))
        self.count = Signal(range(n))
        self.max = n - 1
 
    def op(self, m, name, si, so):
        with m.If(self.count == self.max):
            m.d.sync += [
                self.peak.eq(self.peak - self.peak_int),
            ]

        with m.If(self.data > self.peak_int):
            m.d.sync += [
                so.eq(self.data),
                self.peak.eq(self.data << self.point),
                self.count.eq(0),
            ]
        with m.Else():
            m.d.sync += [
                so.eq(self.peak_int),
                self.count.eq(self.count + 1),
            ]

    def elaborate(self, platform):
        m = UnaryOp.elaborate(self, platform)

        m.d.comb += [
            self.data.eq(self.i.data),
            self.peak_int.eq(self.peak >> self.point),
        ]

        return m

#
#

class StereoAbs(Elaboratable):

    def __init__(self, layout=None):

        self.i = Stream(layout=layout, name="i")
        width = layout[0][1]
        self.abs = Abs(layout=layout, fields=["left","right"])
        self.max = Max(iwidth=width, owidth=width)

        olayout = self.max.o.get_layout()
        self.o = Stream(layout=olayout, name="o")

        self.mods = [
            self.abs,
            self.max,
        ]

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mods

        m.d.comb += Stream.connect(self.i, self.abs.i)
        m.d.comb += Stream.connect(self.abs.o, self.max.i, mapping={"left":"a","right":"b"})
        m.d.comb += Stream.connect(self.max.o, self.o)

        return m

#
#

class PPM(Elaboratable):

    def __init__(self, layout=None, name="PPM"):
        # expects a 48kHz input signal, rectified by Abs()
        self.name = name
        width = layout[0][1]

        # 48kHz/512 ~ 10ms average
        self.rise = Boxcar(width, 512)
        self.decimate = Decimate(32, layout=layout)
        decay = int((1<<5)/width)
        self.peak = PeakHold(decay, point=8, name=f"PeakHold({decay})", layout=layout)
        # should have 2..3s decay for PPM
        self.delta = Delta(layout=layout)

        self.i = self.rise.i
        self.o = self.delta.o

        self.mods = [
            self.rise,
            self.decimate,
            self.peak,
            self.delta,
        ]

    def elaborate(self, platform):
        m = Module()

        m.submodules += self.mods

        m.d.comb += Stream.connect(self.rise.o, self.decimate.i)
        m.d.comb += Stream.connect(self.decimate.o, self.peak.i)
        m.d.comb += Stream.connect(self.peak.o, self.delta.i)

        return m

#
#

class Comparator(Elaboratable):

    def __init__(self, iwidth, owidth, name="Comparator"):
        layout = [ ("data", iwidth), ("hi", iwidth), ("lo", iwidth), ("mul", iwidth), ]
        self.i = Stream(layout=layout, name="i")
        self.o = Stream(layout=[("data", owidth)], name="o")

        self.max = (1 << owidth) - 1
        self.shift = iwidth - owidth
        self.calc = Signal(iwidth)
        self.mul = Signal(iwidth)
        self.pause = Signal()
        self.first = Signal()
        self.last = Signal()

    def elaborate(self, platform):
        m = Module()

        def tx(first, last, data):
           return [
                self.o.valid.eq(1),
                self.o.first.eq(first),
                self.o.last.eq(last),
                self.o.data.eq(data),
            ]

        with m.If(self.o.valid & self.o.ready):
            m.d.sync += [
                self.o.valid.eq(0),
                self.o.first.eq(0),
                self.o.last.eq(0),
                self.i.ready.eq(1),
            ]

        with m.If(~self.i.ready):
            with m.If(~self.o.valid):
                with m.If(~self.pause):
                    m.d.sync += self.i.ready.eq(1)

        with m.If(self.i.valid & self.i.ready):
            m.d.sync += [
                self.i.ready.eq(0),
                self.first.eq(self.i.first),
                self.last.eq(self.i.last),
                self.mul.eq(self.i.mul),
                self.calc.eq(self.i.data - self.i.lo),
            ]

            with m.If(self.i.data >= self.i.hi):
                m.d.sync += tx(self.i.first, self.i.last, self.max)
            with m.Elif(self.i.data <= self.i.lo):
                m.d.sync += tx(self.i.first, self.i.last, 0)
            with m.Else():
                with m.If(self.mul):
                    m.d.sync += self.pause.eq(1)
                with m.Else():
                    # we don't know the mul, so set the output to 1/2
                    m.d.sync += tx(self.i.first, self.i.last, self.max >> 1)

        with m.If(self.pause):
            m.d.sync += tx(self.first, self.last, (self.mul * self.calc) >> self.shift)
            m.d.sync += self.pause.eq(0)

        return m

#
#

class BarGraph(Elaboratable):

    def __init__(self, iwidth, owidth, thresholds=None, name=None):
        assert thresholds
        assert len(thresholds) > 1
        self.n = len(thresholds) - 1
        self.name = name or f"BarGraph({self.n})"
        self.end = self.n - 1
        self.max = (1 << owidth) - 1
        self.loss = (iwidth - owidth) - 1
        assert self.loss

        self.i = Stream(layout=[("data", iwidth)], name="i")
        self.data = Signal(iwidth)

        self.cmp = Comparator(iwidth, owidth)

        self.lo = Array(thresholds[:-1])
        self.hi = Array(thresholds[1:])
        mul = list([ self.mul(thresholds[i], thresholds[i+1]) for i in range(len(thresholds)-1) ])
        self.mul = Array(mul)

        self.idx = Signal(range(self.n + 1))
        self.send = Signal()

        self.o = self.cmp.o

        self.mods = [
            self.cmp,
        ]

    def mul(self, lo, hi):
        mul = int((self.max / (hi-lo)) * (1 << self.loss))
        return mul

    def elaborate(self, platform):
        m = Module()
        m.submodules += self.mods

        with m.If((~self.send) & ~self.i.ready):
            m.d.sync += self.i.ready.eq(1)

        with m.If(self.i.valid & self.i.ready):
            # read data, enable packet creation
            m.d.sync += [
                self.i.ready.eq(0),
                self.data.eq(self.i.data),
                self.send.eq(1),
                self.idx.eq(0),
            ]

        with m.If(self.cmp.i.valid & self.cmp.i.ready):
            m.d.sync += self.cmp.i.valid.eq(0)

        with m.If(self.send & self.cmp.i.ready & ~self.cmp.i.valid):
            # can send the next part of the packet
            m.d.sync += [
                self.cmp.i.valid.eq(1),
                self.cmp.i.first.eq(self.idx == 0),
                self.cmp.i.last.eq(self.idx == self.end),
                self.cmp.i.data.eq(self.data),
                self.cmp.i.lo.eq(self.lo[self.idx]),
                self.cmp.i.hi.eq(self.hi[self.idx]),
                self.cmp.i.mul.eq(self.mul[self.idx]),
                self.idx.eq(self.idx + 1),
            ]

        with m.If(self.send & (self.idx == self.n)):
            m.d.sync += self.send.eq(0)

        return m

#
#

class KeyOnOff(Elaboratable):

    def __init__(self, width):
        self.i = Stream(layout=[ ("data", width) ], name="i")
        self.o = Stream(layout=[ ("data", width), ("state", 1) ], name="o")
        self.state = Signal(width)
        self.diff = Signal(width)
        self.mask = Signal(width)

    def elaborate(self, platform):
        m = Module()

        with m.FSM(reset="IDLE"):

            with m.State("IDLE"):

                with m.If(~self.i.ready):
                    m.d.sync += self.i.ready.eq(1)

                with m.If(self.i.ready & self.i.valid):
                    m.d.sync += [
                        self.diff.eq(self.state ^ self.i.data),
                        self.state.eq(self.i.data),
                        self.i.ready.eq(0),
                        self.o.first.eq(1),
                    ]
                    m.next = "CALC"

            with m.State("CALC"):

                with m.If(self.diff):
                    m.d.sync += self.mask.eq(self.diff & -self.diff)
                    m.next = "SEND"
                with m.Else():
                    m.d.sync += self.i.ready.eq(1)
                    m.next = "IDLE"

            with m.State("SEND"):

                with m.If(~self.o.valid):
                    m.d.sync += [
                        self.o.valid.eq(1),
                        self.o.data.eq(self.mask),
                        self.o.last.eq(self.diff == self.mask),
                        self.diff.eq(self.diff & ~self.mask),
                    ]
                    with m.If(self.mask & self.state):
                        m.d.sync += self.o.state.eq(1)
                    with m.Else():
                        m.d.sync += self.o.state.eq(0)

                with m.If(self.o.valid & self.o.ready):
                    m.d.sync += [
                        self.o.valid.eq(0),
                        self.o.first.eq(0),
                    ]
                    with m.If(self.diff == 0):
                        m.d.sync += self.i.ready.eq(1)
                        m.next = "IDLE"
                    with m.Else():
                        m.next = "CALC"

        return m

#   FIN
