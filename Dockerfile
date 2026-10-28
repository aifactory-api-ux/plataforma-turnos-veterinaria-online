# Imagen de la API de turnos de la clínica veterinaria.
#
# La imagen instala también las dependencias de desarrollo para que la suite
# de pruebas pueda ejecutarse dentro del contenedor con `pytest`.
FROM python:3.11-slim

WORKDIR /app

# Salida sin buffer para ver los registros del servidor en tiempo real.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Manifiestos de dependencias: se copian primero para aprovechar la caché de
# capas de Docker cuando solo cambia el código de la aplicación.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

# Código de la aplicación y suite de pruebas.
COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
