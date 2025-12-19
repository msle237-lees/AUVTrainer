from fastapi import FastAPI

from .database import initialize_database
from .routes import router as db_router

app = FastAPI(title="AUVTrainer DB API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    """
    Initialize the SQLite schema when the service starts.
    """
    initialize_database()


app.include_router(db_router)
