import subprocess
from pathlib import Path
from src.utils.helpers import log, ensure_dir

class CertificateManager:
    """
    Verwaltet Code-Signing Zertifikate mittels nativer Windows PowerShell Befehle.
    Erstellt .pfx und .cer Dateien.
    """
    
    def __init__(self, cert_store_path: Path):
        self.store_path = cert_store_path
        ensure_dir(self.store_path)

    def list_certificates(self):
        """Listet alle verfügbaren PFX-Dateien im Store auf."""
        certs = list(self.store_path.glob("*.pfx"))
        return certs

    def create_certificate(self, name: str, password: str) -> tuple[Path, Path]:
        """
        Erstellt ein Self-Signed Code Signing Zertifikat.
        1. Erstellt Cert im Windows Cert Store (User scope).
        2. Exportiert es als PFX (mit Passwort) und CER.
        """
        log.info(f"Erstelle neues Zertifikat: {name}...")
        
        pfx_path = self.store_path / f"{name}.pfx"
        cer_path = self.store_path / f"{name}.cer"
        
        # PowerShell Script Konstruktion
        # Wir nutzen New-SelfSignedCertificate mit Type CodeSigning
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        try {{
            $cert = New-SelfSignedCertificate -DnsName "{name}" -CertStoreLocation "Cert:\\CurrentUser\\My" -Type CodeSigningCert -FriendlyName "PySignBuilder-{name}"
            
            # Passwort SecureString erstellen
            $pwd = ConvertTo-SecureString -String "{password}" -Force -AsPlainText
            
            # Export als PFX
            Export-PfxCertificate -Cert $cert -FilePath "{pfx_path.absolute()}" -Password $pwd
            
            # Export als CER (Public Key)
            Export-Certificate -Cert $cert -FilePath "{cer_path.absolute()}"
            
            Write-Output "SUCCESS_CERT_CREATED"
        }} catch {{
            Write-Error $_
        }}
        """
        
        try:
            # Ausführung via subprocess
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                text=True,
                check=True
            )
            
            if pfx_path.exists() and cer_path.exists():
                log.success(f"Zertifikat erstellt: {pfx_path.name}")
                return pfx_path, cer_path
            else:
                log.error("Zertifikatserstellung fehlgeschlagen (Dateien nicht gefunden).")
                log.debug(result.stderr)
                raise FileNotFoundError("Zertifikate wurden nicht erstellt.")
                
        except subprocess.CalledProcessError as e:
            log.error(f"PowerShell Fehler: {e.stderr}")
            raise e

    def create_install_script(self, output_dir: Path, cert_name: str, cer_file: Path):
        """Erstellt eine Batch-Datei für den Enduser zur Installation des Zertifikats."""
        bat_path = output_dir / "install_cert.bat"
        cer_filename = cer_file.name
        
        content = f"""@echo off
echo Installiere Zertifikat fuer {cert_name}...
echo.
echo ACHTUNG: Bitte Bestaetigen Sie den Administrator-Dialog.
echo Das Zertifikat wird in 'TrustedPeople' und 'Root' importiert.
echo.
certutil -addstore -f "TrustedPeople" "%~dp0{cer_filename}"
certutil -addstore -f "Root" "%~dp0{cer_filename}"
echo.
echo Zertifikat installiert. Die Anwendung sollte nun ohne Warnung starten.
pause
"""
        with open(bat_path, "w") as f:
            f.write(content)
        log.info(f"Installations-Skript erstellt: {bat_path}")
