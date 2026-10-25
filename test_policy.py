import math, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vanta_data_generator import Metrics, analyse, shannon
from vanta_render_policy import RenderPolicy

class T(unittest.TestCase):
    def setUp(self): self.m = Metrics(); self.p = RenderPolicy(self.m)
    def test_entropy(self):
        self.assertEqual(shannon(b"\0" * 100), 0.0)
        self.assertGreater(shannon(os.urandom(65536)), 7.9)
    def test_valid_chunk(self):
        self.p.ingest(analyse(1, os.urandom(1024))); self.assertEqual(self.m.rejected, 0)
    def test_fail_closed_empty(self):
        self.p.ingest(analyse(1, b"")); self.assertEqual(self.m.rejected, 1)
    def test_fail_closed_nan(self):
        c = analyse(1, os.urandom(512)); c.entropy = math.nan
        self.p.ingest(c); self.assertEqual(self.m.rejected, 1)
    def test_garbage_type(self):
        self.p.ingest("not a chunk"); self.assertEqual(self.m.rejected, 1)
    def test_histogram_normalised(self):
        for i in range(RenderPolicy.WINDOW): self.p.ingest(analyse(i, os.urandom(2048)))
        self.assertEqual(max(self.m.hist), 1.0); self.assertEqual(self.m.accepted, RenderPolicy.WINDOW)
        d = [c.density for c in self.p.out]; self.assertEqual(d, sorted(d, reverse=True))
if __name__ == "__main__": unittest.main()
