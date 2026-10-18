@echo off
cd /d "%~dp0"
if "%~1"=="" (
  set "DEPTH_INPUT=%~dp0inputs"
) else (
  set "DEPTH_INPUT=%~1"
)
echo Fichiers a traiter : "%DEPTH_INPUT%"
"%~dp0.venv\Scripts\python.exe" "%~dp0depth.py" --input "%DEPTH_INPUT%"
if errorlevel 1 (
  echo Une erreur est survenue. Lisez le message ci-dessus.
  pause
  exit /b 1
)
echo.
echo Resultat dans le dossier results\relative
pause
