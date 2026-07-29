from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import router

app = FastAPI(title="World Cup 2026 Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUILD_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "build"
INDEX_HTML = BUILD_DIR / "index.html"
ASSETS_DIR = BUILD_DIR / "assets"

app.include_router(router)

# Serve React static assets - for production build
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


# Catch-all route to serve index.html for Single Page Application (SPA) routing
def _frontend_index() -> FileResponse:
    if not INDEX_HTML.is_file():
        raise HTTPException(
            status_code=404,
            detail="Frontend build not found. Run: cd dashboard/frontend && ./build.sh",
        )
    return FileResponse(INDEX_HTML)


@app.get("/", include_in_schema=False)
async def spa_root() -> FileResponse:
    return _frontend_index()


for _path in ("/teams", "/knockout", "/predictions", "/groups", "/bracket"):
    app.add_api_route(
        _path,
        spa_root,
        methods=["GET"],
        include_in_schema=False,
    )


@app.api_route("/{full_path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def spa_fallback(full_path: str) -> FileResponse:
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="Not Found")
    return _frontend_index()
