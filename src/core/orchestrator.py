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
        # Das lädt jetzt auch osslsigncode.exe
        self.env_manager.prepare_environment(project_root)

    def get_cert_path(self, config: dict) -> Path:
        mode = config.get("cert_mode", "auto")
        password = config.get("cert_password", "")
        
        if mode == "file":
            pfx_path = Path(config.get("pfx_path"))
            if not pfx_path.exists():
                raise FileNotFoundError(f"PFX nicht gefunden: {pfx_path}")
            return pfx_path
        else:
            name = config.get("cert_name", "MyCert")
            use_openssl = config.get("use_openssl", False)
            
            certs = self.cert_manager.list_certificates()
            for cert in certs:
                if cert.stem == name:
                    log.info(f"♻️ Nutze Cache Zertifikat: {cert.name}")
                    return cert
            
            log.info(f"✨ Erstelle neues Zertifikat: {name}")
            pfx, cer = self.cert_manager.create_certificate(name, password, use_openssl=use_openssl)
            self.cert_manager.create_install_script(Path("builds"), name, cer)
            return pfx

    def run_full_pipeline(self, config: dict):
        log.info("=== STARTING BUILD PIPELINE ===")

        script_path = Path(config.get("script_file"))
        if not script_path.exists():
            log.error(f"Script fehlt: {script_path}")
            return

        # 1. Tools laden (osslsigncode)
        self.setup_environment(Path("."))

        # 2. Zertifikat
        try:
            pfx_path = self.get_cert_path(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Zertifikats-Fehler: {e}")
            return

        # 3. Assets
        raw_assets = config.get("assets", [])
        formatted_assets = []
        for asset in raw_assets:
            path_obj = Path(asset)
            if not path_obj.exists(): continue
            
            if path_obj.is_file():
                formatted_assets.append(f"{asset};.")
            elif path_obj.is_dir():
                formatted_assets.append(f"{asset};{path_obj.name}")

        # 4. Build
        exe_path = self.builder.build(
            script_path=script_path,
            app_name=config.get("app_name", "MyApp"),
            icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
            console=config.get("console", True),
            one_file=config.get("one_file", True),
            add_data=formatted_assets
        )

        if not exe_path: return

        # 5. Sign (Binary Mode)
        log.info("--- Signierung ---")
        success = self.signer.sign_exe(exe_path, pfx_path, cert_pass)
        
        if success:
            log.success("✅ DONE!")
            print(f"\n[OUTPUT]")
            print(f" EXE: {exe_path.absolute()}")
            print(f" PFX: {pfx_path.absolute()}")
        else:
            log.error("❌ Signatur fehlgeschlagen.")
