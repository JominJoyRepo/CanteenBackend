import os
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers.auth import router as auth_router
from routers.categories import router as categories_router
from routers.records import router as records_router
from routers.stores import router as stores_router
from utils.logger import logger

app = FastAPI(title='Stock Recorder Backend', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(records_router)
app.include_router(stores_router)


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(f'Unhandled error ({request.method} {request.url}): {exc}')
    return JSONResponse(status_code=500, content={'error': 'Something went wrong!'})


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 3000))
    logger.info(f'Server running on http://localhost:{port}')
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')
