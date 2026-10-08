FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

ARG REQUIREMENTS_FILE=requirements.txt
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r ${REQUIREMENTS_FILE}

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
