<#
.SYNOPSIS
    ExeFile Builder Framework - Master Launcher (VENV Edition)
    Author: Smilez1985 & Gemini
.DESCRIPTION
    - Prüft/Installiert globales Python & Git (für die Basis)
    - Erstellt/Nutzt ein lokales Virtual Environment (.venv)
    - Installiert Dependencies NUR in dieses VENV
    - Startet die GUI isoliert im VENV
#>

# -----------------------------------------------------------------------------
# 1. ADMIN RECHTE PRÜFEN & ANFORDERN
# -----------------------------------------------------------------------------
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Warte auf Administrator-Rechte..." -ForegroundColor Yellow
    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "powershell.exe"
    $processInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$($MyInvocation.MyCommand.Definition)`""
    $processInfo.Verb = "runas"
    try {
        [System.Diagnostics.Process]::Start($processInfo)
    } catch {
        Write-Error "Konnte Admin-Rechte nicht anfordern. Abbruch."
    }
    exit
}

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
Clear-Host
Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host "#    EXE BUILDER - VENV LAUNCHER & SETUP SYSTEM         #" -ForegroundColor Cyan
Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# 2. HILFSFUNKTIONEN
# -----------------------------------------------------------------------------
function Wait-For-Internet {
    Write-Host "Prüfe Internetverbindung..." -NoNewline
    while (-not (Test-Connection 8.8.8.8 -Quiet -Count 1)) {
        Write-Host "." -NoNewline -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    Write-Host " OK." -ForegroundColor Green
}

function Check-And-Install-Global-Python {
    # Wir brauchen ein globales Python nur, um das VENV zu erstellen
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        Write-Host "✅ Globales Python gefunden (Systembasis)." -ForegroundColor Green
    } else {
        Write-Host "❌ Python fehlt. Starte Download & Installation..." -ForegroundColor Red
        Wait-For-Internet
        
        # Web Installer Fallback (zuverlässiger als Winget bei PATH Problemen)
        $url = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
        $output = "$env:TEMP\python_installer.exe"
        try {
            Invoke-WebRequest -Uri $url -OutFile $output
            Start-Process -FilePath $output -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
            Write-Host "Python installiert." -ForegroundColor Green
        } catch {
            Write-Error "Installation fehlgeschlagen: $_"
            Pause
            exit 1
        }
        # Path Refresh für aktuelle Session
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
}

function Check-And-Install-Git {
    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        Write-Host "❌ Git fehlt. Installiere..." -ForegroundColor Red
        Wait-For-Internet
        try {
            winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
        } catch {
            Write-Warning "Winget fehlgeschlagen, bitte Git manuell installieren."
        }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } else {
        Write-Host "✅ Git gefunden." -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# 3. VENV LOGIK (Der Kern)
# -----------------------------------------------------------------------------

# A) Basis-Checks
Check-And-Install-Global-Python
Check-And-Install-Git

# B) Repo Update
if (Test-Path ".git") {
    Write-Host "Prüfe auf Updates (git pull)..." -ForegroundColor Cyan
    try { git pull } catch { Write-Warning "Git Pull nicht möglich (Offline?)." }
}

# C) VENV Einrichtung
$VenvPath = "$PSScriptRoot\.venv"
$VenvPython = "$VenvPath\Scripts\python.exe"
$VenvPip = "$VenvPath\Scripts\pip.exe"

Write-Host "Prüfe Virtual Environment (.venv)..." -ForegroundColor Cyan

if (-not (Test-Path $VenvPython)) {
    Write-Host "🔨 Erstelle neues VENV in $VenvPath..." -ForegroundColor Yellow
    python -m venv .venv
    
    if (-not (Test-Path $VenvPython)) {
        Write-Error "VENV Erstellung fehlgeschlagen!"
        Pause
        exit 1
    }
    Write-Host "✅ VENV erstellt." -ForegroundColor Green
} else {
    Write-Host "✅ VENV bereits vorhanden." -ForegroundColor Green
}

# D) Dependencies im VENV installieren
# Wir nutzen direkt den VENV-Pfad, das ist sicherer als 'activate'
Write-Host "Synchronisiere Dependencies im VENV..." -ForegroundColor Cyan
if (Test-Path "Requirements.txt") {
    # Ping Loop nur wenn nötig (einfacher Check)
    & $VenvPython -m pip install -r Requirements.txt
}

# E) Starten
Write-Host "🚀 Starte GUI im VENV Modus..." -ForegroundColor Green
Write-Host "---------------------------------------------------------"
Start-Sleep -Seconds 1

# Der entscheidende Aufruf: Wir starten das Script mit DEM VENV PYTHON
& $VenvPython main_gui.py

# Falls das Script crasht, Fenster offen lassen
if ($LASTEXITCODE -ne 0) {
    Write-Host "Das Programm wurde mit Fehler beendet." -ForegroundColor Red
    Pause
}
