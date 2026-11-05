@echo off
setlocal
pushd "%~dp0"

docker compose version >nul 2>&1
if errorlevel 1 (
    echo Docker Compose nao esta disponivel. Instale e inicie o Docker Desktop.
    pause
    popd
    exit /b 1
)

:menu
echo.
echo Lisa Comercial - execucao local
echo [1] Iniciar aplicacao
echo [2] Parar aplicacao
echo [3] Ver estado
echo [4] Sair
choice /c 1234 /n /m "Escolha uma opcao: "

if errorlevel 4 goto sair
if errorlevel 3 goto estado
if errorlevel 2 goto parar
if errorlevel 1 goto iniciar

:iniciar
echo.
echo Iniciando aplicacao. A primeira inicializacao pode levar alguns minutos...
docker compose up --build -d
if errorlevel 1 goto erro
echo.
echo Aplicacao iniciada. Acesse http://localhost:3000
start "" "http://localhost:3000"
goto menu

:parar
echo.
docker compose stop
if errorlevel 1 goto erro
echo Aplicacao parada. Os dados do banco foram preservados.
goto menu

:estado
echo.
docker compose ps
if errorlevel 1 goto erro
goto menu

:erro
echo.
echo Nao foi possivel concluir a operacao. Verifique se o Docker Desktop esta em execucao.
pause
goto menu

:sair
popd
endlocal
