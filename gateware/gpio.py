
from amaranth import *

from streams import Stream

#
#

class GpioIn(Elaboratable):

    def __init__(self, width, name="GpioIn"):
        self.name = name
        self.width = width
        self.i = Signal(width)
        self.en = Signal()
        self.o = Stream(layout=[("data", width),], name="o")

        # compare to last sent data
        self.prev = Signal(width, reset=-1)

    def elaborate(self, platform):
        m = Module()

        with m.If(self.o.valid & self.o.ready):
            m.d.sync += self.o.valid.eq(0)

        with m.If(self.en & ~self.o.valid):
            with m.If(self.i != self.prev):
                m.d.sync += [
                    self.o.valid.eq(1),
                    self.o.data.eq(self.i),
                    self.prev.eq(self.i),
                ]

        return m

#
#

class GpioOut(Elaboratable):

    def __init__(self, width, name="GpioOut"):
        self.name = name
        self.width = width
        self.o = Signal(width)
        self.i = Stream(layout=[("data", width),], name="i")

    def elaborate(self, platform):
        m = Module()

        with m.If(self.i.valid & self.i.ready):
            m.d.sync += [
                self.i.ready.eq(0),
                self.o.eq(self.i.data),
            ]

        with m.If(~self.i.ready):
            m.d.sync += self.i.ready.eq(1)

        return m

#   FIN
