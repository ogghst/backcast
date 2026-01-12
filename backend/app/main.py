"""Main application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

# Include routers
from app.api.routes import (
    auth,
    change_orders,
    cost_element_types,
    cost_elements,
    departments,
    projects,
    users,
    wbes,
)
from app.core.config import settings
from app.core.exceptions.filtering import FilterError
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

# Import models to ensure they are registered with SQLAlchemy
# (user_preference removed - now embedded in user table as JSON)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Configure logging on startup
    setup_logging()

    # Startup: could check db connection here
    yield
    # Shutdown: clean up resources


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.BACKEND_CORS_METHODS,
    allow_headers=settings.BACKEND_CORS_HEADERS,
)


# Exception Handlers


@app.exception_handler(FilterError)
async def filter_exception_handler(request: Request, exc: FilterError) -> JSONResponse:
    """Handle filter parsing errors by returning 400 Bad Request."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with detailed information."""
    logger.error(f"Validation error on {request.url}: {exc.errors()}")

    errors = exc.errors()
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": formatted_errors,
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Backcast EVS API"}


app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["Users"])
app.include_router(
    departments.router,
    prefix=f"{settings.API_V1_STR}/departments",
    tags=["Departments"],
)
app.include_router(
    projects.router,
    prefix=f"{settings.API_V1_STR}/projects",
    tags=["Projects"],
)
app.include_router(
    wbes.router,
    prefix=f"{settings.API_V1_STR}/wbes",
    tags=["WBEs"],
)
app.include_router(
    cost_element_types.router,
    prefix=f"{settings.API_V1_STR}/cost-element-types",
    tags=["Cost Element Types"],
)
app.include_router(
    cost_elements.router,
    prefix=f"{settings.API_V1_STR}/cost-elements",
    tags=["Cost Elements"],
)
app.include_router(
    change_orders.router,
    prefix=f"{settings.API_V1_STR}/change-orders",
    tags=["Change Orders"],
)
