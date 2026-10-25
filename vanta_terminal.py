"""VANTA terminal: ANSI gravity-collapse header driven by live throughput. Keys: s=spike, q=quit."""
import asyncio, math, os, random, shutil, sys, time
from vanta_data_generator import Metrics, Simulator
from vanta_render_policy import RenderPolicy

FONT = {"V": ["#...#","#...#","#...#",".#.#.","..#.."], "A": [".###.","#...#","#####","#...#","#...#"],
        "N": ["#...#","##..#","#.#.#","#..##","#...#"], "T": ["#####","..#..","..#..","..#..","..#.."],
        "C": [".####","#....","#....","#....",".####"], "O": [".###.","#...#","#...#","#...#",".###."],
        "R": ["####.","#...#","####.","#..#.","#...#"], "E": ["#####","#....","####.","#....","#####"]}
SHADE = "█▓▒░"
def fg(g): return f"\x1b[38;5;{232 + max(0, min(23, int(g)))}m"

class Header:
    def __init__(self, cols, rows):
        self.cols, self.rows, self.ps = cols, rows, []
        sx = 2 if cols >= 130 else 1
        text = "VANTA CORE"; w = sum(0 if ch == " " else 6 * sx for ch in text) + text.count(" ") * 4 * sx
        x0, y0, cx = max(0, (cols - w) // 2), 3, 0
        for ch in text:
            if ch == " ": cx += 4 * sx; continue
            for r, row in enumerate(FONT[ch]):
                for c, v in enumerate(row):
                    if v == "#":
                        for k in range(sx):
                            hx, hy = x0 + cx + c * sx + k, y0 + r
                            self.ps.append([hx, hy, hx, hy, 0.0, 0.0])  # x y homex homey vx vy
            cx += 6 * sx
        self.cx, self.cy = cols / 2, y0 + 2.5
        self.phase, self.t0, self.cool = "idle", 0.0, 0.0
    def trigger(self, now):
        if self.phase == "idle" and now > self.cool: self.phase, self.t0 = "collapse", now
    def step(self, now, dt, spike):
        age = now - self.t0
        if self.phase == "collapse" and age > 1.4: self.phase, self.t0 = "rain", now
        elif self.phase == "rain" and age > 1.6: self.phase, self.t0 = "rebuild", now
        elif self.phase == "rebuild" and age > 0.8 and all(abs(p[0]-p[2]) + abs(p[1]-p[3]) < 0.6 for p in self.ps):
            self.phase, self.cool = "idle", now + 2.0
        for p in self.ps:
            if self.phase == "collapse":
                dx, dy = self.cx - p[0], (self.cy - p[1]) * 2; d = math.hypot(dx, dy) + 0.5
                g = (60 + 140 * spike) / d
                p[4] += (dx / d * g - dy / d * g * 0.6) * dt; p[5] += (dy / d * g + dx / d * g * 0.3) * dt * 0.5
                p[4] *= 0.985; p[5] *= 0.985
                if d < 1.5: p[0] += random.uniform(-.5, .5); p[1] += random.uniform(-.2, .2)
            elif self.phase == "rain":
                p[5] += 40 * dt; p[4] *= 0.99
                if p[1] > self.rows - 6: p[1] = self.rows - 6; p[5] *= -0.35; p[4] += random.uniform(-3, 3)
            elif self.phase == "rebuild":
                p[4] += (p[2] - p[0]) * 18 * dt; p[5] += (p[3] - p[1]) * 18 * dt; p[4] *= 0.88; p[5] *= 0.88
            else:
                p[4] = p[5] = 0.0; p[0], p[1] = p[2], p[3]
            p[0] += p[4] * dt * 2; p[1] += p[5] * dt

def draw(h: Header, m: Metrics, now):
    cols, rows = h.cols, h.rows
    grid = [[(" ", 0)] * cols for _ in range(rows)]
    if h.phase in ("collapse", "rain"):  # black hole accretion rings
        r = 2 + 6 * m.spike if h.phase == "collapse" else 1
        for y in range(rows):
            for x in range(cols):
                d = math.hypot(x - h.cx, (y - h.cy) * 2)
                if d < r: grid[y][x] = ("█" if d < r * .5 else "▓", 1 if d < r * .5 else 6)
                elif d < r + 3 and h.phase == "collapse": grid[y][x] = (SHADE[3 - min(3, int(d - r))], 7 + int(d))
    for p in h.ps:
        x, y = int(p[0]), int(p[1])
        if 0 <= x < cols and 0 <= y < rows:
            sp = math.hypot(p[4], p[5]); i = 0 if sp < 1 else min(3, 1 + int(sp / 12))
            grid[y][x] = (SHADE[i], 23 - 4 * i)
    out = ["\x1b[H"]
    for row in grid: out.append("".join(fg(g) + c for c, g in row) + "\x1b[0m\n")
    bar = int(min(1.0, m.tp / (m.base * 4 + 1)) * (cols - 30))
    lines = [f" PHASE {h.phase.upper():8} TP {m.tp/1e6:8.2f} MB/s  SPIKE {m.spike:4.2f}  H {m.entropy:4.2f}/8  OK {m.accepted}  REJ {m.rejected}",
             " [" + "█" * bar + "░" * (cols - 30 - bar) + "]  " + "".join(" ▁▂▃▄▅▆▇█"[int(v * 8)] for v in m.hist)]
    return "".join(out[:rows - 1]) + "\x1b[%d;1H" % (rows - 1) + "\n".join(fg(20) + l[:cols] for l in lines) + "\x1b[0m"

async def main():
    cols, rows = shutil.get_terminal_size((100, 30)); rows = max(rows, 20)
    m = Metrics(); sim = Simulator(); pol = RenderPolicy(m); h = Header(cols, rows)
    tasks = [asyncio.create_task(sim.run(pol.ingest))]
    loop, stop = asyncio.get_running_loop(), asyncio.Event()
    old = None
    try:
        import termios, tty
        old = termios.tcgetattr(sys.stdin); tty.setcbreak(sys.stdin.fileno())
        def key():
            k = os.read(sys.stdin.fileno(), 8).decode(errors="ignore")
            if "q" in k: stop.set()
            if "s" in k: sim.poke(); h.trigger(time.monotonic())
        loop.add_reader(sys.stdin.fileno(), key)
    except Exception: pass
    sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J")
    last = time.monotonic()
    try:
        while not stop.is_set():
            now = time.monotonic(); dt = min(now - last, 0.05); last = now
            if m.spike > 0.55: h.trigger(now)
            h.step(now, dt, m.spike)
            sys.stdout.write(draw(h, m, now)); sys.stdout.flush()
            await asyncio.sleep(max(0, 1 / 30 - (time.monotonic() - now)))
    finally:
        for t in tasks: t.cancel()
        if old:
            import termios; termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        sys.stdout.write("\x1b[?25h\x1b[?1049l")

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: sys.stdout.write("\x1b[?25h\x1b[?1049l")
