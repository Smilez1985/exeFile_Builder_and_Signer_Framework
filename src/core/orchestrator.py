from pathlib import Path
import sys

# Importiere Module - Pfade basierend auf der Repo-Struktur
from core.environment import EnvironmentManager
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
        """Installiert Dependencies."""
        self.env_manager.prepare_environment(project_root)

    def create_or_get_cert(self, cert_name: str, password: str) -> Path:
        """
        Sucht nach einem existierenden PFX Zertifikat oder erstellt ein neues.
        Gibt den Pfad zur PFX zurück.
        """
        # Suche im Store
        certs = self.cert_manager.list_certificates()
        for cert in certs:
            if cert.stem == cert_name:
                log.info(f"Vorhandenes Zertifikat gefunden: {cert.name}")
                return cert
        
        # Erstelle neu
        log.info(f"Kein Zertifikat für '{cert_name}' gefunden. Erstelle neu...")
        pfx, cer = self.cert_manager.create_certificate(cert_name, password)
        
        # Erstelle Install-Script für den Nutzer
        self.cert_manager.create_install_script(Path("builds"), cert_name, cer)
        
        return pfx

    def run_full_pipeline(self, config: dict):
        """
        Führt die komplette Pipeline basierend auf der Konfiguration aus.
        config dict erwartet: script_file, app_name, cert_name, cert_pass, etc.
        """
        script_path = Path(config.get("script_file"))
        if not script_path.exists():
            log.error(f"Eingabedatei nicht gefunden: {script_path}")
            return

        # 1. Netzwerk Check (optional, falls Dependencies geladen werden müssen)
        if not self.network.check_connection():
            log.warning("Keine Internetverbindung. Überspringe Online-Checks.")
        
        # 2. Environment
        self.setup_environment(Path("."))

        # 3. Zertifikat vorbereiten
        cert_pass = config.get("cert_password", "SecretPass123!")
        cert_name = config.get("cert_name", "MySelfSignedCert")
        
        try:
            pfx_path = self.create_or_get_cert(cert_name, cert_pass)
        except Exception as e:
            log.error(f"Zertifikatsfehler: {e}")
            return

        # 4. Build
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

        # 5. Sign
        log.info("Starte Signierung...")
        success = self.signer.sign_exe(exe_path, pfx_path, cert_pass)
        
        if success:
            log.success(f"Prozess abgeschlossen! Fertige Datei: {exe_path}")
            log.info("HINWEIS: Damit die Datei ohne Warnung läuft, muss das Zertifikat (siehe 'builds/install_cert.bat') einmalig installiert werden.")
        else:
            log.error("Signierung fehlgeschlagen, aber die EXE wurde erstellt (unsigniert).")
