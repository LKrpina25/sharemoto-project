from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.routers import auth, motorcycles, reservations

app = FastAPI(
    title="ShareMoto API",
    description="Backend sustav za rezervaciju i probnu vožnju motocikala.",
    version="1.0.0",
)

# Registracija globalnih exception handlerja
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Registracija routera
app.include_router(auth.router)
app.include_router(motorcycles.router)
app.include_router(reservations.router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Dobrodošli u ShareMoto API! Sustav je spreman za rad.",
        "docs": "/docs",
    }
