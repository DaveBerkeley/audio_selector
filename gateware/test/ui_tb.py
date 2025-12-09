#!/bin/env python

import sys

from amaranth import *
from amaranth.sim import *

sys.path.append(".")
sys.path.append("streams/streams")

from streams.stream import Stream
from streams.sim import SinkSim, SourceSim

from audio_selector import UI

def load_packet(s, t, packet):
    for i, data in enumerate(packet):
        s.push(t, data=data, first=(i==0), last=(i == (len(packet)-1)))

#
#

def sim_ui(m):
    print("test ui")
    sim = Simulator(m)

    sink = SinkSim(m.o)
    src = SourceSim(m.keys)

    polls = [ sink, src ]

    def tick(n=1):
        assert n
        for i in range(n):
            yield Tick()
            for poll in polls:
                yield from poll.poll()

    def proc():

        keys = [
            0x1, 0x0, # edit mode
            0x2, 0x6, 0x4, 0x0, # down
            0x2, 0x6, 0x4, 0x0,
            0x2, 0x6, 0x4, 0x0,
            0x2, 0x6, 0x4, 0x0,
            0x2, 0x6, 0x4, 0x0,
            0x2, 0x6, 0x4, 0x0,
            0x1, 0x0, # select

            0x1, 0x0, # edit mode
            0x04, 0x06, 0x02, 0x00, # up
            0x04, 0x06, 0x02, 0x00,
            0x04, 0x06, 0x02, 0x00,
            0x04, 0x06, 0x02, 0x00,
            0x04, 0x06, 0x02, 0x00,
            0x04, 0x06, 0x02, 0x00,
            0x1, 0x0, # select
        ]

        t = 10
        for key in keys:
            load_packet(src, t, [ key ])
            t += 30

        yield from tick(10)

        while not src.done():
            yield from tick(1)

        yield from tick(10)

        def decode(p):
            #print(p)
            leds = [ 0, -1, -1, -1 ]
            for i, item in enumerate(p):
                assert i == item[0] # address
                for idx in range(1, 4):
                    if item[idx]:
                        assert leds[idx] == -1
                        leds[idx] = i
            #print(leds)
            assert leds[0] == 0 # addr
            assert leds[3] == -1 # blue
            return leds[1], leds[2] # r, g

        expects = [
            [ 0, 0 ],
            [ 0, 4 ],
            [ 0, 3 ],
            [ 0, 2 ],
            [ 0, 1 ],
            [ 0, 0 ],
            [ 0, 4 ],
            [ 4, 4 ],
            [ 4, 0 ],
            [ 4, 1 ],
            [ 4, 2 ],
            [ 4, 3 ],
            [ 4, 4 ],
            [ 4, 0 ],
        ]

        d = sink.get_data()
        for i, p in enumerate(d):
            def get(x):
                return x['addr'], x['r'], x['g'], x['b']
            x = [ get(a) for a in p ]
            r, g = decode(x)
            #print(r, g)
            assert [r, g] == expects[i]

    sim.add_clock(1 / 50e6)
    sim.add_sync_process(proc)
    with sim.write_vcd("gtk/ui.vcd", traces=[]):
        sim.run()

#
#

if __name__ == "__main__":
    do_all = True
    if do_all:
        dut = UI()
        sim_ui(dut)

    from streams import dot
    dot_path = "/tmp/wifi.dot"
    png_path = "test.png"
    dot.graph(dut, dot_path, png_path)

#   FIN
