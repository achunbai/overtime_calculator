@echo off
setlocal enabledelayedexpansion

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    REM Show message box
    mshta "javascript:var sh=new ActiveXObject('WScript.Shell'); sh.Popup('Python is not installed. Please install it from the Microsoft Store.', 10, 'Python Not Found', 64);close()"
    
    REM Open Microsoft Store Python page in default browser
    start "" "ms-windows-store://pdp/?productid=9NCVDN91XZQP"
    
    REM Exit the script
    exit /b
)

REM Check Python version
for /f "tokens=1,2 delims=." %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
    set PYTHON_MAJOR=%%i
    set PYTHON_MINOR=%%j
)

echo Python version: %PYTHON_MAJOR%.%PYTHON_MINOR%

if %PYTHON_MAJOR% LSS 3 (
    goto InstallPython
) else if %PYTHON_MAJOR% EQU 3 (
    if %PYTHON_MINOR% LSS 9 (
        goto InstallPython
    )
)

goto Continue

:InstallPython
REM Show message box
mshta "javascript:var sh=new ActiveXObject('WScript.Shell'); sh.Popup('Python version is less than 3.9. Please install the latest version from the Microsoft Store.', 10, 'Python Version Too Low', 64);close()"

REM Open Microsoft Store Python page in default browser
start "" "ms-windows-store://pdp/?productid=9NCVDN91XZQP"

REM Exit the script
exit /b

:Continue
REM Set pip mirror to bfsu.edu.cn
@echo Setting pip mirror to bfsu.edu.cn...
@pip config set global.index-url https://mirrors.bfsu.edu.cn/pypi/web/simple

REM Install dependencies
@echo Installing dependencies...
@pip install -r requirements.txt

REM Run the Python script
@echo Running the Python script...
@python calculator.py

@echo Environment setup complete!
@pause