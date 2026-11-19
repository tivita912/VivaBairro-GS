param([string]$PythonExe)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($PythonExe) {
    & $PythonExe -c "import sys; assert sys.version_info[:2] == (3,14)"
    if ($LASTEXITCODE -ne 0) { throw 'Use Python 3.14 x64.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) { & $PythonExe -m venv .venv }
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    if (-not (Test-Path '.venv/Scripts/python.exe')) { & py -3.14 -m venv .venv }
} else {
    if (-not (Test-Path '.venv/Scripts/python.exe')) { & python -m venv .venv }
}
if ($LASTEXITCODE -and -not (Test-Path '.venv/Scripts/python.exe')) { throw 'Falha ao criar o ambiente.' }
$ProjectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
& $ProjectPython -c "import sys,struct; assert sys.version_info[:2] == (3,14) and struct.calcsize('P') == 8; print(sys.version)"
if ($LASTEXITCODE -ne 0) { throw 'O ambiente precisa de Python 3.14 x64.' }
& $ProjectPython -m pip install -r requirements.txt -r requirements-academic.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
& $ProjectPython -m pip check
exit $LASTEXITCODE
