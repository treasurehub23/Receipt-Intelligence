from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.expenses import router as expenses_router
from app.routes.analytics import router as analytics_router
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()
app.include_router(auth_router)
app.include_router(expenses_router)
app.include_router(analytics_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from pathlib import Path
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

@app.get("/")
def serve_homepage():
    return FileResponse(FRONTEND_DIST / "index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy"}




app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIST / "assets"),
    name="frontend-assets",
)

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    requested_file = FRONTEND_DIST / full_path

    if full_path and requested_file.is_file():
        return FileResponse(requested_file)

    return FileResponse(FRONTEND_DIST / "index.html")