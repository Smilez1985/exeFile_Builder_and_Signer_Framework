import subprocess
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """Signiert Executables mit einem PFX Zertifikat via PowerShell."""

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name}...")
        
        timestamp_server = "http://timestamp.digicert.com"
        
        # PowerShell Script:
        # Wir verlassen uns auf Autoloading der Module, da wir Bypass nutzen.
        ps_script = f"""
        $OutputEncoding = [System.Text.Encoding]::UTF8
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $ErrorActionPreference = 'Stop'
        
        try {{
            # WICHTIG: Kein manuelles Import-Module mehr!
            # Durch -ExecutionPolicy Bypass lädt PowerShell das Nötige selbst.

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
            # Wir behalten "-ExecutionPolicy Bypass", um Rechteprobleme zu lösen
            result = subprocess.run(
                ["powershell", "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
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
