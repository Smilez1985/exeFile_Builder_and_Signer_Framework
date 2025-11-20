import shutil
from pathlib import Path
import sys

# Importiere Module
from src.core.environment import EnvironmentManager
from src.core.certs import CertificateManager
from src.core.signer import AuthenticodeSigner
from src.core.builder import PyBuilder
from src.core.network import NetworkGuard
from src.utils.helpers import log

class BuildOrchestrator:
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        self.cert_manager = CertificateManager(cert_store_path=Path("certs_store"))
        self.signer = AuthenticodeSigner()
        self.builder = PyBuilder()
        self.network = NetworkGuard()
        
    def setup_environment(self, project_root: Path):
        self.env_manager.prepare_environment(project_root)

    def get_cert_tuple(self, config: dict) -> tuple[Path, Path]:
        """
        Gibt PFX (Privat) UND CER (Öffentlich) zurück.
        """
        mode = config.get("cert_mode", "auto")
        password = config.get("cert_password", "")
        
        if mode == "file":
            pfx_path = Path(config.get("pfx_path"))
            if not pfx_path.exists():
                raise FileNotFoundError(f"PFX nicht gefunden: {pfx_path}")
            
            cer_path = pfx_path.with_suffix(".cer")
            if not cer_path.exists():
                log.warning("Bei externer PFX wurde keine .cer Datei gefunden. Auto-Install Script wird evtl. nicht funktionieren.")
                return pfx_path, None
                
            return pfx_path, cer_path
        else:
            name = config.get("cert_name", "MyCert")
            use_openssl = config.get("use_openssl", False)
            
            # 1. Suche im Store
            pfx_path = self.cert_manager.store_path / f"{name}.pfx"
            cer_path = self.cert_manager.store_path / f"{name}.cer"

            if pfx_path.exists() and cer_path.exists():
                log.info(f"♻️ Nutze Cache Zertifikat: {name}")
                return pfx_path, cer_path
            
            log.info(f"✨ Erstelle neues Zertifikat: {name}")
            return self.cert_manager.create_certificate(name, password, use_openssl=use_openssl)

    def create_readme(self, output_dir: Path):
        """Erstellt eine DAU-freundliche Anleitung für den Empfänger."""
        readme_path = output_dir / "ANLEITUNG_LESEN.txt"
        content = """========================================================================
             WICHTIGE INSTALLATIONS-HINWEISE
========================================================================

Damit dieses Programm auf Ihrem Computer ohne Warnmeldungen läuft, 
muss einmalig das beiliegende Sicherheitszertifikat installiert werden.

SCHRITT 1: ZERTIFIKAT INSTALLIEREN
----------------------------------
1. Finden Sie in diesem Ordner die Datei "install_cert.bat".
2. Klicken Sie mit der RECHTEN Maustaste darauf.
3. Wählen Sie "Als Administrator ausführen".
4. Bestätigen Sie eventuelle Fenster mit "Ja" oder "OK".

-> Es erscheint kurz ein schwarzes Fenster, das den Erfolg bestätigt.


SCHRITT 2: PROGRAMM STARTEN
---------------------------
Jetzt können Sie das Programm (die .exe Datei mit dem Icon) 
ganz normal mit einem Doppelklick starten.

Viel Spaß!
"""
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(content)
            log.info(f"   -> Anleitung erstellt: {readme_path.name}")
        except Exception as e:
            log.warning(f"Konnte Anleitung nicht erstellen: {e}")

    def run_full_pipeline(self, config: dict):
        log.info("=== STARTING BUILD PIPELINE ===")

        script_path = Path(config.get("script_file"))
        if not script_path.exists():
            log.error(f"Script fehlt: {script_path}")
            return

        self.setup_environment(Path("."))

        # 1. Zertifikat
        try:
            pfx_path, cer_path = self.get_cert_tuple(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Zertifikats-Fehler: {e}")
            return

        # 2. Assets
        raw_assets = config.get("assets", [])
        formatted_assets = []
        for asset in raw_assets:
            path_obj = Path(asset)
            if not path_obj.exists(): continue
            
            if path_obj.is_file():
                formatted_assets.append(f"{asset};.")
            elif path_obj.is_dir():
                formatted_assets.append(f"{asset};{path_obj.name}")

        # 3. Build
        exe_path = self.builder.build(
            script_path=script_path,
            app_name=config.get("app_name", "MyApp"),
            icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
            console=config.get("console", True),
            one_file=config.get("one_file", True),
            add_data=formatted_assets
        )

        if not exe_path:
            return

        # 4. Sign
        log.info("--- Signierung ---")
        success = self.signer.sign_exe(exe_path, pfx_path, cert_pass)
        
        if success:
            # --- DISTRIBUTION ---
            dist_dir = exe_path.parent
            
            log.info("📦 Erstelle Distributions-Paket...")
            
            # A) CER kopieren
            final_cer_path = None
            if cer_path and cer_path.exists():
                try:
                    final_cer_path = dist_dir / cer_path.name
                    shutil.copy(cer_path, final_cer_path)
                    log.info(f"   -> Public Key kopiert: {final_cer_path.name}")
                except Exception as e:
                    log.warning(f"Konnte CER nicht kopieren: {e}")

            # B) Install-Script erstellen
            if final_cer_path:
                self.cert_manager.create_install_script(dist_dir, pfx_path.stem, final_cer_path)
                log.info(f"   -> Installer Script erstellt in: {dist_dir}")
            
            # C) Anleitung erstellen (NEU)
            self.create_readme(dist_dir)

            log.success("✅ DONE!")
            print(f"\n[DISTRIBUTION - DIESEN ORDNER WEITERGEBEN]")
            print(f" 📂 {dist_dir.absolute()}")
            print(f"     ├── {exe_path.name}")
            if final_cer_path:
                print(f"     ├── {final_cer_path.name}")
                print(f"     ├── install_cert.bat")
                print(f"     └── ANLEITUNG_LESEN.txt")
        else:
            log.error("❌ Signatur fehlgeschlagen.")
