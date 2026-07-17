from pathlib import Path
from aiohttp import web

ROOT = Path(__file__).resolve().parent / "webapp"

async def index(_: web.Request) -> web.StreamResponse:
    return web.FileResponse(ROOT / "index.html")

app = web.Application()
app.router.add_get("/", index)
app.router.add_get("/boss-app", index)
app.router.add_get("/boss-app/", index)
app.router.add_static("/boss-app/", ROOT, show_index=False)

print("Preview: http://127.0.0.1:8765/boss-app/?demo=1")
web.run_app(app, host="127.0.0.1", port=8765, print=None)
