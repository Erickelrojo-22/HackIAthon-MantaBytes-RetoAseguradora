param(
    [switch]$RegenerateData,
    [int]$ApiPort = 8010,
    [int]$StreamlitPort = 8510
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

Step "Smoke test Streamlit"
$StreamlitLog = Join-Path $ProjectRoot "streamlit.smoke.log"
$StreamlitErr = Join-Path $ProjectRoot "streamlit.smoke.err.log"
Remove-Item $StreamlitLog, $StreamlitErr -ErrorAction SilentlyContinue
$StreamlitProcess = Start-Process -WindowStyle Hidden -WorkingDirectory $ProjectRoot -FilePath $Python -ArgumentList @(
    "-m", "streamlit", "run", "src\fraudia_claims\app\main.py",
    "--server.address", "127.0.0.1",
    "--server.port", "$StreamlitPort",
    "--server.headless", "true"
) -RedirectStandardOutput $StreamlitLog -RedirectStandardError $StreamlitErr -PassThru
try {
    Start-Sleep -Seconds 10
    $Response = Invoke-WebRequest "http://127.0.0.1:$StreamlitPort" -UseBasicParsing
    Write-Host "Streamlit HTTP: $($Response.StatusCode)"
} finally {
    Stop-IfRunning $StreamlitProcess
}

Step "Listo"
Write-Host "Smoke test completo."
Write-Host "Para ejecutar manualmente:"
Write-Host ".\.venv\Scripts\python -m streamlit run src\fraudia_claims\app\main.py"
Write-Host ".\.venv\Scripts\python -m uvicorn fraudia_claims.api:app --app-dir src --reload"
