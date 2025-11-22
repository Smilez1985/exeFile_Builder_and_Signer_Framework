import shutil
import time
from pathlib import Path
import sys

# Module
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
        mode = config.get("cert_mode", "auto")
        password = config.get("cert_password", "")
        
        if mode == "file":
            pfx = Path(config.get("pfx_path"))
            if not pfx.exists(): raise FileNotFoundError("PFX fehlt")
            cer = pfx.with_suffix(".cer")
            return pfx, (cer if cer.exists() else None)
        else:
            name = config.get("cert_name", "MyCert")
            # Prüfen ob schon da
            pfx = self.cert_manager.store_path / f"{name}.pfx"
            cer = self.cert_manager.store_path / f"{name}.cer"
            if pfx.exists():
                log.info(f"♻️ Zertifikat aus Cache: {name}")
                return pfx, cer
            
            log.info(f"✨ Erstelle Zertifikat: {name}")
            return self.cert_manager.create_certificate(name, password, use_openssl=config.get("use_openssl", False))

    def create_readme(self, output_dir: Path):
        try:
            with open(output_dir / "README.txt", "w", encoding="utf-8") as f:
                f.write("Bitte install_cert.bat als Administrator ausführen!\nDann Programm starten.")
        except: pass

    def run_full_pipeline(self, config: dict):
        log.info("=== START PIPELINE ===")
        
        # 1. Checks
        script = Path(config.get("script_file"))
        if not script.exists():
            log.error("Script nicht gefunden")
            return
            
        self.setup_environment(Path("."))

        # 2. Zertifikat
        try:
            pfx_path, cer_path = self.get_cert_tuple(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Cert Fehler: {e}")
            return

        # 3. Assets vorbereiten (GUI -> Builder Format)
        assets = []
        for item in config.get("assets", []):
            p = Path(item)
            if p.is_file(): assets.append(f"{item};.")
            elif p.is_dir(): assets.append(f"{item};{p.name}")

        # 4. BUILD (Hier passiert die Magie mit den hardcoded Imports)
        exe_path = self.builder.build(
            script_path=script,
            app_name=config.get("app_name", "App"),
            icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
            console=config.get("console", True),
            one_file=config.get("one_file", True),
            add_data=assets
        )

        if not exe_path: return

        # 5. SIGN
        log.info("Warte kurz auf Dateisystem...")
        time.sleep(2)
        
        if self.signer.sign_exe(exe_path, pfx_path, cert_pass):
            dist = exe_path.parent
            if cer_path:
                try: shutil.copy(cer_path, dist / cer_path.name)
                except: pass
                self.cert_manager.create_install_script(dist, pfx_path.stem, cer_path)
            self.create_readme(dist)
            
            log.success("✅ DONE! Fertiges Paket in:")
            print(f" -> {dist.absolute()}")
        else:
            log.error("Signatur fehlgeschlagen.")
