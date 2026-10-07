@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py -3"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python 3.10+ is required.
        pause
        exit /b 1
    )
    set "PY_CMD=python"
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating local virtual environment...
    %PY_CMD% -m venv .venv || goto :failed
)

echo [2/4] Installing lesson 3 dependencies...
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements-lesson3.txt || goto :failed

echo [3/4] Running tests and compile checks...
.venv\Scripts\python.exe -m pytest -q || goto :failed
.venv\Scripts\python.exe -m compileall -q packages integrations experiments tests || goto :failed

echo [4/4] Running retrieval comparison...
.venv\Scripts\python.exe -m experiments.retrieval_comparison || goto :failed

echo.
echo SUCCESS: lesson 3 context pipeline is runnable.
pause
exit /b 0

:failed
echo.
echo FAILED: see the error above. Check network access and run RUN.bat again.
pause
exit /b 1
