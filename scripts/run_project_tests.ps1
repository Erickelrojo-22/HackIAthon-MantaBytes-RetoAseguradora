param(
    [switch]$RegenerateData,
    [int]$ApiPort = 8010
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Step($Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Stop-IfRunning($Process) {
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

Step "Proyecto"
Write-Host $ProjectRoot

Step "Entorno virtual"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

if ($RegenerateData) {
    Step "Regenerando datos demo"
    & $Python scripts\generate_demo_data.py --force
} else {
    Step "Validando datos demo"
    & $Python -c "import sys; sys.path.insert(0, 'src'); from fraudia_claims.storage import initialize_demo_data; print(initialize_demo_data(force=False))"
}

Step "Pruebas unitarias"
& $Python -m unittest discover -s tests

Step "Smoke test API"
$ApiLog = Join-Path $ProjectRoot "api.smoke.log"
$ApiErr = Join-Path $ProjectRoot "api.smoke.err.log"
Remove-Item $ApiLog, $ApiErr -ErrorAction SilentlyContinue
$ApiProcess = Start-Process -WindowStyle Hidden -WorkingDirectory $ProjectRoot -FilePath $Python -ArgumentList @(
    "-m", "uvicorn", "fraudia_claims.api:app", "--app-dir", "src",
    "--host", "127.0.0.1", "--port", "$ApiPort"
) -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErr -PassThru
try {
    Start-Sleep -Seconds 6
    $Health = Invoke-RestMethod "http://127.0.0.1:$ApiPort/health"
    $Metrics = Invoke-RestMethod "http://127.0.0.1:$ApiPort/metrics"
    $Risk = Invoke-RestMethod "http://127.0.0.1:$ApiPort/claims/risk?limit=3&level=Rojo"
    Write-Host "API health: $($Health.status)"
    Write-Host "Metricas: $($Metrics.Count)"
    Write-Host "Casos rojos consultados: $($Risk.Count)"
} finally {
    Stop-IfRunning $ApiProcess
}

Step "Build frontend React"
$FrontendRoot = Join-Path $ProjectRoot "frontend"
if (Test-Path $FrontendRoot) {
    Push-Location $FrontendRoot
    try {
        npm install
        npm run build
    } finally {
        Pop-Location
    }
} else {
    throw "No existe la carpeta frontend."
}

Step "Listo"
Write-Host "Smoke test completo."
Write-Host "Para ejecutar manualmente:"
Write-Host ".\.venv\Scripts\python -m uvicorn fraudia_claims.api:app --app-dir src --reload"
Write-Host "cd frontend; npm run dev"
