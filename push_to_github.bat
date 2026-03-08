@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
  echo Usage: push_to_github.bat YOUR_GITHUB_USERNAME
  echo Example: push_to_github.bat johndoe
  echo.
  echo First create the repo on GitHub:
  echo   1. Go to https://github.com/new
  echo   2. Repository name: Analytics_Graph_Share
  echo   3. Leave "Add a README" UNCHECKED
  echo   4. Click Create repository
  exit /b 1
)

set "USER=%~1"
git remote remove origin 2>nul
git remote add origin "https://github.com/%USER%/Analytics_Graph_Share.git"
git branch -M main
git push -u origin main

endlocal
