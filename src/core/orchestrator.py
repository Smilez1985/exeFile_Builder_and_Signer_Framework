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
            # Bei externer PFX müssen wir schauen, ob wir den Public Key extrahieren können
            # oder ob der User ihn bereitstellt.
            # Vereinfachung: Wir nehmen an, pfx ist da. CER Generierung wäre hier komplexer ohne OpenSSL.
            # Fallback: Wir geben nur PFX zurück, User muss CER selbst haben.
            pfx_path = Path(config.get("pfx_path"))
            if not pfx_path.exists():
                raise FileNotFoundError(f"PFX nicht gefunden: {pfx_path}")
            
            # Wir versuchen, eine .cer neben der .pfx zu finden
            cer_path = pfx_path.with_suffix(".cer")
            if not cer_path.exists():
                # Wenn keine CER da ist, erstellen wir keine Install-Bat (oder warnen)
                log.warning("Bei externer PFX wurde keine .cer Datei gefunden. Auto-Install Script wird evtl. nicht funktionieren.")
                return pfx_path, None
                
            return pfx_path, cer_path
        else:
            name = config.get("cert_name", "MyCert")
            use_openssl = config.get("use_openssl", False)
            
            # 1. Suche im Store
            # Wir müssen checken, ob PFX UND CER da sind
            pfx_path = self.cert_manager.store_path / f"{name}.pfx"
            cer_path = self.cert_manager.store_path / f"{name}.cer" # Windows macht oft .cer

            if pfx_path.exists() and cer_path.exists():
                log.info(f"♻️ Nutze Cache Zertifikat: {name}")
                return pfx_path, cer_path
            
            log.info(f"✨ Erstelle neues Zertifikat: {name}")
            # Create liefert (pfx, cer) zurück
            return self.cert_manager.create_certificate(name, password, use_openssl=use_openssl)

    def run_full_pipeline(self, config: dict):
        log.info("=== STARTING BUILD PIPELINE ===")

        script_path = Path(config.get("script_file"))
        if not script_path.exists():
            log.error(f"Script fehlt: {script_path}")
            return

        self.setup_environment(Path("."))

        # 1. Zertifikat holen (PFX + CER)
        try:
            pfx_path, cer_path = self.get_cert_tuple(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Zertifikats-Fehler: {e}")
            return

        # 2. Assets vorbereiten
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
            # --- FINALISIERUNG: Das Distributions-Paket schnüren ---
            dist_dir = exe_path.parent # Das ist builds/dist/
            
            log.info("📦 Erstelle Distributions-Paket...")
            
            # A) CER Datei kopieren (damit der Kunde sie hat)
            final_cer_path = None
            if cer_path and cer_path.exists():
                try:
                    final_cer_path = dist_dir / cer_path.name
                    shutil.copy(cer_path, final_cer_path)
                    log.info(f"   -> Public Key kopiert: {final_cer_path.name}")
                except Exception as e:
                    log.warning(f"Konnte CER nicht kopieren: {e}")

            # B) Install-Script direkt beim Endprodukt erstellen
            if final_cer_path:
                self.cert_manager.create_install_script(dist_dir, pfx_path.stem, final_cer_path)
                log.info(f"   -> Installer Script erstellt in: {dist_dir}")

            log.success("✅ DONE!")
            print(f"\n[DISTRIBUTION - DIESEN ORDNER WEITERGEBEN]")
            print(f" 📂 {dist_dir.absolute()}")
            print(f"     ├── {exe_path.name} (Deine App)")
            if final_cer_path:
                print(f"     ├── {final_cer_path.name} (Schlüssel)")
                print(f"     └── install_cert.bat (Für den Kunden)")
        else:
            log.error("❌ Signatur fehlgeschlagen.")
