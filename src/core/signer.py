import subprocess
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """Signiert Executables mit einem PFX Zertifikat via PowerShell."""

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name}...")
        
        # Hinweis: TimestampServer ist wichtig für Gültigkeit, auch wenn Cert abläuft.
        timestamp_server = "http://timestamp.digicert.com"
        
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        try {{
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
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
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
            log.error(f"Fehler beim Signieren via PowerShell: {e.stderr}")
            return False
