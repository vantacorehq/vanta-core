"""One command: serves index.html on :8000 and the live metrics on :8765."""
import asyncio, functools, http.server, os, threading, webbrowser
from vanta_data_generator import Metrics, Simulator, serve
from vanta_render_policy import RenderPolicy

def start_http(port=8000):
    root = os.path.dirname(os.path.abspath(__file__))
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

async def main():
    m = Metrics(); pol = RenderPolicy(m); sim = Simulator()
    start_http(); srv = await serve(m)
    print("VANTA  http://127.0.0.1:8000/index.html   (Ctrl-C to stop)")
    webbrowser.open("http://127.0.0.1:8000/index.html")
    async with srv:
        await sim.run(pol.ingest)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
