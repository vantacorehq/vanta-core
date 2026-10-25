"""VANTA data generator: asyncio.Protocol byte-stream simulator + HTTP metrics endpoint."""
import asyncio, collections, json, math, os, random, time
from dataclasses import dataclass

_NONPRINT = bytes(i for i in range(256) if not 32 <= i < 127)

@dataclass(slots=True)
class Chunk:
    seq: int; data: bytes; entropy: float; printable: int; density: float; fmt_ok: bool; ts: float

def shannon(b: bytes) -> float:
    n = len(b)
    if not n: return 0.0
    return -sum(c / n * math.log2(c / n) for c in collections.Counter(b).values())

def analyse(seq: int, data: bytes) -> Chunk:
    """Local text-formatting analysis: char counting + hex round-trip validation."""
    hx = data.hex()
    ok = len(hx) == 2 * len(data) and bytes.fromhex(hx) == data
    printable = len(data) - len(data.translate(None, _NONPRINT))
    ent = shannon(data)
    return Chunk(seq, data, ent, printable, (ent / 8.0) * 0.7 + (printable / max(1, len(data))) * 0.3, ok, time.monotonic())

class Metrics:
    def __init__(self):
        self.tp = self.base = 1.0; self.entropy = self.density = 0.0
        self.accepted = self.rejected = self.bytes = 0; self.last = time.monotonic()
        self.hist = [0.0] * 16
    @property
    def spike(self) -> float:
        return max(0.0, min(1.0, (self.tp - self.base) / max(self.base, 1.0)))
    def update(self, size: int, entropy: float, density: float):
        now = time.monotonic(); dt = max(now - self.last, 1e-4); self.last = now
        self.tp += 0.15 * (size / dt - self.tp); self.base += 0.01 * (self.tp - self.base)
        self.entropy += 0.1 * (entropy - self.entropy); self.density += 0.1 * (density - self.density)
        self.accepted += 1; self.bytes += size
    def snapshot(self) -> dict:
        return dict(tp=self.tp, spike=self.spike, entropy=self.entropy, density=self.density,
                    accepted=self.accepted, rejected=self.rejected, bytes=self.bytes, hist=self.hist)

class Simulator:
    """High-entropy synthetic stream with bursty 'transmission vectors'."""
    def __init__(self, base_size=4096):
        self.base_size, self.burst, self.seq = base_size, 0.0, 0
    def poke(self): self.burst = 1.0
    async def run(self, sink):
        while True:
            if random.random() < 0.015: self.burst = 1.0
            self.burst *= 0.97
            mult = 1 + int(self.burst * 15)
            size = self.base_size * mult
            raw = os.urandom(size)
            if random.random() < 0.3:  # mix in low-entropy text-like regions
                raw = raw[: size // 2] + (b"VANTA-CORE-%08d|" % self.seq) * (size // 32)
            if random.random() < 0.002: raw = b""  # malformed chunk -> policy must reject
            self.seq += 1
            sink(analyse(self.seq, raw))
            await asyncio.sleep(0.02 / (1 + self.burst * 3))

class MetricsProtocol(asyncio.Protocol):
    """Raw HTTP over asyncio.Protocol: GET /metrics -> JSON."""
    metrics: Metrics = None
    def connection_made(self, t): self.t = t
    def data_received(self, d):
        line = d.split(b"\r\n", 1)[0]
        ok = line.startswith(b"GET /metrics")
        body = json.dumps(self.metrics.snapshot()).encode() if ok else b"not found"
        head = (b"HTTP/1.1 200 OK" if ok else b"HTTP/1.1 404 Not Found") + (
            b"\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nCache-Control: no-store"
            b"\r\nConnection: close\r\nContent-Length: %d\r\n\r\n" % len(body))
        self.t.write(head + body); self.t.close()

async def serve(metrics: Metrics, host="127.0.0.1", port=8765):
    MetricsProtocol.metrics = metrics
    return await asyncio.get_running_loop().create_server(MetricsProtocol, host, port)

async def main():
    from vanta_render_policy import RenderPolicy
    m = Metrics(); sim = Simulator(); pol = RenderPolicy(m)
    srv = await serve(m)
    print("VANTA generator: http://127.0.0.1:8765/metrics  (Ctrl-C to stop)")
    async def report():
        while True:
            await asyncio.sleep(1)
            print(f"tp={m.tp/1e6:7.2f} MB/s spike={m.spike:.2f} H={m.entropy:.2f} ok={m.accepted} rej={m.rejected}")
    async with srv:
        await asyncio.gather(sim.run(pol.ingest), report())

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
