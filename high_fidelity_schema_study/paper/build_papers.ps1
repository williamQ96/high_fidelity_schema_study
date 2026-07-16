param(
    [string]$Tectonic = "C:\Users\izayo\.cache\codex-tools\tectonic-0.16.9\tectonic.exe"
)

$ErrorActionPreference = "Stop"
$PaperDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDir = Join-Path $PaperDir "build"

if (-not (Test-Path -LiteralPath $Tectonic)) {
    throw "Tectonic executable not found: $Tectonic"
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null

Push-Location $PaperDir
try {
    & $Tectonic --keep-logs --keep-intermediates --outdir $BuildDir semantic_architecture_study_en.tex
    if ($LASTEXITCODE -ne 0) { throw "English manuscript compilation failed" }
    & $Tectonic --keep-logs --keep-intermediates --outdir $BuildDir semantic_architecture_study_zh.tex
    if ($LASTEXITCODE -ne 0) { throw "Chinese manuscript compilation failed" }
}
finally {
    Pop-Location
}

Get-ChildItem -LiteralPath $BuildDir -Filter "*.pdf" | Select-Object Name, Length, LastWriteTime
