
import amaranth
from amaranth.hdl import _ast, _ir
from amaranth.back import verilog

# https://github.com/orbcode/orbtrace/blob/main/orbtrace/amaranth_glue/wrapper.py

import migen

from litex.soc.interconnect.stream import Endpoint, EndpointDescription

from pathlib import Path

class Wrapper(migen.Module):
    def __init__(self, platform, name = 'amaranth_wrapper'):
        self.platform = platform
        self.name = name

        self.m = amaranth.Module()

        self.connections = []
        self._map = {}

    def add_module(self, m):
        self.m.submodules += m

    def connect(self, migen_sig, amaranth_sig):
        print("connect", migen_sig, amaranth_sig, f"id={id(amaranth_sig)}")
        self.connections.append((migen_sig, amaranth_sig))

    def connect_domain(self, name):
        n = 'sync' if name == 'sys' else name

        setattr(self.m.domains, n, amaranth.ClockDomain(n))

        self.connect(migen.ClockSignal(name), amaranth.ClockSignal(n))
        self.connect(migen.ResetSignal(name), amaranth.ResetSignal(n))

    def from_amaranth(self, amaranth_sig):
        assert isintance(amaranth_sig, amaranth.Signal)
        tag = id(amaranth_sig)
        if tag in self._map:
            return self._map[tag]
        shape = amaranth_sig.shape()
        migen_sig = migen.Signal((shape.width, shape.signed), name = amaranth_sig.name)
        self._map[tag] = migen_sig

        self.connect(migen_sig, amaranth_sig)

        return migen_sig

    def from_migen(self, migen_sig):
        assert isinstance(migen_sig, migen.Signal)
        amaranth_sig = amaranth.Signal(amaranth.Shape(migen_sig.nbits, migen_sig.signed))

        self.connect(migen_sig, amaranth_sig)

        return amaranth_sig

    def get_instance(self):
        connections = {}

        for m, n in self.connections:
            print("zzz", m, n, f"id={id(n)}")
            for x in self.amaranth_name_map.items():
                print("xxx", x)
            name, direction = self.amaranth_name_map[n]
            s = f'{direction}_{name}'

            assert s not in connections, f'Signal {s} connected multiple times.'

            connections[s] = m

        return migen.Instance(self.name, **connections)

    def generate_verilog(self):

        ports = [n for m, n in self.connections]

        fragment = _ir.Fragment.get(self.m, None).prepare(ports = ports, hierarchy = (self.name,))

        v, _name_map = verilog.convert_fragment(fragment, name = self.name)
        netlist = _ir.build_netlist(fragment, name = self.name)

        self.amaranth_name_map = _ast.SignalDict((sig, (name, 'o' if name in netlist.top.ports_o else 'i')) for name, sig, _ in fragment.ports)

        for name, domain in fragment.fragment.domains.items():
            if domain.clk in self.amaranth_name_map:
                self.amaranth_name_map[amaranth.ClockSignal(name)] = self.amaranth_name_map[domain.clk]
            if domain.rst in self.amaranth_name_map:
                self.amaranth_name_map[amaranth.ResetSignal(name)] = self.amaranth_name_map[domain.rst]

        return v

    def do_finalize(self):
        verilog_filename = str(Path(self.platform.output_dir) / 'gateware' / f'{self.name}.v')

        with open(verilog_filename, 'w') as f:
            f.write(self.generate_verilog())

        self.platform.add_source(verilog_filename)

        self.specials += self.get_instance()

    def iface(self, ainterface, add=[], mapping={}):
        # create migen Interface proxying Amaranth Interface
        signals = {}
        layout = []

        def me(a): return a

        for (name,), flow, asig in ainterface.signature.flatten(ainterface):
            print(name, flow, asig)
            msig = self.from_amaranth(asig)
            fn = mapping.get(name, me)
            signals[name] = fn(msig)
            if flow == amaranth.lib.wiring.In(msig.nbits):
                dirn = migen.DIR_M_TO_S
            if flow == amaranth.lib.wiring.Out(msig.nbits):
                dirn = migen.DIR_S_TO_M
            layout.append((name, dirn, msig.nbits))

        for name, size, dirn in add:
            s = migen.Signal(size)
            layout.append((name, dirn, size))
            signals[name] = s

        record = migen.Record(layout=layout)

        for name, _, _ in layout:
            s = signals[name]
            print(name, s)
            setattr(record, name, s)

        return record

    def astream_to_migen(self, astream, src=True, exclude=[]):
        # return a LiteX Stream connected to the given Amaranth Stream
        up = migen.DIR_M_TO_S
        down = migen.DIR_S_TO_M
        if not src:
            up, down = down, up

        def populate(record, layout):
            for item in layout:
                name = item[0]
                if name in exclude:
                    continue
                if isinstance(item[1], list):
                    r = getattr(record, name)
                    populate(r, item[1]) # sublayout
                else:
                    x = getattr(astream, name)
                    y = self.from_amaranth(x)
                    setattr(record, name, y)

        payload_layout = []

        for name, size in astream.get_layout():
            payload_layout.append((name, size, up))

        desc = EndpointDescription(payload_layout)
        mstream = Endpoint(desc)
        layout = mstream.description.get_full_layout()
        populate(mstream, layout)
        return mstream

#   FIN
