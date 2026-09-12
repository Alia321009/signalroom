web: python -m alembic upgrade head && gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers ${WEB_CONCURRENCY:-1} --bind 0.0.0.0:${PORT:-8000}
