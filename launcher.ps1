<#
.SYNOPSIS
    ExeFile Builder Framework - Master Launcher & Installer
    Author: Smilez1985 & Gemini
.DESCRIPTION
    Dieses Script übernimmt die vollständige Einrichtung:
    - Prüft/Installiert Python & Git (Winget oder Direct Download)
    - Setzt Environment Variablen (PATH)
    - Aktualisiert das Repo (Git Pull)
    - Startet die GUI
#>

# -----------------------------------------------------------------------------
# 1. ADMIN RECHTE PRÜFEN & ANFORDERN
# -----------------------------------------------------------------------------
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Warte auf Administrator-Rechte für Installationen..." -ForegroundColor Yellow
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

# Execution Policy für diesen Prozess hart setzen (wie angefordert)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Clear-Host
Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host "#       EXE BUILDER FRAMEWORK - LAUNCHER & SETUP        #" -ForegroundColor Cyan
Write-Host "#########################################################" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------------------
# 2. HILFSFUNKTIONEN (Ping Loop etc.)
# -----------------------------------------------------------------------------
function Wait-For-Internet {
    Write-Host "Prüfe Internetverbindung..." -NoNewline
    while (-not (Test-Connection 8.8.8.8 -Quiet -Count 1)) {
        Write-Host "." -NoNewline -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
    Write-Host " OK." -ForegroundColor Green
}

function Install-Python-Web {
    Write-Host "Lade Python Installer herunter (Fallback)..." -ForegroundColor Yellow
    Wait-For-Internet
    $url = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe"
    $output = "$env:TEMP\python_installer.exe"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $output
        Write-Host "Installiere Python (Silent)... Das dauert kurz." -ForegroundColor Cyan
        # Silent Install für alle User, PATH hinzufügen
        $args = "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
        Start-Process -FilePath $output -ArgumentList $args -Wait
        Write-Host "Python Installation abgeschlossen." -ForegroundColor Green
    } catch {
        Write-Error "Download fehlgeschlagen: $_"
        exit 1
    }
}

function Install-Git-Web {
    Write-Host "Lade Git Installer herunter (Fallback)..." -ForegroundColor Yellow
    Wait-For-Internet
    $url = "https://github.com/git-for-windows/git/releases/download/v2.42.0.windows.2/Git-2.42.0.2-64-bit.exe"
    $output = "$env:TEMP\git_installer.exe"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $output
        Write-Host "Installiere Git (Silent)..." -ForegroundColor Cyan
        # Silent Install Parameters
        Start-Process -FilePath $output -ArgumentList "/VERYSILENT /NORESTART" -Wait
        Write-Host "Git Installation abgeschlossen." -ForegroundColor Green
    } catch {
        Write-Error "Download fehlgeschlagen: $_"
    }
}

function Check-And-Install-Python {
    if (Get-Command "python" -ErrorAction SilentlyContinue) {
        Write-Host "✅ Python ist installiert." -ForegroundColor Green
    } else {
        Write-Host "❌ Python fehlt. Starte Installation..." -ForegroundColor Red
        Wait-For-Internet
        
        # Versuch 1: Winget
        try {
            Write-Host "Versuche Installation via Winget..."
            winget install -e --id Python.Python.3.11 --scope machine --accept-package-agreements --accept-source-agreements
        } catch {
            Write-Warning "Winget fehlgeschlagen."
        }

        # Check ob es geklappt hat, sonst Web Installer
        # Wir müssen den Pfad refreshen
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        
        if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
            Install-Python-Web
        }
        
        # Finaler Check
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
            Write-Error "Konnte Python nicht installieren. Bitte manuell prüfen."
            Pause
            exit 1
        }
    }
}

function Check-And-Install-Git {
    if (Get-Command "git" -ErrorAction SilentlyContinue) {
        Write-Host "✅ Git ist installiert." -ForegroundColor Green
    } else {
        Write-Host "❌ Git fehlt. Starte Installation..." -ForegroundColor Red
        Wait-For-Internet
        
        try {
            winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
        } catch {
            Install-Git-Web
        }
        
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
}

# -----------------------------------------------------------------------------
# 3. LOGIK ABLAUF
# -----------------------------------------------------------------------------

# A) Dependencies prüfen
Check-And-Install-Python
Check-And-Install-Git

# B) Repo Update (Git Pull)
if (Test-Path ".git") {
    Write-Host "Prüfe auf Updates (git pull)..." -ForegroundColor Cyan
    Wait-For-Internet
    try {
        git pull
    } catch {
        Write-Warning "Git Pull fehlgeschlagen (Evtl. Konflikte oder kein Netz). Fahre fort..."
    }
}

# C) System-weite Verfügbarkeit (PATH setzen)
$currentPath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$scriptPath = $PSScriptRoot

if ($currentPath -notlike "*$scriptPath*") {
    Write-Host "Füge Framework zum System-PATH hinzu..." -ForegroundColor Yellow
    $newPath = $currentPath + ";" + $scriptPath
    [System.Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "✅ CLI ist nun systemweit verfügbar (als 'python main.py' im Ordner)." -ForegroundColor Green
} else {
    Write-Host "✅ Framework ist bereits im System-PATH." -ForegroundColor Green
}

# D) Dependencies installieren (Pip)
# Wir lassen pip laufen, um sicherzugehen, dass alles da ist
Write-Host "Prüfe Python Pakete..." -ForegroundColor Cyan
Wait-For-Internet
python -m pip install -r Requirements.txt

# E) Starten
Write-Host "🚀 Starte GUI..." -ForegroundColor Green
Start-Sleep -Seconds 1
python main_gui.py
