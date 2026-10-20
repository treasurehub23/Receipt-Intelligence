from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.expenses import router as expenses_router
from app.routes.analytics import router as analytics_router
app = FastAPI()
app.include_router(auth_router)
app.include_router(expenses_router)
app.include_router(analytics_router)

@app.get("/")
def home():
    return {"message": "I'm aliveeee"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


