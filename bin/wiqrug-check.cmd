@echo off
rem wiqrug-check for PowerShell and cmd: the same probe as bin/wiqrug-check, which Git Bash runs.
rem Untested: wiqrug is proved on Linux only. Every argument goes to lib\project_check.py, except
rem --python (the name found), --run SCRIPT [ARG...] (SCRIPT under that Python) and --skill [ARG...]
rem (the same answer, always exit 0: Claude Code aborts a skill whose snippet exits non-zero).
rem --skill keeps exit 0 before --run too, Python or none.
setlocal
set "SKILL="
if "%~1"=="--skill" ( set "SKILL=1" & shift )
set "PY="
for %%P in (python3 python py) do if not defined PY (
    %%P -c "import sys; sys.exit(sys.version_info < (3, 9))" >nul 2>&1 && set "PY=%%P"
)
if not defined PY (
    echo wiqrug: Python 3.9 or newer is not installed (none of python3, python, py runs it^) - install Python, then run this again.
    if defined SKILL exit /b 0
    exit /b 3
)
if "%~1"=="--python" if "%~2"=="" ( echo %PY%& exit /b 0 )
if "%~1"=="--run" goto :run
if defined SKILL goto :skill
%PY% "%~dp0..\lib\project_check.py" %*
exit /b %errorlevel%

:skill
%PY% "%~dp0..\lib\project_check.py" %1 %2 %3 %4
exit /b 0

:run
shift
set "ARGS="
:collect
if "%~1"=="" goto :go
set ARGS=%ARGS% %1
shift
goto :collect
:go
if defined SKILL ( %PY% %ARGS% 2>&1 & exit /b 0 )
%PY% %ARGS%
exit /b %errorlevel%
