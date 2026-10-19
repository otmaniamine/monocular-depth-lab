@echo off
cd /d "%~dp0"
set "DEPTH_INPUT=%~dp0inputs"
if not "%~1"=="" set "DEPTH_INPUT=%~1"
echo Choisissez le type de scene :
echo 1 - Interieur
echo 2 - Exterieur
set "DEPTH_CHOICE="
set /p "DEPTH_CHOICE=Votre choix (1 ou 2) : "
set "DEPTH_MODEL=indoor"
if "%DEPTH_CHOICE%"=="2" set "DEPTH_MODEL=outdoor"
"%~dp0.venv\Scripts\python.exe" "%~dp0reconstruct.py" --input "%DEPTH_INPUT%" --model %DEPTH_MODEL% --open
if errorlevel 1 echo Une erreur est survenue. Lisez le message ci-dessus.
pause
