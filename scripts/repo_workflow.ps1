param(
    [string]$RemoteUrl = "https://github.com/Erickelrojo-22/HackIAthon-MantaBytes-RetoAseguradora.git",
    [string]$Branch = "main",
    [string]$Message = "Update FraudIA backend",
    [switch]$SetupRemote,
    [switch]$RegenerateData,
    [switch]$Commit,
    [switch]$Pull,
    [switch]$Push
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Step($Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

Step "Proyecto"
Write-Host $ProjectRoot

Step "Git"
$isRepo = $true
try {
    git rev-parse --show-toplevel | Out-Null
} catch {
    $isRepo = $false
}

if (-not $isRepo) {
    if (-not $SetupRemote) {
        Write-Warning "Esta carpeta no tiene .git. Ejecuta con -SetupRemote para conectarla al repo remoto."
    } else {
        Step "Inicializando repo local"
        git init
        git branch -M $Branch
        git remote add origin $RemoteUrl
        $isRepo = $true
    }
}

if ($isRepo) {
    git remote -v
    git status --short --branch
}

if ($RegenerateData) {
    Step "Regenerando dataset demo"
    python scripts\generate_demo_data.py --force
}

Step "Ejecutando pruebas"
python -m unittest discover -s tests

Step "Probando API sin levantar servidor"
python -c "import sys; sys.path.insert(0, 'src'); from fraudia_claims.api import health; print(health())"

if ($isRepo -and $Commit) {
    Step "Commit"
    git add .
    git commit -m $Message
}

if ($isRepo -and $Pull) {
    Step "Pull"
    git pull --rebase origin $Branch
}

if ($isRepo -and $Push) {
    Step "Push"
    git push origin $Branch
}

Step "Demo local"
Write-Host "API:      python -m uvicorn fraudia_claims.api:app --app-dir src --reload"
Write-Host "Frontend: cd frontend; npm run dev"
