import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from app.api.routes import router
from app.api.reports import router as report_router
from app.api.analysis import router as analysis_router
from app.api.exports import router as export_router
from app.utils.uploads import MAX_UPLOAD

app = FastAPI(
    title="ChatLens",
    description="Local, deterministic conversation analytics",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


class LimitUpload:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        limit = MAX_UPLOAD + 1024 * 1024
        try:
            too_large = int(headers.get(b"content-length", b"0")) > limit
        except ValueError:
            too_large = True
        if too_large:
            return await JSONResponse({"detail": "Upload too large"}, 413)(
                scope, receive, send
            )
        count = 0

        async def limited_receive():
            nonlocal count
            message = await receive()
            count += len(message.get("body", b""))
            if count > limit:
                from starlette.exceptions import HTTPException

                raise HTTPException(413, "Upload too large")
            return message

        await self.app(scope, limited_receive, send)


app.add_middleware(LimitUpload)
app.include_router(router)
app.include_router(report_router)
app.include_router(analysis_router)
app.include_router(export_router)


@app.get("/health")
def health():
    from sqlalchemy import text
    from app.models.database import engine

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}
