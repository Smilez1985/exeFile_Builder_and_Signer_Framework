import subprocess
import os
from pathlib import Path
from src.utils.helpers import log, ensure_dir

class CertificateManager:
    """
    Verwaltet Code-Signing Zertifikate.
    Unterstützt zwei Backends:
    1. Native Windows PowerShell (Self-Signed)
    2. OpenSSL (Cross-Platform Standard)
    """
    
    def __init__(self, cert_store_path: Path):
        self.store_path = cert_store_path
        ensure_dir(self.store_path)

    def list_certificates(self):
        return list(self.store_path.glob("*.pfx"))

    def create_certificate(self, name: str, password: str, use_openssl: bool = False) -> tuple[Path, Path]:
        """Factory-Methode: Wählt das Backend."""
        if use_openssl:
            return self._create_certificate_openssl(name, password)
        else:
            return self._create_certificate_powershell(name, password)

    def _create_certificate_openssl(self, name: str, password: str) -> tuple[Path, Path]:
        """Erstellt Zertifikat via OpenSSL subprocess."""
        log.info(f"Erstelle Zertifikat '{name}' via OpenSSL...")
        
        key_path = self.store_path / f"{name}.key"
        csr_path = self.store_path / f"{name}.csr"
        crt_path = self.store_path / f"{name}.cer" # Windows mag .cer Endung
        pfx_path = self.store_path / f"{name}.pfx"
        cnf_path = self.store_path / "temp_openssl.cnf"

        # 1. Config erstellen für Code Signing Extensions
        # Das ist wichtig, sonst akzeptiert Windows die Signatur nicht als "Code Signing"
        openssl_cnf = f"""
        [req]
        distinguished_name = req_distinguished_name
        x509_extensions = v3_req
        prompt = no
        [req_distinguished_name]
        CN = {name}
        O = ExeBuilder Framework
        C = DE
        [v3_req]
        keyUsage = critical, digitalSignature
        extendedKeyUsage = codeSigning
        """
        with open(cnf_path, "w") as f:
            f.write(openssl_cnf)

        try:
            # 2. Private Key & Certificate generieren (in einem Rutsch self-signed)
            # openssl req -x509 -nodes -days 3650 -newkey rsa:4096 ...
            subprocess.run([
                "openssl", "req", "-x509", "-nodes", "-days", "3650",
                "-newkey", "rsa:4096",
                "-keyout", str(key_path),
                "-out", str(crt_path),
                "-config", str(cnf_path)
            ], check=True, capture_output=True)

            # 3. In PFX konvertieren (pkcs12)
            subprocess.run([
                "openssl", "pkcs12", "-export",
                "-out", str(pfx_path),
                "-inkey", str(key_path),
                "-in", str(crt_path),
                "-passout", f"pass:{password}"
            ], check=True, capture_output=True)

            log.success(f"OpenSSL Zertifikat erstellt: {pfx_path.name}")
            
            # Aufräumen (Key und Config löschen, Cert behalten für Install-Script)
            if key_path.exists(): os.remove(key_path)
            if cnf_path.exists(): os.remove(cnf_path)

            return pfx_path, crt_path

        except subprocess.CalledProcessError as e:
            log.error("OpenSSL Fehler. Ist OpenSSL installiert?")
            log.debug(str(e))
            if hasattr(e, 'stderr'): log.debug(e.stderr.decode())
            raise RuntimeError("OpenSSL Certificate creation failed")
        except FileNotFoundError:
            log.error("OpenSSL Executable nicht gefunden! Bitte 'ensure_system_tools' laufen lassen.")
            raise

    def _create_certificate_powershell(self, name: str, password: str) -> tuple[Path, Path]:
        """Erstellt Zertifikat via native Windows PowerShell (New-SelfSignedCertificate)."""
        log.info(f"Erstelle Zertifikat '{name}' via PowerShell...")
        
        pfx_path = self.store_path / f"{name}.pfx"
        cer_path = self.store_path / f"{name}.cer"
        
        ps_script = f"""
        $ErrorActionPreference = 'Stop'
        try {{
            $cert = New-SelfSignedCertificate -DnsName "{name}" -CertStoreLocation "Cert:\\CurrentUser\\My" -Type CodeSigningCert -FriendlyName "PySignBuilder-{name}"
            $pwd = ConvertTo-SecureString -String "{password}" -Force -AsPlainText
            Export-PfxCertificate -Cert $cert -FilePath "{pfx_path.absolute()}" -Password $pwd
            Export-Certificate -Cert $cert -FilePath "{cer_path.absolute()}"
            Write-Output "SUCCESS_CERT_CREATED"
        }} catch {{
            Write-Error $_
        }}
        """
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, check=True
            )
            if pfx_path.exists() and cer_path.exists():
                log.success(f"PowerShell Zertifikat erstellt: {pfx_path.name}")
                return pfx_path, cer_path
            else:
                raise FileNotFoundError("Zertifikate wurden nicht erstellt.")
        except subprocess.CalledProcessError as e:
            log.error(f"PowerShell Fehler: {e.stderr}")
            raise e

    def create_install_script(self, output_dir: Path, cert_name: str, cer_file: Path):
        """Erstellt Batch-Datei für Import in Trusted Root."""
        bat_path = output_dir / "install_cert.bat"
        cer_filename = cer_file.name
        content = f"""@echo off
echo Installiere Zertifikat: {cert_name}
echo Benoetigt Administrator-Rechte.
certutil -addstore -f "TrustedPeople" "%~dp0{cer_filename}"
certutil -addstore -f "Root" "%~dp0{cer_filename}"
pause
"""
        with open(bat_path, "w") as f:
            f.write(content)
        log.info(f"Installations-Skript erstellt: {bat_path}")
