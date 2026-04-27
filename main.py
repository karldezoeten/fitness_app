from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from database import engine, init_db
from routers import strava
import uvicorn
from routers import strava, goals, trails


# Create the FastAPI app
app = FastAPI(
    title="Trail Running Training App",
    description="Smart ultra marathon training with trail suggestions",
    version="0.1.0"
)

# Mount the frontend static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Register routers
app.include_router(strava.router)
app.include_router(goals.router)
app.include_router(trails.router)

@app.on_event("startup")
def startup_event():
    """
    Runs once when the app starts.
    Creates all database tables if they don't exist yet.
    """
    init_db()
    print("✅ Database initialized")
    print("✅ App started - open http://localhost:8000")

@app.get("/")
def root():
    return {"message": "Trail Running Training App is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Run the app
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

