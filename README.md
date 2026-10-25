<p align="center"><img src="banner.svg" alt="VANTA CORE" width="100%"></p>

<p align="center">
<img src="https://img.shields.io/badge/python-3.11-1a1a1a?style=flat-square" alt="python">
<img src="https://img.shields.io/badge/webgl-2.0-1a1a1a?style=flat-square" alt="webgl2">
<img src="https://img.shields.io/badge/dependencies-0-1a1a1a?style=flat-square" alt="deps">
<img src="https://img.shields.io/badge/license-MIT-1a1a1a?style=flat-square" alt="license">
</p>

# VANTA CORE

> Brutalist monochrome kinetic art engine. 2,000,000 WebGL 2.0 particles, asyncio byte-stream simulator, ANSI black-hole terminal. Pure Python 3.11, zero dependencies.

<p align="center"><img src="assets/vanta-motion.gif" alt="black hole" width="640"></p>

<img src="assets/divider.svg" width="100%" alt="">

## Quick start
```
python vanta_server.py       # serves index.html + live metrics, opens the browser
python vanta_terminal.py     # terminal animation (s = spike, q = quit)
make test                    # stdlib unittest
```
Separate processes also work: `python vanta_data_generator.py`, then open `index.html`.

## Controls (browser)
Drag = orbit with inertia. Wheel = zoom. Pointer = repels particles. Click = pulse.

## Motion gallery
<p align="center">
<img src="assets/vanta-glitch.gif" alt="glitch" width="640"><br>
<img src="assets/vanta-equalizer.gif" alt="equalizer" width="640"><br>
<img src="assets/vanta-tunnel.gif" alt="tunnel" width="480">
</p>

## How it works
```
Simulator -> analyse() -> RenderPolicy (fail-closed) -> Metrics
Metrics -> HTTP /metrics (127.0.0.1:8765) -> index.html (WebGL2)
Metrics -> vanta_terminal.py (ANSI)
```
Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Files
| Path | Role |
|---|---|
| `vanta_data_generator.py` | asyncio.Protocol stream simulator + `/metrics` endpoint |
| `vanta_render_policy.py` | fail-closed validation, density sorting |
| `vanta_terminal.py` | ANSI gravity animation of the header |
| `vanta_server.py` | one-command launcher |
| `index.html` | WebGL 2.0 swarm, 2M particles |
| `tests/test_policy.py` | unit tests |
| `tools/` | stdlib generators: PNG, GIF encoder, motion pack |
| `assets/` | logo, favicon, divider, social preview, texture, 4 GIFs, mp4 |
| `docs/ARCHITECTURE.md` | data flow |
| `LICENSE` `CONTRIBUTING.md` `CODE_OF_CONDUCT.md` `SECURITY.md` `CHANGELOG.md` | project meta |
| `.github/` | CI, issue and PR templates |

Regenerate assets: `python tools/make_social_preview.py`, `python tools/make_motion.py`, `python tools/make_motion_pack.py`.

## Social preview
Upload `assets/social-preview.png` in Settings > General > Social preview.

## License
MIT
