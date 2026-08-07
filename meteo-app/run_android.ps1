param(
    [string]$Device = "android-15"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "lib\config\secrets.local.dart")) {
    Write-Host "Generation des secrets Supabase..."
    python tool\sync_secrets.py
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Echec sync_secrets.py - voir README."
    }
}

$flutterDevices = flutter devices 2>&1 | Out-String
if ($flutterDevices -notmatch "emulator|android") {
    Write-Host "Demarrage de l emulateur $Device..."
    flutter emulators --launch $Device
    Write-Host "Attente du demarrage de l emulateur - 30 secondes..."
    Start-Sleep -Seconds 30
}

flutter run -d android
