"""產生 gameclicker.ico（寶藍底、白色游標、橘色點擊波紋）。不用 Pillow，只用 Python 內建的東西。
用法：python installer/make_icon.py"""
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUE, WHITE, ORANGE = (0x1E, 0x3A, 0x8A), (0xFF, 0xFF, 0xFF), (0xF5, 0x9E, 0x0B)
ARROW = [(0.34, 0.24), (0.34, 0.80), (0.48, 0.66), (0.58, 0.88), (0.69, 0.83), (0.59, 0.62), (0.77, 0.62)]
TIP = ARROW[0]


def inside_poly(x, y, poly):
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def in_round_rect(x, y, r=0.2):
    cx, cy = min(max(x, r), 1 - r), min(max(y, r), 1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r and 0 <= x <= 1 and 0 <= y <= 1


def sample(x, y):
    """回傳 (顏色, 是否在圖示內)；座標 0~1。"""
    if not in_round_rect(x, y):
        return None
    d = ((x - TIP[0]) ** 2 + (y - TIP[1]) ** 2) ** 0.5
    if inside_poly(x, y, ARROW):
        return WHITE
    if 0.15 <= d <= 0.20 or 0.26 <= d <= 0.30:
        return ORANGE
    return BLUE


def render(size, ss=3):
    rows = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = sample((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    if c:
                        r, g, b, a = r + c[0], g + c[1], b + c[2], a + 1
            n = ss * ss
            row += bytes((r // a, g // a, b // a, a * 255 // n)) if a else b"\0\0\0\0"
        rows.append(bytes(row))
    return rows


def png(size, rows):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    raw = b"".join(b"\0" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def main():
    sizes = [16, 32, 48, 256]
    blobs = [png(s, render(s)) for s in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset, entries = 6 + 16 * len(sizes), b""
    for s, blob in zip(sizes, blobs):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path = os.path.join(ROOT, "gameclicker.ico")
    with open(path, "wb") as f:
        f.write(head + entries + b"".join(blobs))
    print("已產生", path)


if __name__ == "__main__":
    main()
