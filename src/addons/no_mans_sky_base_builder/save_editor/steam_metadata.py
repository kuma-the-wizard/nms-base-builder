"""Steam metadata codec, derived from libNOM.io's documented format/codec.

Copyright (c) Christian Engelhardt 2021; Python adaptation 2026.
SPDX-License-Identifier: GPL-3.0-only
Reference: https://github.com/zencq/libNOM.io (PlatformSteam_Read/Write.cs).
This is unrelated to, and contains no code from, TazMD's optimizer.
"""
import struct
import time

MASK = 0xffffffff
DELTA = 0x9e3779b9


def storage_number(filename):
    stem = filename.removeprefix('mf_').removesuffix('.hg')
    if not stem.startswith('save'):
        raise ValueError('Expected a Steam save filename')
    return (int(stem[4:]) if stem[4:] else 1) + 1


def crypt(data, storage, decrypt=False):
    if len(data) not in (360, 384, 432):
        raise ValueError('Unsupported Steam metadata version')
    values = list(struct.unpack('<%dI' % (len(data)//4), data))
    value = storage ^ 0x1422cb8c
    rotate = ((value << 13) | (value >> 19)) & MASK
    keys = [(rotate * 5 + 0xe6546b64) & MASK, *struct.unpack('<4I', b'NAESEVADNAYRTNRG')[1:]]
    def mix(y, z, total, index):
        return ((((y >> 3) ^ (z << 4)) + ((y << 2) ^ (z >> 5))) ^ ((z ^ keys[(index & 3) ^ ((total >> 2) & 3)]) + (y ^ total))) & MASK
    total = (DELTA * 6) & MASK if decrypt else 0
    z = 0
    for _ in range(6):
        if decrypt:
            y = values[0]
            for i in range(len(values)-1, -1, -1):
                z = values[i-1] if i else values[-1]
                values[i] = (values[i] - mix(y,z,total,i)) & MASK
                y = values[i]
            total = (total - DELTA) & MASK
        else:
            total = (total + DELTA) & MASK
            for i in range(len(values)):
                y = values[(i+1) % len(values)]
                values[i] = (values[i] + mix(y,z,total,i)) & MASK
                z = values[i]
    return struct.pack('<%dI' % len(values), *values)


def decode(data, filename):
    first = storage_number(filename)
    for slot in [first] + [i for i in range(2,32) if i != first]:
        plain = crypt(data, slot, True)
        if struct.unpack_from('<I', plain)[0] == 0xeeeeeebe:
            return plain
    raise ValueError('Could not decrypt Steam save metadata')


def rebuild(data, source, destination, compressed_size, decompressed_size, name=None):
    plain = bytearray(decode(data, source))
    struct.pack_into('<I', plain, 56, decompressed_size)
    if len(plain) >= 384:
        struct.pack_into('<I', plain, 60, compressed_size)
        struct.pack_into('<I', plain, 356, int(time.time()))
    if name is not None:
        encoded = name.encode('utf8')
        if len(encoded) > 127:
            raise ValueError('Save name is too long')
        plain[88:216] = encoded + bytes(128-len(encoded))
    encrypted = crypt(plain, storage_number(destination))
    if decode(encrypted, destination) != plain:
        raise ValueError('Metadata verification failed')
    return encrypted
