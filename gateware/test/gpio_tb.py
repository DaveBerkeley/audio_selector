#!/bin/env python

import sys

from amaranth import *
from amaranth.sim import *

sys.path.append(".")
sys.path.append("streams/streams")

from streams.stream import Stream
from streams.sim import SinkSim, SourceSim

from gpio import GpioIn

def load_packet(s, t, packet):
    for i, data in enumerate(packet):
        s.push(t, data=data, first=(i==0), last=(i == (len(packet)-1)))

#
#

def sim_gpio_in(m):
    print("test gpio_in")
    sim = Simulator(m)

    sink = SinkSim(m.o)

    polls = [ sink ]

    info = {
        'ck' : 0,
    }

    def tick(n=1):
        assert n
        for i in range(n):
            yield Tick()
            for poll in polls:
                yield from poll.poll()
            info['ck'] += 1
            if info['ck'] == 4:
                info['ck'] = 0
                yield m.en.eq(1)
            else:
                yield m.en.eq(0)

    def proc():

        data = [
            0,
            1,
            0,
            2,
            0,
            4,
            0,
            1,
            3,
            7,
        ]

        yield from tick(10)

        for d in data:
            yield m.i.eq(d)
            yield from tick(10)

        yield from tick(10)

        d = sink.get_data("data")[0]
        assert d == data, (d, data)

    sim.add_clock(1 / 50e6)
    sim.add_process(proc)
    with sim.write_vcd("gtk/gpio_in.vcd", traces=[]):
        sim.run()

#
#

if __name__ == "__main__":
    do_all = True
    if do_all:
        dut = GpioIn(width=3)
        sim_gpio_in(dut)

    from streams import dot
    dot_path = "/tmp/wifi.dot"
    png_path = "test.png"
    dot.graph(dut, dot_path, png_path)

#   FIN
