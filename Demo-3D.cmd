@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0reconstruct.py" --input "%~dp0source\assets\examples\demo01.jpg" --model outdoor --max-depth 35 --open
if errorlevel 1 echo Une erreur est survenue. Lisez le message ci-dessus.
pause
