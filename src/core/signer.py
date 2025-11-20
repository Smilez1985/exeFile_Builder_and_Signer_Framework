import subprocess
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """Signiert Executables mit einem PFX Zertifikat via PowerShell."""

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name}...")
        
        timestamp_server = "http://timestamp.digicert.com"
        
        # PowerShell Script:
        # Strategie: "Clean Room" Ansatz.
        # 1. Wir versuchen aktiv, das Modul zu ENTFERNEN, um Zombie-Reste zu löschen.
        # 2. Wir laden es FRISCH neu.
        ps_script = f"""
        $OutputEncoding = [System.Text.Encoding]::UTF8
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $ErrorActionPreference = 'Stop'
        
        try {{
            # SCHRITT 1: Aufräumen (Entladen)
            # Falls Reste des Moduls im Speicher hängen, werfen wir sie raus.
            if (Get-Module -Name Microsoft.PowerShell.Security) {{
                Remove-Module Microsoft.PowerShell.Security -ErrorAction SilentlyContinue
            }}

            # SCHRITT 2: Sauber Laden
            # Wir erzwingen einen frischen Import (-Force).
            # Fehler beim Import (z.B. "TypData existiert schon") fangen wir ab, 
            # solange das Cmdlet danach verfügbar ist.
            try {{
                Import-Module Microsoft.PowerShell.Security -Force -ErrorAction Stop
            }} catch {{
                # Wir ignorieren Import-Fehler, falls Teile core-locked sind, 
                # prüfen aber sofort danach die Funktion.
            }}

            # SCHRITT 3: Funktions-Check
            if (-not (Get-Command ConvertTo-SecureString -ErrorAction SilentlyContinue)) {{
                throw "CRITICAL: Das Security-Modul konnte nicht geladen werden."
            }}

            # SCHRITT 4: Signieren
            $pwd = ConvertTo-SecureString -String "{password}" -Force -AsPlainText
            $cert = Get-PfxCertificate -FilePath "{pfx_path.absolute()}" -Password $pwd
            
            $sig = Set-AuthenticodeSignature -FilePath "{exe_path.absolute()}" -Certificate $cert -TimestampServer "{timestamp_server}"
            
            if ($sig.Status -eq 'Valid') {{
                Write-Output "SIGNATURE_VALID"
            }} else {{
                Write-Output "SIGNATURE_INVALID"
                Write-Output $sig.StatusMessage
            }}
        }} catch {{
            Write-Error $_
        }}
        """

        try:
            # Wir starten eine komplett frische PowerShell-Instanz (-NoProfile)
            # und hebeln die Richtlinien aus (-ExecutionPolicy Bypass)
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='utf-8',       # Zwingend UTF-8, um Encoding-Crashs zu verhindern
                errors='replace',       # Fehlertoleranz bei unbekannten Zeichen
                check=True
            )
            
            output = result.stdout.strip()
            if "SIGNATURE_VALID" in output:
                log.success(f"Signatur erfolgreich: {exe_path.name}")
                return True
            else:
                log.warning(f"Signatur-Status unklar oder fehlgeschlagen: {output}")
                log.debug(f"Full Output: {output}")
                return False

        except subprocess.CalledProcessError as e:
            err_msg = e.stderr if e.stderr else "Unbekannter PowerShell Fehler"
            log.error(f"Fehler beim Signieren via PowerShell: {err_msg}")
            return False
        except Exception as e:
            log.error(f"Allgemeiner Fehler im Signer: {e}")
            return False
