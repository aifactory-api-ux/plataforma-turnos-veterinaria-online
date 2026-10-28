#!/usr/bin/env bash
#
# Atajo de arranque y verificación de la API de turnos de la clínica veterinaria.
#
# Uso:
#   ./run.sh install   Crea el entorno virtual e instala las dependencias.
#   ./run.sh api       Levanta la API en local con uvicorn (puerto 8000).
#   ./run.sh stack     Levanta la pila de contenedores (PostgreSQL + API).
#   ./run.sh tests     Ejecuta la suite de pruebas.
#   ./run.sh help      Muestra esta ayuda.
#
# Variables de entorno reconocidas:
#   DATABASE_URL  Conexión a la base de datos. Si no se define, `./run.sh api`
#                 usa una base SQLite local en `.data/vetclinic.db`.
#   JWT_SECRET    Secreto de firma de los tokens. Por defecto, el valor de
#                 desarrollo de `.env.example`.
#   API_HOST      Dirección de escucha del servidor local. Por defecto 0.0.0.0.
#   API_PORT      Puerto de escucha del servidor local. Por defecto 8000.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="$VENV_DIR/bin/python"
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"

usage() {
    cat <<'AYUDA'
Uso:
  ./run.sh install   Crea el entorno virtual e instala las dependencias.
  ./run.sh api       Levanta la API en local con uvicorn (puerto 8000).
  ./run.sh stack     Levanta la pila de contenedores (PostgreSQL + API).
  ./run.sh tests     Ejecuta la suite de pruebas.
  ./run.sh help      Muestra esta ayuda.

Variables de entorno reconocidas:
  DATABASE_URL  Conexión a la base de datos. Si no se define, `./run.sh api`
                usa una base SQLite local en `.data/vetclinic.db`.
  JWT_SECRET    Secreto de firma de los tokens. Por defecto, el valor de
                desarrollo de `.env.example`.
  API_HOST      Dirección de escucha del servidor local. Por defecto 0.0.0.0.
  API_PORT      Puerto de escucha del servidor local. Por defecto 8000.
AYUDA
}

# Devuelve el intérprete de Python disponible en el equipo.
find_python() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        echo "python"
    else
        echo "Error: no se encontró Python 3 en el equipo." >&2
        exit 1
    fi
}

# Crea el entorno virtual si todavía no existe.
ensure_venv() {
    if [ ! -x "$PYTHON_BIN" ]; then
        echo "==> Creando el entorno virtual en .venv"
        "$(find_python)" -m venv "$VENV_DIR"
    fi
}

# Instala las dependencias de ejecución y de desarrollo.
install_dependencies() {
    ensure_venv
    echo "==> Instalando las dependencias del proyecto"
    "$PYTHON_BIN" -m pip install --quiet --upgrade pip
    "$PYTHON_BIN" -m pip install --quiet \
        -r "$ROOT_DIR/requirements.txt" \
        -r "$ROOT_DIR/requirements-dev.txt"
}

# Instala las dependencias solo si el entorno no las tiene todavía.
ensure_dependencies() {
    ensure_venv
    if ! "$PYTHON_BIN" -c "import fastapi, uvicorn, pytest" >/dev/null 2>&1; then
        install_dependencies
    fi
}

# Levanta la API en local con el servidor ASGI.
run_api() {
    ensure_dependencies
    if [ -z "${DATABASE_URL:-}" ]; then
        export DATABASE_URL="sqlite:///$ROOT_DIR/.data/vetclinic.db"
        mkdir -p "$ROOT_DIR/.data"
        echo "==> DATABASE_URL no definida: se usa SQLite local en .data/vetclinic.db"
    fi
    export JWT_SECRET="${JWT_SECRET:-change-me-in-production}"
    echo "==> API disponible en http://localhost:$API_PORT (documentación en /docs)"
    cd "$ROOT_DIR"
    exec "$PYTHON_BIN" -m uvicorn app.main:app \
        --host "$API_HOST" --port "$API_PORT" --reload
}

# Levanta la pila de contenedores con PostgreSQL y la API.
run_stack() {
    if ! command -v docker >/dev/null 2>&1; then
        echo "Error: Docker no está disponible en este equipo." >&2
        echo "       Usa './run.sh api' para levantar la API en local." >&2
        exit 1
    fi
    cd "$ROOT_DIR"
    exec docker compose up --build
}

# Ejecuta la suite de pruebas; acepta argumentos adicionales de pytest.
run_tests() {
    ensure_dependencies
    cd "$ROOT_DIR"
    if [ "$#" -gt 0 ]; then
        exec "$PYTHON_BIN" -m pytest "$@"
    fi
    exec "$PYTHON_BIN" -m pytest -q
}

COMMAND="${1:-help}"
if [ "$#" -gt 0 ]; then
    shift
fi

case "$COMMAND" in
    install)
        install_dependencies
        ;;
    api)
        run_api
        ;;
    stack)
        run_stack
        ;;
    tests)
        run_tests "$@"
        ;;
    help | -h | --help)
        usage
        ;;
    *)
        echo "Comando desconocido: $COMMAND" >&2
        usage >&2
        exit 2
        ;;
esac
