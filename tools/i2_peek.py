import struct
from pathlib import Path
d = Path(__file__).resolve().parent.parent.joinpath("work/I2Languages.raw").read_bytes()
p = 0
def u32():
    global p; v = struct.unpack_from("<I", d, p)[0]; p += 4; return v
def align():
    global p; p = (p + 3) & ~3
def s():
    global p; n = u32(); v = d[p:p+n].decode("utf-8"); p += n; align(); return v
p = 12 + 4 + 12; name = s()
flags = [u32() for _ in range(3)]
n_terms = u32()
for _ in range(n_terms):
    term = s(); ttype = u32()
    langs = [s() for _ in range(u32())]
    nf = u32(); p += nf; align()
print("after terms at", p, "of", len(d))
import binascii
tail = d[p:]
print(binascii.hexlify(tail[:64]).decode())
i = 0
while i < len(tail) and i < 4000:
    print(repr(tail[i:i+120])); i += 120
