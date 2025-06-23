docker build -t clipso-backend .    

docker run --rm clipso-backend pytest
docker run -it --rm -e PYTHONPATH=/app clipso-backend /bin/bash
>pytest

pytest

docker run -p 8000:8000 clipso-backend

alembic revision --autogenerate -m "Initial"
alembic upgrade head


alembic migrations in docker:
docker-compose build backend
docker-compose up -d
docker-compose exec backend /bin/bash
# Inside the container:
alembic revision --autogenerate -m "Initial"
alembic upgrade head