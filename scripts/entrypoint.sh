set -e
cd /app || cd /code || true
python -m alembic -c alembic.ini upgrade head || true
exec "$@"
