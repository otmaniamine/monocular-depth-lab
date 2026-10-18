@echo off
cd /d "%~dp0"
if "%~1"=="" (
  echo Glissez une photo ou un dossier sur ce fichier.
  pause
  exit /b 1
)
for %%M in (relative hybrid large) do (
  echo.
  echo Modele : %%M
  "%~dp0.venv\Scripts\python.exe" "%~dp0depth.py" --input "%~1" --model %%M
  if errorlevel 1 (
    echo Le modele %%M a echoue.
    pause
    exit /b 1
  )
)
echo.
echo Les cartes sont dans results\relative, results\hybrid et results\large.
pause
