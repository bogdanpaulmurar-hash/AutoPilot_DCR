@echo off
rem Compileaza si porneste AutoPilot DC (C#).
rem Build-ul se face in %LOCALAPPDATA%\AutoPilotDC_build, NU in Google Drive
rem (Google Drive blocheaza scrierea fisierelor .exe si restore-ul NuGet).
cd /d "%~dp0"
dotnet build "AutoPilotDC.UI\AutoPilotDC.UI.csproj" -nologo -v q --artifacts-path "%LOCALAPPDATA%\AutoPilotDC_build"
if errorlevel 1 (
    echo.
    echo Build esuat. Daca eroarea e "Cannot create a file when that file already exists", ruleaza din nou.
    pause
    exit /b 1
)
start "" "%LOCALAPPDATA%\AutoPilotDC_build\bin\AutoPilotDC.UI\debug\AutoPilotDC.UI.exe"
