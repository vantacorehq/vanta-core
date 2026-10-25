"""VANTA render policy: fail-closed constraint validation, density sorting, distribution normalisation."""
import math
from vanta_data_generator import Chunk, Metrics

class PolicyViolation(Exception): pass

class RenderPolicy:
    MIN, MAX, WINDOW, BUCKETS = 64, 1 << 20, 32, 16
    def __init__(self, metrics: Metrics):
        self.m, self.buf, self.out = metrics, [], []
    def validate(self, c: Chunk):
        if not isinstance(c, Chunk): raise PolicyViolation("type")
        if not self.MIN <= len(c.data) <= self.MAX: raise PolicyViolation("size")
        if not c.fmt_ok: raise PolicyViolation("format")
        for v in (c.entropy, c.density):
            if not math.isfinite(v): raise PolicyViolation("nan")
        if not 0.0 <= c.entropy <= 8.0 or not 0.0 <= c.density <= 1.0: raise PolicyViolation("range")
        if c.printable > len(c.data): raise PolicyViolation("count")
    def ingest(self, c) -> None:
        try:
            self.validate(c)
        except Exception:      # fail closed: any anomaly -> drop chunk, never render it
            self.m.rejected += 1
            return
        self.buf.append(c)
        if len(self.buf) >= self.WINDOW: self.flush()
    def flush(self):
        batch = sorted(self.buf, key=lambda c: c.density, reverse=True); self.buf = []
        hist = [0] * self.BUCKETS
        for c in batch: hist[min(self.BUCKETS - 1, int(c.density * self.BUCKETS))] += 1
        peak = max(hist) or 1
        self.m.hist = [h / peak for h in hist]          # clean, normalised distribution
        for c in batch: self.m.update(len(c.data), c.entropy, c.density)
        self.out = batch
