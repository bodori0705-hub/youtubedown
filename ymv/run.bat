@echo off
chcp 65001 > nul
setlocal

:: Python 실행 경로 탐색
set "PY_EXE=C:\Users\user\AppData\Local\Programs\Python\Python311\pythonw.exe"
if not exist "%PY_EXE%" (
    set "PY_EXE=pythonw.exe"
)

:: 실행
cd /d "%~dp0"
start "" "%PY_EXE%" "%~dp0main.py"
