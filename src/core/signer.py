import subprocess
from pathlib import Path
from src.utils.helpers import log

class AuthenticodeSigner:
    """Signiert Executables mit einem PFX Zertifikat via PowerShell."""

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str):
        log.info(f"Signiere {exe_path.name} mit {pfx_path.name}...")
        
        # PowerShell Befehl für Set-AuthenticodeSignature
        # Hinweis: TimestampServer ist wichtig für Gültigkeit, auch wenn Cert abläuft.
        timestamp_server = "http://timestamp.digicert.com"
        
        ps_script = f"""
        $pwd = ConvertTo-SecureString -String "{password}" -Force -AsPlainText
        $cert = Get-PfxCertificate -FilePath "{pfx_path.absolute()}" -Password $pwd
        Set-AuthenticodeSignature -FilePath "{exe_path.absolute()}" -Certificate $cert -TimestampServer "{timestamp_server}"
        """

        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Überprüfung ob "Valid" im Output steht
            if "Valid" in result.stdout:
                log.success(f"Signatur erfolgreich: {exe_path.name}")
                return True
            else:
                log.warning("Signatur-Prozess lief durch, aber Status unklar.")
                log.debug(result.stdout)
                return False

        except subprocess.CalledProcessError as e:
            log.error(f"Fehler beim Signieren: {e.stderr}")
            raise e
