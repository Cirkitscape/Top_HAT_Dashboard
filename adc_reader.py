import time
from smbus2 import SMBus

I2C_BUS_NUM = 1
ADS_ADDR = 0x49
REG_CONV   = 0x00
REG_CONFIG = 0x01

PGA = {0:6.144, 1:4.096, 2:2.048, 3:1.024, 4:0.512, 5:0.256}
MUX_SINGLE = {0:0b100, 1:0b101, 2:0b110, 3:0b111}

def _twos_comp_12(x: int) -> int:
    x &= 0x0FFF
    return x - 0x1000 if (x & 0x0800) else x

def _build_config(mux_code: int, pga_code: int, dr_code: int) -> int:
    cfg  = (1 << 15)
    cfg |= (mux_code & 0x7) << 12
    cfg |= (pga_code & 0x7) << 9
    cfg |= (1 << 8)
    cfg |= (dr_code & 0x7) << 5
    cfg |= 0b11
    return cfg

def ads1015_read_single(bus: SMBus, addr: int, chan: int, pga_code: int = 1, dr_code: int = 4):
    mux = MUX_SINGLE[chan]
    cfg = _build_config(mux, pga_code, dr_code)
    bus.write_i2c_block_data(addr, REG_CONFIG, [(cfg >> 8) & 0xFF, cfg & 0xFF])

    # Wait for conversion
    t0 = time.time()
    while True:
        hi, _ = bus.read_i2c_block_data(addr, REG_CONFIG, 2)
        if hi & 0x80: break
        if time.time() - t0 > 0.05: break

    hi, lo = bus.read_i2c_block_data(addr, REG_CONV, 2)
    raw16 = (hi << 8) | lo
    raw12 = _twos_comp_12(raw16 >> 4)
    fs = PGA[pga_code]
    volts = (raw12 / 2048.0) * fs
    return raw12, volts

def read_all_channels():
    with SMBus(I2C_BUS_NUM) as bus:
        readings = {}
        for ch in range(4):
            _, v = ads1015_read_single(bus, ADS_ADDR, ch)
            readings[f"AIN{ch}"] = round(v, 4)
        return readings
