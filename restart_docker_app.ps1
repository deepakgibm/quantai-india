# Restart-DockerApp.ps1
# This script stops the docker-compose app, restarts Docker Desktop, waits for Docker daemon, and restarts the app.

$ScriptName = $MyInvocation.MyCommand.Name
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change directory to the script's directory (workspace root)
Set-Location -Path $ScriptDir

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   QuantAI India - Docker & App Restart Script    " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Stop the docker-compose stack if it is running
Write-Host "[1/5] Stopping the Docker Compose application..." -ForegroundColor Yellow
docker compose down
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: docker compose down failed or no stack was running. Continuing..." -ForegroundColor Gray
} else {
    Write-Host "Docker Compose application stopped successfully." -ForegroundColor Green
}

# 2. Terminate Docker Desktop processes
Write-Host "[2/5] Stopping Docker Desktop processes..." -ForegroundColor Yellow
$dockerProcesses = @("Docker Desktop", "com.docker.backend", "com.docker.build", "docker")
foreach ($proc in $dockerProcesses) {
    if (Get-Process -Name $proc -ErrorAction SilentlyContinue) {
        Write-Host "Killing process: $proc" -ForegroundColor Gray
        Stop-Process -Name $proc -Force -ErrorAction SilentlyContinue
    }
}

# Wait for processes to release resources
Start-Sleep -Seconds 5

# 3. Start Docker Desktop
$dockerPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $dockerPath) {
    Write-Host "[3/5] Launching Docker Desktop from: $dockerPath" -ForegroundColor Yellow
    Start-Process -FilePath $dockerPath
} else {
    Write-Host "Error: Docker Desktop executable not found at $dockerPath" -ForegroundColor Red
    Exit 1
}

# 4. Wait for Docker daemon to become ready
Write-Host "[4/5] Waiting for Docker daemon to become responsive..." -ForegroundColor Yellow
$timeout = 120
$elapsed = 0
$interval = 5
$dockerReady = $false

while ($elapsed -lt $timeout) {
    docker info > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        break
    }
    Start-Sleep -Seconds $interval
    $elapsed += $interval
    Write-Host "Waiting for Docker daemon... ($elapsed/$timeout seconds elapsed)" -ForegroundColor Gray
}

if (-not $dockerReady) {
    Write-Host "Error: Docker daemon did not respond within $timeout seconds." -ForegroundColor Red
    Exit 1
}
Write-Host "Docker daemon is ready!" -ForegroundColor Green

# 5. Start the Docker Compose stack
Write-Host "[5/5] Starting the Docker Compose application..." -ForegroundColor Yellow
docker compose up -d --build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Docker Compose application started successfully!" -ForegroundColor Green
    Write-Host "`nContainer Status:" -ForegroundColor Cyan
    docker compose ps
} else {
    Write-Host "Error: Failed to start the Docker Compose application." -ForegroundColor Red
    Exit 1
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "                 Restart Complete!                " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
