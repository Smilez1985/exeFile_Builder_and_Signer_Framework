from pathlib import Path
import sys

# Importiere Module - Alle Pfade explizit via 'src.'
from src.core.environment import EnvironmentManager
from src.core.certs import CertificateManager
from src.core.signer import AuthenticodeSigner
from src.core.builder import PyBuilder
from src.core.network import NetworkGuard
from src.utils.helpers import log

class BuildOrchestrator:
    """
    Koordiniert den gesamten Ablauf:
    Environment Check -> Zertifikat Prüfung -> Build -> Signierung
    """
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.cert_manager = CertificateManager(cert_store_path=Path("certs_store"))
        self.signer = AuthenticodeSigner()
        self.builder = PyBuilder()
        self.network = NetworkGuard()
        
    def setup_environment(self, project_root: Path):
        """Installiert Dependencies & System Tools (OpenSSL)."""
        self.env_manager.prepare_environment(project_root)

    def create_or_get_cert(self, cert_name: str, password: str, use_openssl: bool = False) -> Path:
        """
        Sucht nach einem existierenden PFX Zertifikat oder erstellt ein neues.
        Nutzt je nach Config OpenSSL oder PowerShell.
        """
        # 1. Suche im Store
        certs = self.cert_manager.list_certificates()
        for cert in certs:
            if cert.stem == cert_name:
                log.info(f"Vorhandenes Zertifikat gefunden: {cert.name}")
                return cert
        
        # 2. Erstelle neu
        log.info(f"Kein Zertifikat für '{cert_name}' gefunden. Erstelle neu...")
        
        # Hier wird entschieden, welche Engine genutzt wird
        pfx, cer = self.cert_manager.create_certificate(cert_name, password, use_openssl=use_openssl)
        
        # 3. Erstelle Install-Script für den Nutzer
        self.cert_manager.create_install_script(Path("builds"), cert_name, cer)
        
        return pfx

    def run_full_pipeline(self, config: dict):
        """
        Führt die komplette Pipeline basierend auf der Konfiguration aus.
        """
        script_path = Path(config.get("script_file"))
        if not script_path.exists():
            log.error(f"Eingabedatei nicht gefunden: {script_path}")
            return

        # 1. Netzwerk & Environment Check
        # (Ping Loop passiert hier drinnen, falls Tools fehlen)
        self.setup_environment(Path("."))

        # 2. Zertifikat vorbereiten
        cert_pass = config.get("cert_password", "SecretPass123!")
        cert_name = config.get("cert_name", "MySelfSignedCert")
        
        # Config Flag für OpenSSL (Standard: False/PowerShell)
        use_openssl = config.get("use_openssl", False)
        
        try:
            pfx_path = self.create_or_get_cert(cert_name, cert_pass, use_openssl=use_openssl)
        except Exception as e:
            log.error(f"Zertifikatsfehler: {e}")
            return

        # 3. Build
        exe_path = self.builder.build(
            script_path=script_path,
            app_name=config.get("app_name", "MyApplication"),
            icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
            console=config.get("console", True),
            one_file=config.get("one_file", True)
        )

        if not exe_path:
            log.error("Abbruch: Build fehlgeschlagen.")
            return

        # 4. Sign
        log.info("Starte Signierung...")
        success = self.signer.sign_exe(exe_path, pfx_path, cert_pass)
        
        if success:
            log.success(f"Prozess abgeschlossen! Fertige Datei: {exe_path}")
            log.info("HINWEIS: Bitte 'builds/install_cert.bat' als Admin ausführen, um Trust herzustellen.")
        else:
            log.error("Signierung fehlgeschlagen (Datei ist unsigniert).")
