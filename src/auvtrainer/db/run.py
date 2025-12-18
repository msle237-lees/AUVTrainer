from __future__ import annotations

from fastapi import FastAPI

from .deps import lifespan
from .routers import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="API Service",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.get("/")
    async def root():
        return {"ok": True, "service": "API Service"}

    return app


# ASGI entrypoint (uvicorn <your_package_name>.run:app)
app = create_app()
