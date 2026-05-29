param(
    [int]$ApiPort = 8010
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Step($Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Restore-Env($Snapshot) {
    foreach ($name in $Snapshot.Keys) {
        if ($null -eq $Snapshot[$name]) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        } else {
            Set-Item "Env:$name" $Snapshot[$name]
        }
    }
}

function Stop-IfRunning($Process) {
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    }
}

function Remove-TempFile($Path) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return
    }
    try {
        if ([System.IO.File]::Exists($Path)) {
            [System.IO.File]::Delete($Path)
        }
    } catch {
        Write-Host "No se pudo borrar temporal $Path; se puede eliminar manualmente." -ForegroundColor Yellow
    }
}

$EnvSnapshot = @{
    FRAUDIA_DB_BACKEND = $env:FRAUDIA_DB_BACKEND
    FRAUDIA_DB_PATH = $env:FRAUDIA_DB_PATH
    FRAUDIA_DATA_SOURCE = $env:FRAUDIA_DATA_SOURCE
    FRAUDIA_DATABASE_URL = $env:FRAUDIA_DATABASE_URL
    FRAUDIA_COMPANY_DATA_DIR = $env:FRAUDIA_COMPANY_DATA_DIR
}

try {
    Step "Dependencias"
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        python -m venv .venv
    }
    $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    & $Python -m pip install -r requirements.txt

    Step "Modo online Supabase"
    Restore-Env $EnvSnapshot
    Remove-Item Env:FRAUDIA_DB_BACKEND, Env:FRAUDIA_DB_PATH, Env:FRAUDIA_DATA_SOURCE, Env:FRAUDIA_DATABASE_URL, Env:FRAUDIA_COMPANY_DATA_DIR -ErrorAction SilentlyContinue
    & $Python scripts\verify_data_source.py

    Step "Modo offline CSV"
    $OfflineDb = Join-Path $env:TEMP "fraudia_claims_offline_csv_readiness.db"
    Remove-TempFile $OfflineDb
    $env:FRAUDIA_DB_BACKEND = "sqlite"
    $env:FRAUDIA_DATA_SOURCE = "csv"
    $env:FRAUDIA_DB_PATH = $OfflineDb
    Remove-Item Env:FRAUDIA_DATABASE_URL -ErrorAction SilentlyContinue
    & $Python scripts\generate_demo_data.py --force
    & $Python scripts\verify_data_source.py
    Remove-TempFile $OfflineDb

    Step "Pruebas unitarias"
    $TestDb = Join-Path $env:TEMP "fraudia_claims_tests_readiness.db"
    Remove-TempFile $TestDb
    $env:FRAUDIA_DB_BACKEND = "sqlite"
    $env:FRAUDIA_DATA_SOURCE = "csv"
    $env:FRAUDIA_DB_PATH = $TestDb
    & $Python -m unittest discover -s tests
    Remove-TempFile $TestDb

    Step "Smoke API online"
    Restore-Env $EnvSnapshot
    Remove-Item Env:FRAUDIA_DB_BACKEND, Env:FRAUDIA_DB_PATH, Env:FRAUDIA_DATA_SOURCE, Env:FRAUDIA_DATABASE_URL, Env:FRAUDIA_COMPANY_DATA_DIR -ErrorAction SilentlyContinue
    $ApiLog = Join-Path $ProjectRoot "api.readiness.log"
    $ApiErr = Join-Path $ProjectRoot "api.readiness.err.log"
    Remove-Item $ApiLog, $ApiErr -ErrorAction SilentlyContinue
    $ApiProcess = Start-Process -WindowStyle Hidden -WorkingDirectory $ProjectRoot -FilePath $Python -ArgumentList @(
        "-m", "uvicorn", "fraudia_claims.api:app", "--app-dir", "src",
        "--host", "127.0.0.1", "--port", "$ApiPort"
    ) -RedirectStandardOutput $ApiLog -RedirectStandardError $ApiErr -PassThru
    try {
        $Headers = @{ Authorization = "Bearer demo-token-analista" }
        $Health = $null
        for ($attempt = 1; $attempt -le 30; $attempt++) {
            if ($ApiProcess.HasExited) {
                throw "La API termino antes del smoke test. Revisa $ApiErr"
            }
            try {
                $Health = Invoke-RestMethod "http://127.0.0.1:$ApiPort/health" -TimeoutSec 2
                break
            } catch {
                Start-Sleep -Seconds 2
            }
        }
        if ($null -eq $Health) {
            throw "La API no respondio en http://127.0.0.1:$ApiPort/health. Revisa $ApiErr"
        }
        $Kpis = Invoke-RestMethod "http://127.0.0.1:$ApiPort/dashboard/kpis" -Headers $Headers
        $Agent = Invoke-RestMethod "http://127.0.0.1:$ApiPort/agent/question" -Method Post -Headers $Headers -ContentType "application/json" -Body '{"question":"Que proveedores concentran el 80% de las alertas rojas?","scope":"global"}'
        Write-Host "API health: $($Health.status) / $($Health.database.backend) / $($Health.database.data_source)"
        Write-Host "Siniestros: $($Kpis.kpis.total_siniestros)"
        Write-Host "Agente: $($Agent.source)"
    } finally {
        Stop-IfRunning $ApiProcess
    }

    Step "Build frontend"
    Push-Location "frontend"
    try {
        npm install
        npm run build
    } finally {
        Pop-Location
    }

    Step "Entregables"
    $RequiredFiles = @(
        "README.md",
        "requirements.txt",
        ".env.example",
        "docs\arquitectura.md",
        "docs\modelo_datos.md",
        "docs\reglas_negocio.md",
        "docs\uso_ia.md",
        "docs\limitaciones.md",
        "docs\datos_supabase.md",
        "docs\checklist_entrega.md",
        "presentation\pitch_ejecutivo.md",
        "presentation\pitch_ejecutivo.pdf"
    )
    foreach ($file in $RequiredFiles) {
        if (-not (Test-Path $file)) {
            throw "Falta entregable requerido: $file"
        }
        Write-Host "OK $file"
    }

    Step "Listo"
    Write-Host "FraudIA esta listo para demo online Supabase y offline CSV."
} finally {
    Restore-Env $EnvSnapshot
}
