@echo off
REM =====================================================
REM  EpitopX AI — Start both backend and frontend
REM  
REM  PREREQUISITES:
REM    1. PostgreSQL 17 running on localhost:5432
REM       Database: backend_db, User: epitopx, Password: epitopx2024
REM    2. Node.js installed  (cd frontend && npm install)
REM    3. Python 3.11+ with packages installed:
REM       pip install -r backend\requirements.txt
REM =====================================================

REM ── Database connection ───────────────────────────────
set DATABASE_URL=postgresql://epitopx:epitopx2024@localhost:5432/backend_db
set DJANGO_DEBUG=True

echo =====================================================
echo  EpitopX AI — Local startup
echo =====================================================
echo.

REM ── 1. Run Django migrations ──────────────────────────
echo [1/3] Running Django database migrations ...
cd /d "%~dp0backend"
python manage.py migrate --noinput
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Django migration failed.
    echo         Ensure PostgreSQL is running on localhost:5432
    echo         Database: backend_db, User: epitopx, Password: epitopx2024
    pause
    exit /b 1
)
echo       Migrations OK.
echo.

REM ── Ensure admin user from environment ───────────────────────────────
echo [2/3] Ensuring admin user from environment...
python ..\scripts\create_admin_from_env.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo [WARNING] Admin creation script failed.
)
echo.

REM ── 2. Start Django backend (waitress — handles concurrent users) ────────
echo [2/3] Starting Django backend on http://localhost:8000 ...
start "Django Backend" cmd /k "cd /d %~dp0backend && python -m waitress --port=8000 --threads=16 --connection-limit=500 --backlog=256 config.wsgi:application"
timeout /t 2 /nobreak >nul

REM ── 3. Start Node.js frontend ─────────────────────────
echo [3/3] Starting Node.js frontend on http://localhost:3333 ...
start "Node Frontend" cmd /k "cd /d %~dp0frontend && node server.js"

echo.
echo =====================================================
echo  Both services are starting:
echo    Django API  -^>  http://localhost:8000/api/
echo    Frontend    -^>  http://localhost:3333   ^<-- open in browser
echo =====================================================
echo.
echo Press any key to close this launcher window ...
pause >nul
