@echo off
setlocal

REM Vai para a pasta onde o .bat está
cd /d "%~dp0"

echo =====================================
echo   FIIs - Ranking e Busca
echo =====================================
echo.

REM Verifica se o Python está no PATH
where python >nul 2>nul
if errorlevel 1 (
    echo ERRO: Python nao foi encontrado no PATH.
    echo Instale Python 3.11+ e marque a opcao "Add python to PATH".
    echo.
    pause
    exit /b 1
)

echo Instalando/atualizando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Iniciando aplicacao Streamlit...
python -m streamlit run Script/core/app.py

echo.
pause
