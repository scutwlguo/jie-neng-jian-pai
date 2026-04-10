@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 936 >nul

title Zhidian Xianfeng Launcher
cd /d "%~dp0"

set "APP_FILE=yunduan_app.py"
set "REQ_FILE=requirements_zhidian_xianfeng.txt"

echo ========================================
echo         Zhidian Xianfeng Launcher
echo ========================================
echo.

if not exist "%APP_FILE%" (
    echo [ERROR] %APP_FILE% not found in current folder.
    echo Make sure this bat file, app script, and requirements file are in the same folder.
    echo Current folder: %cd%
    echo.
    pause
    exit /b 1
)

echo Please input full path of Python executable.
echo Example: D:\software\anaconda\envs\pytorch\python.exe
echo.

:INPUT_PYTHON
set "PYTHON_EXE="
set /p PYTHON_EXE=Python path: 

if "%PYTHON_EXE%"=="" (
    echo [INFO] Python path cannot be empty.
    echo.
    goto INPUT_PYTHON
)

if not exist "%PYTHON_EXE%" (
    echo [ERROR] File not found: %PYTHON_EXE%
    echo Please check the path and try again.
    echo.
    goto INPUT_PYTHON
)

"%PYTHON_EXE%" --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Not a valid Python executable: %PYTHON_EXE%
    echo.
    goto INPUT_PYTHON
)

echo.
echo [1/4] Python executable check passed:
"%PYTHON_EXE%" --version

echo.
echo [2/4] Checking pip...
"%PYTHON_EXE%" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo [INFO] pip not found, trying ensurepip...
    "%PYTHON_EXE%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ERROR] Failed to install pip. Please install pip in this environment first.
        echo.
        pause
        exit /b 1
    )
)

echo [3/4] Installing/checking dependencies...
if exist "%REQ_FILE%" (
    "%PYTHON_EXE%" -m pip install --upgrade pip
    "%PYTHON_EXE%" -m pip install -r "%REQ_FILE%"
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed. Check network/mirror/permissions.
        pause
        exit /b 1
    )
) else (
    echo [INFO] %REQ_FILE% not found, skip dependency install.
)

echo.
echo [4/4] Launching Streamlit app...
"%PYTHON_EXE%" -m streamlit run "%APP_FILE%"

if errorlevel 1 (
    echo.
    echo [ERROR] Launch failed. Check streamlit installation and logs above.
)

echo.
pause