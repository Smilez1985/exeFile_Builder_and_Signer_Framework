import shutil
import time
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple, Optional

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
        # (Zertifikatslogik unverändert)
        mode = config.get("cert_mode", "auto")
        password = config.get("cert_password", "")
        
        if mode == "file":
            pfx = Path(config.get("pfx_path"))
            if not pfx.exists(): raise FileNotFoundError("PFX fehlt")
            cer = pfx.with_suffix(".cer")
            return pfx, (cer if cer.exists() else None)
        else:
            name = config.get("cert_name", "MyCert")
            pfx = self.cert_manager.store_path / f"{name}.pfx"
            cer = self.cert_manager.store_path / f"{name}.cer"
            if pfx.exists():
                log.info(f"♻️ Zertifikat aus Cache: {name}")
                return pfx, cer
            log.info(f"✨ Erstelle Zertifikat: {name}")
            return self.cert_manager.create_certificate(name, password, use_openssl=config.get("use_openssl", False))

    def create_readme(self, output_dir: Path):
        try:
            with open(output_dir / "ANLEITUNG_LESEN.txt", "w", encoding="utf-8") as f:
                f.write("Bitte install_cert.bat als Administrator ausführen!\nDann Programm starten.")
        except: pass

    def detect_config_from_assets(self, assets: List[str]) -> Tuple[List[str], Path, str]:
        """
        Sucht in den vom User bereitgestellten Assets nach einer Config-Datei.
        Rückgabe: (Argumente, ProjectRoot, ConfigFilePath)
        """
        for asset_path in assets:
            path_obj = Path(asset_path)
            
            # Wir suchen nur nach .py Dateien in der Asset-Liste
            if not path_obj.exists() or path_obj.suffix.lower() != ".py":
                continue
            
            try:
                # Schnell-Check: Enthält die Datei unser Keyword?
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    if "PYINSTALLER_CMD_ARGS" not in f.read():
                        continue
                
                log.info(f"🔧 Build-Config in Assets erkannt: {path_obj.name}")
                
                # Importieren
                spec = importlib.util.spec_from_file_location("asset_config", str(path_obj))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                if hasattr(mod, "PYINSTALLER_CMD_ARGS"):
                    args = getattr(mod, "PYINSTALLER_CMD_ARGS")
                    
                    # Root ermitteln: Wenn die Datei in 'scripts' liegt, ist Root eins drüber.
                    # Sonst ist Root der Ordner der Datei.
                    project_root = path_obj.parent
                    if project_root.name in ["scripts", "config"]:
                        project_root = project_root.parent
                        
                    log.success(f"✅ Konfiguration geladen! Root: {project_root}")
                    return args, project_root, str(path_obj)
                    
            except Exception as e:
                log.warning(f"Konnte Asset {path_obj.name} nicht als Config laden: {e}")
                continue
        
        return [], None, None

    def run_full_pipeline(self, config: dict):
        log.info("=== START PIPELINE ===")
        
        script_input = Path(config.get("script_file"))
        if not script_input.exists():
            log.error("Script nicht gefunden")
            return

        self.setup_environment(Path("."))

        try:
            pfx_path, cer_path = self.get_cert_tuple(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Cert Fehler: {e}")
            return

        # --- LOGIK: CONFIG vs GUI ---
        # Wir schauen in die Assets, die der User in die GUI gezogen hat
        gui_assets = config.get("assets", [])
        
        config_args, project_root, config_file = self.detect_config_from_assets(gui_assets)
        
        exe_path = None
        
        if config_args:
            # MODUS A: Config (Goldstandard)
            log.info("Starte Build mit externer Konfiguration...")
            
            # Falls der User NOCH MEHR Assets in der GUI hat (außer der Config), 
            # fügen wir diese sicherheitshalber auch hinzu.
            extra_assets = []
            for item in gui_assets:
                if item == config_file: continue # Config selbst nicht packen
                
                p = Path(item)
                if p.is_file(): extra_assets.append(f"--add-data={item};.")
                elif p.is_dir(): extra_assets.append(f"--add-data={item};{p.name}")
            
            if extra_assets:
                log.info(f"Füge {len(extra_assets)} weitere Assets aus der GUI hinzu.")
                config_args.extend(extra_assets)

            # WICHTIG: Wir nutzen 'build_with_args' (aus dem vorherigen Update)
            exe_path = self.builder.build_with_args(config_args, project_root)
            
        else:
            # MODUS B: Standard GUI
            log.info("Keine Config-Datei in den Assets gefunden. Nutze Standard-Modus.")
            
            clean_assets = []
            for item in gui_assets:
                p = Path(item)
                if p.is_file(): clean_assets.append(f"{item};.")
                elif p.is_dir(): clean_assets.append(f"{item};{p.name}")

            exe_path = self.builder.build_from_gui(
                script_path=script_input,
                app_name=config.get("app_name", "MyApp"),
                icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
                console=config.get("console", True),
                one_file=config.get("one_file", True),
                add_data=clean_assets
            )

        if not exe_path: return

        # SIGNIERUNG
        log.info("Warte auf Dateisystem...")
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
