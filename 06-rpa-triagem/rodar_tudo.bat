@echo off
rem Roda tudo de uma vez: instala, executa o robo, avalia, provoca falhas e roda os testes.
rem De dois cliques neste arquivo. A janela fica aberta no final.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (set PY=py -3) else (set PY=python)

echo.
echo ===== 1 de 5: instalando as bibliotecas =====
%PY% -m pip install -q -r requirements.txt
if errorlevel 1 goto erro

echo.
echo ===== 2 de 5: fluxo completo do robo =====
%PY% main.py
if errorlevel 1 goto erro

echo.
echo ===== 3 de 5: avaliacao da IA no conjunto de teste =====
%PY% main.py avaliar
if errorlevel 1 goto erro

echo.
echo ===== 4 de 5: falhas provocadas =====
%PY% main.py falhas
if errorlevel 1 goto erro

echo.
echo ===== 5 de 5: testes automatizados =====
%PY% -m pytest -q

echo.
echo PRONTO. As evidencias estao na pasta "evidencias".
pause
exit /b 0

:erro
echo.
echo ALGO FALHOU. Copie as linhas acima e envie para conferencia.
pause
exit /b 1
