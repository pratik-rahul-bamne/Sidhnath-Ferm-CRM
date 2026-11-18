@echo off
setlocal enabledelayedexpansion
title Siddhanth Firm - Executable Builder

:: Ensure we operate in the folder where this batch file is stored
cd /d "%~dp0"

echo ====================================================================
echo    SHREE SIDDHNATH BULLION ^& TESTING MANAGEMENT SYSTEM
echo                   WINDOWS EXE BUILDER
echo ====================================================================
echo.

:: 1. Check Python installation
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10+ and check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do set PYTHON_VER=%%v
echo       Found: %PYTHON_VER%

:: 2. Check and install dependencies only if missing
echo.
echo [2/4] Verifying required Python packages...
python -c "import flask, reportlab, flask_bcrypt, dotenv, PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo       Some dependencies are missing. Installing required packages...
    python -m pip install -r requirements.txt
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
) else (
    echo       All required packages (Flask, ReportLab, Bcrypt, PyInstaller) are verified.
)

:: 3. Check for custom icon
set ICON_ARG=
if exist "static\icon.ico" (
    set "ICON_ARG=--icon=static\icon.ico"
) else if exist "icon.ico" (
    set "ICON_ARG=--icon=icon.ico"
)

:: 4. Build Standalone Executable using PyInstaller
echo.
echo [3/4] Building standalone executable with PyInstaller...
echo       Bundling templates, static files, and database schemas...
echo.

pyinstaller --noconfirm --clean --onefile ^
    --name "SiddhanthFirm" ^
    %ICON_ARG% ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "database.sql;." ^
    --add-data ".env.example;." ^
    --hidden-import "jinja2" ^
    --hidden-import "reportlab" ^
    --hidden-import "reportlab.platypus" ^
    --hidden-import "reportlab.lib" ^
    --hidden-import "reportlab.lib.colors" ^
    --hidden-import "reportlab.lib.pagesizes" ^
    --hidden-import "reportlab.lib.units" ^
    --hidden-import "reportlab.lib.styles" ^
    --hidden-import "reportlab.lib.enums" ^
    --hidden-import "flask" ^
    --hidden-import "flask_bcrypt" ^
    --hidden-import "sqlite3" ^
    --hidden-import "dotenv" ^
    --exclude-module "torch" ^
    --exclude-module "torchvision" ^
    --exclude-module "ultralytics" ^
    --exclude-module "cv2" ^
    --exclude-module "scipy" ^
    --exclude-module "sklearn" ^
    --exclude-module "pandas" ^
    --exclude-module "matplotlib" ^
    --exclude-module "IPython" ^
    --exclude-module "jupyter" ^
    --exclude-module "pytest" ^
    --exclude-module "dlib" ^
    --exclude-module "tkinter" ^
    --exclude-module "zmq" ^
    app.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller compilation failed.
    pause
    exit /b 1
)

:: 5. Prepare distribution folder
echo.
echo [4/4] Preparing distribution folder...
if not exist "dist\siddhanth_firm.db" (
    if exist "siddhanth_firm.db" (
        echo       Copying database to dist\siddhanth_firm.db...
        copy /Y "siddhanth_firm.db" "dist\siddhanth_firm.db" >nul
    )
)

if not exist "dist\.env" (
    if exist ".env" (
        echo       Copying .env to dist\.env...
        copy /Y ".env" "dist\.env" >nul
    ) else if exist ".env.example" (
        echo       Creating dist\.env from .env.example...
        copy /Y ".env.example" "dist\.env" >nul
    )
)

:: Create a launcher script in dist
echo @echo off > "dist\RUN_SIDDHANTH_FIRM.bat"
echo title Siddhanth Firm Management System >> "dist\RUN_SIDDHANTH_FIRM.bat"
echo cd /d "%%~dp0" >> "dist\RUN_SIDDHANTH_FIRM.bat"
echo start "" "SiddhanthFirm.exe" >> "dist\RUN_SIDDHANTH_FIRM.bat"

echo.
echo ====================================================================
echo   BUILD COMPLETED SUCCESSFULLY!
echo ====================================================================
echo   Executable file:
echo   %~dp0dist\SiddhanthFirm.exe
echo.
echo   How to use:
echo   1. Navigate to the "dist" folder.
echo   2. Double-click "SiddhanthFirm.exe" or "RUN_SIDDHANTH_FIRM.bat".
echo   3. Your web browser will automatically open at:
echo      http://localhost:5000
echo.
echo   Note: The database (siddhanth_firm.db) is preserved in "dist\"
echo   alongside the executable so all customer and testing data persists.
echo ====================================================================
echo.
pause
