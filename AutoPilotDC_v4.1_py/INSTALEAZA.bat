@echo off
rem ============================================================
rem  AutoPilot DC v4.1 - instalarea pachetelor Python necesare
rem  Dublu click. Fereastra ramane deschisa pana apesi o tasta,
rem  ca sa vezi daca a mers sau ce eroare a aparut.
rem  Nu cere drepturi de administrator (pachetele se instaleaza
rem  doar pentru utilizatorul curent).
rem
rem  Parametru optional: calea catre python.exe (AutoPilot_DC.pyw
rem  il trimite, ca pachetele sa ajunga exact in Python-ul lui).
rem
rem  ATENTIE la editare: fisierul trebuie sa ramana ASCII + CRLF,
rem  iar parantezele din "echo" din interiorul unui bloc if ( ... )
rem  se scriu ^( si ^) - altfel cmd inchide blocul mai devreme.
rem ============================================================
setlocal EnableExtensions
title AutoPilot DC - instalare pachete
cd /d "%~dp0"

echo.
echo  ==========================================================
echo     AutoPilot DC v4.1 - instalare pachete Python
echo  ==========================================================
echo.

rem -- 1. Python: cel primit ca parametru, altfel "py", altfel "python" --
set "PY="
if not "%~1"=="" if exist "%~1" set PY="%~1"
if defined PY goto :python_ok
py -3 -c "import sys" >nul 2>nul && set "PY=py -3"
if defined PY goto :python_ok
python -c "import sys" >nul 2>nul && set "PY=python"
if defined PY goto :python_ok

echo  [EROARE] Python nu este instalat sau nu este in PATH.
echo.
echo  Instaleaza Python 3.9 sau mai nou de pe https://www.python.org/downloads/
echo  (sau din Company Portal / Software Center, daca exista acolo)
echo  si bifeaza "Add python.exe to PATH" la instalare.
echo  Apoi ruleaza din nou acest fisier.
goto :fail

:python_ok
rem Python isi afiseaza singur versiunea si calea (fara "for /f": cmd strica ghilimelele la cai cu spatii)
%PY% -c "import sys; print('  Python gasit: ' + sys.version.split()[0]); print('  Cale:         ' + sys.executable); sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo.
    echo  [EROARE] E nevoie de Python 3.9 sau mai nou.
    goto :fail
)
echo.

rem -- 2. pip --
%PY% -m pip --version >nul 2>nul
if not errorlevel 1 goto :pip_ok
echo  pip lipseste - il instalez...
%PY% -m ensurepip --user
if errorlevel 1 (
    echo  [EROARE] pip nu a putut fi instalat.
    goto :fail
)

:pip_ok
rem -- 3. Pachetele --
echo  Instalez pachetele din requirements.txt (poate dura 1-3 minute)...
echo  ----------------------------------------------------------
%PY% -m pip install --user --upgrade --disable-pip-version-check -r requirements.txt
if not errorlevel 1 goto :verify

echo.
echo  ----------------------------------------------------------
echo  Prima incercare a esuat. Reincerc pentru reteaua firmei
echo  (inspectie SSL / certificate)...
echo  ----------------------------------------------------------
%PY% -m pip install --user --upgrade --disable-pip-version-check --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
if errorlevel 1 goto :pipfail

:verify
rem -- 4. Verificare: fiecare pachet se poate importa --
echo.
echo  ----------------------------------------------------------
echo  Verificare:
%PY% verifica_instalare.py
if errorlevel 1 (
    echo.
    echo  [ATENTIE] Unele pachete lipsesc. Vezi mesajele de mai sus.
    goto :fail
)

rem -- 5. Scurtatura pe Desktop (optional) --
echo.
choice /c DN /n /m "  Creez o scurtatura AutoPilot DC pe Desktop? [D = da / N = nu] "
if errorlevel 2 goto :done
rem scurtatura porneste direct pythonw.exe: fara fereastra CMD, cu iconita aplicatiei
%PY% app_shell.py scurtatura
if errorlevel 1 goto :shortcut_failed
goto :done

:shortcut_failed
echo  Scurtatura nu a putut fi creata (nu e grav: porneste cu dublu click pe AutoPilot_DC.pyw).

:done
echo.
echo  ==========================================================
echo     GATA. Porneste aplicatia cu dublu click pe AutoPilot_DC.pyw
echo  ==========================================================
echo.
echo  Apasa orice tasta pentru a inchide fereastra...
pause >nul
exit /b 0

:pipfail
echo.
echo  ==========================================================
echo  [EROARE] Instalarea pachetelor a esuat.
echo.
echo  Cauze frecvente:
echo   - fara internet / proxy-ul firmei: incearca din reteaua firmei
echo     sau seteaza proxy-ul, ex:  set HTTPS_PROXY=http://proxy:port
echo   - antivirusul a blocat un fisier: ruleaza din nou
echo   - mesajul exact e mai sus, in fereastra (copiaza-l pentru suport)
echo  ==========================================================
goto :fail_pause

:fail
echo.
echo  ==========================================================
echo     Instalarea NU s-a terminat. Citeste mesajul de mai sus.
echo  ==========================================================

:fail_pause
echo.
echo  Apasa orice tasta pentru a inchide fereastra...
pause >nul
exit /b 1
