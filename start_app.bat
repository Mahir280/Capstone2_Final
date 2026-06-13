@echo off
setlocal EnableExtensions

pushd "%~dp0" >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: Could not switch to the project folder: %~dp0
    echo.
    pause
    exit /b 1
)

set "VENV_PYTHON=.\.venv\Scripts\python.exe"
set "FRONTEND_DIR=frontend"
set "APP_URL=http://127.0.0.1:8000"

echo.
echo ============================================================
echo Fiber Based Wearable Electronics Patent Mapping App
echo ============================================================
echo.
echo Official Windows launcher: start_app.bat
echo Project root: %CD%
echo.
echo The app will be available at: %APP_URL%
echo Health check:                  %APP_URL%/health
echo API docs:                      %APP_URL%/docs
echo.
echo Press Ctrl+C in this window to stop the app after it starts.
echo.

echo [1/8] Checking Python...
where python >nul 2>nul
if errorlevel 1 (
    set "ERROR_MESSAGE=Python was not found on PATH. Install Python 3.11 or newer, then reopen this window."
    goto fail
)
python --version
if errorlevel 1 (
    set "ERROR_MESSAGE=Python was found, but it did not run successfully."
    goto fail
)
echo Python is available.
echo.

if not exist "requirements.txt" (
    set "ERROR_MESSAGE=requirements.txt was not found in the project root."
    goto fail
)

echo [2/8] Checking Python virtual environment...
if not exist "%VENV_PYTHON%" (
    echo .venv was not found. Creating it now...
    python -m venv .venv
    if errorlevel 1 (
        set "ERROR_MESSAGE=Could not create .venv. Check the Python installation and permissions for this folder."
        goto fail
    )
)
if not exist "%VENV_PYTHON%" (
    set "ERROR_MESSAGE=.venv\Scripts\python.exe was not found after virtual environment setup."
    goto fail
)
"%VENV_PYTHON%" --version
if errorlevel 1 (
    set "ERROR_MESSAGE=.venv\Scripts\python.exe did not run successfully."
    goto fail
)
echo Python virtual environment is ready.
echo.

echo [3/8] Installing or updating Python dependencies...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    set "ERROR_MESSAGE=Python dependency installation failed. Check the pip output above."
    goto fail
)
echo Python dependencies are ready.
echo.

echo [4/8] Checking Node.js and npm...
where node >nul 2>nul
if errorlevel 1 (
    set "ERROR_MESSAGE=Node.js was not found on PATH. Install Node.js 20 LTS or newer, then reopen this window."
    goto fail
)
node --version
if errorlevel 1 (
    set "ERROR_MESSAGE=Node.js was found, but it did not run successfully."
    goto fail
)
where npm >nul 2>nul
if errorlevel 1 (
    set "ERROR_MESSAGE=npm was not found on PATH. Install Node.js 20 LTS or newer, then reopen this window."
    goto fail
)
cmd /c npm --version
if errorlevel 1 (
    set "ERROR_MESSAGE=npm was found, but it did not run successfully."
    goto fail
)
echo Node.js and npm are available.
echo.

echo [5/8] Checking frontend project files...
if not exist "%FRONTEND_DIR%\package.json" (
    set "ERROR_MESSAGE=frontend\package.json was not found."
    goto fail
)
echo Frontend project files are present.
echo.

echo [6/8] Checking frontend dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo frontend\node_modules is missing. Installing frontend dependencies...
    pushd "%FRONTEND_DIR%" >nul 2>nul
    if errorlevel 1 (
        set "ERROR_MESSAGE=Could not change into the frontend directory."
        goto fail
    )
    cmd /c npm install
    if errorlevel 1 (
        popd >nul 2>nul
        set "ERROR_MESSAGE=Frontend dependency installation failed. Check the npm output above."
        goto fail
    )
    popd >nul 2>nul
    echo Frontend dependencies installed.
) else (
    echo Frontend dependencies found.
)
if not exist "%FRONTEND_DIR%\node_modules" (
    set "ERROR_MESSAGE=frontend\node_modules was not found after dependency setup."
    goto fail
)
echo.

echo [7/8] Building the React frontend...
pushd "%FRONTEND_DIR%" >nul 2>nul
if errorlevel 1 (
    set "ERROR_MESSAGE=Could not change into the frontend directory."
    goto fail
)
cmd /c npm run build
if errorlevel 1 (
    popd >nul 2>nul
    set "ERROR_MESSAGE=React frontend build failed. Check the npm output above."
    goto fail
)
popd >nul 2>nul

if not exist "%FRONTEND_DIR%\dist\index.html" (
    set "ERROR_MESSAGE=frontend\dist\index.html was not produced by the build."
    goto fail
)
echo Frontend build verified at frontend\dist\index.html.
echo.

echo [8/8] Starting FastAPI with the built React app...
echo.
echo Open this URL in your browser:
echo %APP_URL%
echo.
"%VENV_PYTHON%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
set "SERVER_EXIT=%ERRORLEVEL%"

echo.
if "%SERVER_EXIT%"=="0" (
    echo FastAPI stopped.
) else (
    echo FastAPI stopped with exit code %SERVER_EXIT%.
    echo Check the messages above for the cause.
)
echo.
pause
popd >nul 2>nul
exit /b %SERVER_EXIT%

:fail
echo.
echo ERROR: %ERROR_MESSAGE%
echo.
echo Startup did not finish. Review the message above, then run start_app.bat again.
echo.
pause
popd >nul 2>nul
exit /b 1
