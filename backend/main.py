from contextlib import asynccontextmanager
import logging
import os
import threading
from time import perf_counter
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .schemas import PredictionRequest, PredictionResponse

log = logging.getLogger(__name__)


def create_app(finder=None):
    @asynccontextmanager
    async def lifespan(app):
        if app.state.finder is None:
            try:
                from .engine import Finder
                app.state.finder = Finder()
            except (OSError, ValueError, KeyError) as exc:
                log.error('Search resources are unavailable: %s', exc)
        yield

    app = FastAPI(title='ShabdAnveshi API', version='0.2.0', lifespan=lifespan)
    app.state.finder = finder
    app.state.busy = threading.BoundedSemaphore(1)
    origins = [origin.strip() for origin in os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.get('/api/health')
    def health():
        engine = app.state.finder
        return JSONResponse(status_code=200 if engine else 503, content={
            'status': 'ready' if engine else 'unavailable', 'model': 'multilingual-e5-small ONNX int8',
            'languages': ['en', 'hi'], 'word_senses': engine.metadata['languages'] if engine else {}})

    @app.get('/api/examples')
    def examples():
        return {'en': ['someone who loves books', 'unable to fall asleep', 'fear of enclosed spaces'],
                'hi': ['किताबों से प्यार करने वाला व्यक्ति', 'नींद न आना', 'दूसरों के दुख को समझने की भावना']}

    @app.post('/api/predict', response_model=PredictionResponse)
    def predict(query: PredictionRequest):
        engine = app.state.finder
        if engine is None:
            raise HTTPException(503, 'Search index is unavailable. Prepare dictionary and model resources first.')
        if not app.state.busy.acquire(blocking=False):
            raise HTTPException(429, 'Search is busy. Please retry shortly.')
        start = perf_counter()
        try:
            suggestions = engine.search(query)
        finally:
            app.state.busy.release()
        warnings = ['Hindi words currently have English dictionary definitions.'] if any(s['language'] == 'hi' for s in suggestions) else []
        return {'suggestions': suggestions, 'method': 'multilingual-e5-small + 0.05 TF-IDF (uncalibrated baseline)',
                'elapsed_ms': round((perf_counter() - start) * 1000, 1), 'warnings': warnings}

    return app


app = create_app()
