$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $py) { throw "Python 3.10+ is required." }

if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    if ($py.Name -eq "py.exe") { & py -3 -m venv .venv } else { & python -m venv .venv }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check -r requirements-lesson3.txt
& $venvPython -m pytest -q
& $venvPython -m compileall -q packages integrations experiments tests
& $venvPython -m experiments.retrieval_comparison

Write-Host "SUCCESS: lesson 3 context pipeline is runnable." -ForegroundColor Green
