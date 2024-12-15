from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, JSONResponse
from src.app.model.exceptions import AlreadyExistError, NotExistError, FKNotExistError, \
    FKNoDeleteUpdateError, NotMatchWithSystemError, OpNotPermittedError
from src.web.api.v1.api import api_router


app = FastAPI(
    title="FastAPI", 
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins = [
        "http://localhost",
        "http://localhost:8080",
    ],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)
app.include_router(api_router, prefix="/api/v1")

# Already Exist Error
@app.exception_handler(AlreadyExistError)
async def already_exist_error_handler(_: Request, exc: AlreadyExistError) -> JSONResponse:
    return JSONResponse(
        status_code = 520,
        content = {
            "message": exc.message,
            "details": exc.details
        },
    )
    
@app.exception_handler(NotExistError)
async def not_exist_error_handler(_: Request, exc: NotExistError) -> JSONResponse:
    return JSONResponse(
        status_code = 521,
        content = {
            "message": exc.message,
            "details": exc.details
        },
    )
    
@app.exception_handler(FKNotExistError)
async def fk_not_exist_error_handler(_: Request, exc: FKNotExistError) -> JSONResponse:
    return JSONResponse(
        status_code = 530,
        content = {
            "message": exc.message,
            "details": exc.details
        },
    )
    
@app.exception_handler(FKNoDeleteUpdateError)
async def fk_no_delete_error_handler(_: Request, exc: FKNoDeleteUpdateError) -> JSONResponse:
    return JSONResponse(
        status_code = 531,
        content = {
            "message": exc.message,
            "details": exc.details
        },
    )
    
@app.exception_handler(OpNotPermittedError)
async def op_not_permitted_error_handler(_: Request, exc: OpNotPermittedError) -> JSONResponse:
    return JSONResponse(
        status_code = 540,
        content = {
            "message": exc.message,
        },
    )
    
@app.exception_handler(NotMatchWithSystemError)
async def not_match_system_error_handler(_: Request, exc: NotMatchWithSystemError) -> JSONResponse:
    return JSONResponse(
        status_code = 550,
        content = {
            "message": exc.message,
            "details": exc.details
        },
    )


@app.get("/healthz")
def health_check() -> str:
    return "OK"


@app.get("/")
def root() -> str:
    return "OK"
    