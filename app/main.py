from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from loguru import logger

from .dependencies import config, http_exception
from .effects.effects_controller import effects_router


log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <b>{message}</b>"

logger.add(
    ".log",
    format=log_format,
    level="INFO",
)


app = FastAPI(
    title="ObjectNat effects API",
    description="API for calculating effects for territory by ObjectNat library",
    version=config.get("APP_VERSION"),
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=dict[str, str])
def read_root():
    return RedirectResponse(url='/docs')

@app.get("/status")
async def read_root():
    return {"status": "OK"}

@app.get("/logs")
async def get_logs():
    """
    Get logs file from app
    """

    try:
        return FileResponse(
            ".log",
            media_type='application/octet-stream',
            filename=f"ObjectEffects.log",
        )
    except FileNotFoundError as e:
        raise http_exception(
            status_code=404,
            msg="Log file not found",
            _input={"lof_file_name": ".log"},
            _detail={"error": e.__str__()}
        )
    except Exception as e:
        raise http_exception(
            status_code=500,
            msg="Internal server error during reading logs",
            _input={"log_file_name": ".log"},
            _detail={"error": e.__str__()}
        )


app.include_router(effects_router)