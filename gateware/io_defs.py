#
#   Target agnostic resource definitions
#
#   TODO : make this work in LiteX as well as Amaranth

import sys

import amaranth.build as ab

#
#

family = None
hdl_lang = None
device = None
package = None

def device_to_family(device):
    if device == "GW1NR-LV9QN88PC6/I5":
        return "GW1NR-9C", "QN88P"
    assert 0, device

def set_platform(platform, lang="Amaranth"):
    global family, hdl_lang, device, package
    if hasattr(platform, "family"):
        family = platform.family
    else:
        family = platform.device_family
    hdl_lang = lang
    device = platform.device
    if family is None:
        family, package = device_to_family(device)

    if package is None:
        if hasattr(platform, "package"):
            package = platform.package
    print(f"family={family} device={device}, package={package}, hdl_lang={hdl_lang}")

#
#

def attrs(*args, **kwargs):
    if hdl_lang == "Amaranth":
        return ab.Attrs(**kwargs)
    if hdl_lang == "LiteX":
        from litex.build.generic_platform import IOStandard, Misc
        d = kwargs
        name = d['IO_TYPE']
        del d['IO_TYPE']
        fn = IOStandard(name)
        if d:
            assert len(d) == 1
            (k, v), = d.items()
            fn = fn, Misc(f"{k}={v}")
        return fn

    assert 0, (hdl_lang, args, kwargs)

def resource(*args, **kwargs):
    if hdl_lang == "Amaranth":
        return ab.Resource(*args, **kwargs)
    if hdl_lang == "LiteX":
        return args
    assert 0, (hdl_lang, args, kwargs)

def subsignal(name, pins):
    if hdl_lang == "Amaranth":
        return ab.Subsignal(name, pins)
    if hdl_lang == "LiteX":
        from litex.build.generic_platform import Subsignal
        return Subsignal(name, pins)
    assert 0, (hdl_lang, name, pins)

def pins(pins, dir=None, conn=None, **kwargs):
    if hdl_lang == "Amaranth":
        return ab.Pins(pins, dir=dir, conn=conn, **kwargs)
    if hdl_lang == "LiteX":
        if conn:
            name = f"{conn[0]}{conn[1]}"
            if name.startswith("pmod"):
                # Numbering differs between LiteX and Amaranth!
                # TODO : Need to have a standard way of expressing these!
                pins = [ int(p) for p in pins.split() ]
                for i, p in enumerate(pins):
                    pins[i] = { 1:0, 2:1, 3:2, 4:3, 7:4, 8:5, 9:6, 10:7 }[p]
                pins = [ str(p) for p in pins ]
                
            pins = " ".join([ f"{name}:{pin}" for pin in pins ])
        from litex.build.generic_platform import Pins
        return Pins(pins)
    assert 0, (hdl_lang, pins, dir, conn, kwargs)

#
#

def get_attr(v=None, pull=None, opendrain=None, drive=None, diff=False, r=None, *args, **kwargs):
    #print(attr)
    io = {
        # Lattice chips at least
        "3V3" : "LVCMOS33",
        "2V5" : "LVCMOS25",
        "1V8" : "LVCMOS18",
        "LVDS" : "LVDS",
        "SLVS" : "SLVS",
    }

    # TODO : add facility for drive, opendrain etc.
    assert v in io, v
    assert opendrain is None # TODO
    assert drive is None # TODO

    if family == "ecp5":
        io_type = io[v]
        if diff:
            io_type += "D"
        d = {
            "IO_TYPE" : io_type,
        }
        if pull:
            d["PULLMODE"] = { "down" : "DOWN", "up" : "UP", }[pull]
        if r:
            label = {"LVDS":"DIFFRESISTOR"}.get(v, "TERMINATION")
            d[label] = r
        return attrs(**d)

    if family == "GW1NR-9C":
        # TangNano 9k
        io_type = io[v]
        d = {
            "IO_TYPE" : io_type,
        }
        if pull:
            d["PULLMODE"] = { "down" : "DOWN", "up" : "UP", }[pull]
        return attrs(**d)

    if hdl_lang == "LiteX":
        assert pull is None, (family, hdl_lang) # TODO
        return attrs(io[v])

    if family == "iCE40":
        io_type = io[v]
        d = {
            "IO_TYPE" : io_type,
        }
        if pull:
            d["PULLMODE"] = { "down" : "DOWN", "up" : "UP", }[pull]
        return attrs(IO_STANDARD=io[v])
 
    assert 0, family # TODO

#
#   Swap pins on top/bottom rows of a PMOD connector

def swap_pmod_row(other):
    def fn(pin):
        if not other:
            return pin
        return {
            "1" : "7",
            "2" : "8",
            "3" : "9",
            "4" : "10",
            "7" : "1",
            "8" : "2",
            "9" : "3",
            "10" : "4",
        }[pin]
    return fn

fn = swap_pmod_row(True)
assert fn("1") == "7"
assert fn("4") == "10"
assert fn("7") == "1"
assert fn("10") == "4"
fn = swap_pmod_row(False)
assert fn("1") == "1"
assert fn("4") == "4"
assert fn("7") == "7"
assert fn("10") == "10"

#
#

def make_spi(conn, idx=0, order="1 2 3 4", swap=False):
    swapfn = swap_pmod_row(swap)
    cs, sck, copi, cipo = [ swapfn(pin) for pin in order.split(' ') ]
    print(f"resource spi,{idx} {conn} cs={cs} sck={sck} copi={copi} cipo={cipo}")
    # SPI from PMOD/ESP32
    return [
        resource("spi", idx,
            subsignal("cs",  pins(cs,  dir="i", conn=conn)),
            subsignal("sck", pins(sck,  dir="i", conn=conn)),
            subsignal("copi", pins(copi, dir="i", conn=conn)),
            subsignal("cipo",  pins(cipo,  dir="o", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

def make_io(name, idx, _pins, _dir, conn=None, *args, **kwargs):
    conn_t = conn or ""
    print(f"resource {name},{idx} [{_pins}] {conn_t} {kwargs}")
    return [
        resource(name, idx, 
            pins(_pins, dir=_dir, conn=conn),
            get_attr(*args, **kwargs)
        ),
    ]

#
#

def make_lvds(_pins, _dir="o", idx=0):
    if family == "ecp5":
        # display the LVDS pairs
        import ecp5_pins
        pairs = ecp5_pins.read_pinout(ecp5_pins.path, "CABGA381")
        for needle in _pins.split():
            for p in pairs:
                if needle in p.split():
                    print(f"differential pair: {p}", file=sys.stderr)

    return make_io("lvds", idx, _pins, _dir, v="LVDS")

#
#

def make_sipeed_mics(conn, idx=0, with_sk9822=False):
    print(f"resource sipeed_mics {conn}")
    r = [
        # Sipeed Mic Array
        resource("mic", idx,
            subsignal("sck", pins("4",  dir="o", conn=conn)),
            subsignal("ws",  pins("10",  dir="o", conn=conn)),
            subsignal("d0",  pins("8",  dir="i", conn=conn)),
            subsignal("d1",  pins("2",  dir="i", conn=conn)),
            subsignal("d2",  pins("9",  dir="i", conn=conn)),
            subsignal("d3",  pins("3", dir="i", conn=conn)),
            subsignal("d4",  pins("7", dir="i", conn=conn)), # not in sipeed device
            subsignal("d5",  pins("1", dir="i", conn=conn)), # not in sipeed device
            get_attr(v="3V3"),
        ),
    ]
    if with_sk9822:
        r += [
            resource("sk9822", idx,
                subsignal("co", pins("7",  dir="o", conn=conn)),
                subsignal("do", pins("1",  dir="o", conn=conn)),
                get_attr(v="3V3"),
            ),
        ]
    return r

#
#

def make_i2s_backplane(conn, idx=0, controller=False):
    # I2S backplane board : I2S inputs
    print(f"resource i2s_backplane,{idx} {conn}")
    dirn = {True:"o", False:"i"}[controller]
    return [
        resource("i2s", idx,
            # pin 7 not used
            subsignal("ws",  pins("8",  dir=dirn, conn=conn)),
            subsignal("sck", pins("9",  dir=dirn, conn=conn)),
            subsignal("mck", pins("10", dir=dirn, conn=conn)),
            subsignal("d0",  pins("1",  dir="i", conn=conn)),
            subsignal("d1",  pins("2",  dir="i", conn=conn)),
            subsignal("d2",  pins("3",  dir="i", conn=conn)),
            subsignal("d3",  pins("4",  dir="i", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

#
#

def make_i2s_o(conn, idx=0, swap=False, slave=False, order="2 4 3"):
    pck, pws, psd = [ swap_pmod_row(swap)(x) for x in order.split(' ') ]
    print(f"resource i2so,{idx} {conn} sck={pck} ws={pws} sd={psd}")
    sdir = "o"
    if slave:
        sdir = "i"
    return [
        # I2S output
        resource("i2s", idx,
            # PCM5102A module has sysck then bck (which is our audio bit clock)
            subsignal("sck", pins(pck, dir=sdir, conn=conn)),
            subsignal("ws",  pins(pws, dir=sdir, conn=conn)),
            subsignal("sd",  pins(psd, dir="o", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

def make_pcm5102(conn, idx=0, swap=False, slave=False):
    return make_i2s_o(conn, idx, swap, slave=False, order="2 4 3")

def make_wm8782(conn, idx=0, master=False, swap=False):
    print(f"resource WM8782_i2s_adc,{idx} {conn}")
    dir = { True : "i", False : "o" }[master]
    row = swap_pmod_row(swap)
    return [
        # I2S output
        resource("i2s", idx,
            # WM8782 module : bck is the audio bit clock
            subsignal("mck", pins(row("1"), dir="i", conn=conn)),
            subsignal("ws",  pins(row("2"), dir=dir, conn=conn)),
            subsignal("sck", pins(row("3"), dir=dir, conn=conn)),
            subsignal("sd",  pins(row("4"), dir="i", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

def make_spdif(conn, idx=0, order="7 8", swap=False):
    rx, tx = [ swap_pmod_row(swap)(x) for x in order.split(' ') ]
    print(f"resource spdif,{idx} {conn} rx={rx} tx={tx}")
    return [
        resource("spdif", idx,
            subsignal("rx", pins(rx, dir="i", conn=conn)),
            subsignal("tx", pins(tx, dir="o", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

def make_test(conn, idx=0, dir="o", order="1 2 3 4 7 8 9 10"):
    print(f"resource test,{idx} {conn} [{order}]")
    return [
        resource("test", idx, 
            pins(order, dir=dir, conn=conn), 
            get_attr(v="3V3"),
        ),
    ]

def make_input(conn, idx=0, order="1 2 3 4 7 8 9 10"):
    print(f"resource input,{idx} {conn} [{order}]")
    return [
        Resource("input", idx, 
            Pins(order, dir="i", conn=conn), 
            get_attr(v="3V3"),
        ),
    ]

def make_uart(conn, idx=0, name="uart", rx=None, tx=None):
    print(f"resource uart,{idx} rx={conn}:{rx} tx={conn}:{tx}")
    return [
        resource(name, idx,
            subsignal("rx", pins(rx, dir="i", conn=conn)),
            subsignal("tx", pins(tx, dir="o", conn=conn)),
            get_attr(v="3V3"),
        ),
    ]

def make_uarts(conn, name="uart", uarts=None):
    print(f"resource uart,{name} {conn}:{uarts}")
    r = []
    for item in uarts:
        r += [ 
            resource(name, item["idx"],
                subsignal("rx", pins(item["rx"], dir="i", conn=conn)),
                subsignal("tx", pins(item["tx"], dir="o", conn=conn)),
                get_attr(v="3V3"),
            ),
        ]
    return r

def make_clock(conn, name, _pin=None, freq=None):
    print(f"resource external_clock {name} {conn} [{_pin}] freq={freq}")
    # TODO : does Litex have an equivalent for external clocks?
    from amaranth.build.dsl import Clock
    return [
        resource(name, 0, 
             pins(_pin, dir="i", conn=conn), 
             Clock(freq), 
             get_attr(v="3V3"),
        ),
    ]

#
#

def pmod(name, num):
    if hdl_lang == "LiteX":
        # 0->c, 1->d, 2->e ... 9->l
        return name, chr(ord('c') + num)
    if hdl_lang == "Amaranth":
        return name, num
    assert 0, "Unknown hdl_lang"

#   FIN
