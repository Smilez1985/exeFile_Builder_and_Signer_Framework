import shutil
import time
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple, Optional

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
        # (Logik für Zertifikate bleibt gleich)
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
            with open(output_dir / "README.txt", "w", encoding="utf-8") as f:
                f.write("Bitte install_cert.bat als Administrator ausführen!\nDann Programm starten.")
        except: pass

    def find_project_config(self, script_path: Path) -> Tuple[List[str], Path]:
        """
        Sucht intelligent nach einer Build-Config im Projektbaum des Users.
        Gibt (Argumenten-Liste, Projekt-Root-Pfad) zurück.
        """
        # Wir definieren Suchpfade relativ zum Script (z.B. orchestrator/main.py)
        # 1. Gleicher Ordner
        # 2. Ordner 'scripts' im Parent (../scripts)
        # 3. Ordner 'config' im Parent (../config)
        # 4. Parent Ordner selbst (../)
        
        candidates = [
            script_path.parent,
            script_path.parent.parent / "scripts",
            script_path.parent.parent / "config",
            script_path.parent.parent
        ]
        
        for folder in candidates:
            if not folder.exists(): continue
            
            # Wir suchen nach Python-Dateien, die PYINSTALLER_CMD_ARGS enthalten
            for py_file in folder.glob("*.py"):
                if py_file.resolve() == script_path.resolve(): continue # Sich selbst überspringen
                
                try:
                    # Quick-Scan des Inhalts (Performance)
                    with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    if "PYINSTALLER_CMD_ARGS" in content:
                        log.info(f"🔍 Konfiguration gefunden: {py_file.name}")
                        
                        # Dynamischer Import
                        spec = importlib.util.spec_from_file_location("ext_config", str(py_file))
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        
                        if hasattr(mod, "PYINSTALLER_CMD_ARGS"):
                            args = getattr(mod, "PYINSTALLER_CMD_ARGS")
                            log.success("✅ Argumente erfolgreich geladen!")
                            
                            # Project Root ermitteln:
                            # Wenn Config in /scripts/ liegt, ist Root vermutlich eins drüber.
                            # Wenn Config im Root liegt, ist es der Ordner selbst.
                            project_root = folder.parent if folder.name in ["scripts", "config", "orchestrator"] else folder
                            
                            return args, project_root
                            
                except Exception as e:
                    log.debug(f"Fehler beim Lesen von {py_file}: {e}")
                    continue
        
        return [], None

    def run_full_pipeline(self, config: dict):
        log.info("=== START PIPELINE ===")
        
        script_input = Path(config.get("script_file"))
        if not script_input.exists():
            log.error("Script nicht gefunden")
            return

        # Environment Check (lädt Tools etc.)
        self.setup_environment(Path("."))

        # Zertifikat
        try:
            pfx_path, cer_path = self.get_cert_tuple(config)
            cert_pass = config.get("cert_password", "")
        except Exception as e:
            log.error(f"Zertifikats-Fehler: {e}")
            return

        # --- AUTO-DETECTION START ---
        # Wir suchen nach der Config
        config_args, project_root = self.find_project_config(script_input)
        
        exe_path = None
        
        if config_args:
            # MODUS A: Config gefunden -> Nutze Goldstandard
            log.info(f"Nutze externe Config. Root: {project_root}")
            exe_path = self.builder.build_with_config(config_args, project_root)
        else:
            # MODUS B: Keine Config -> Nutze GUI Eingaben
            log.info("Keine Projekt-Config gefunden. Nutze GUI-Settings.")
            
            gui_assets = []
            for item in config.get("assets", []):
                p = Path(item)
                if p.is_file(): gui_assets.append(f"{item};.")
                elif p.is_dir(): gui_assets.append(f"{item};{p.name}")

            exe_path = self.builder.build_from_gui(
                script_path=script_input,
                app_name=config.get("app_name", "MyApp"),
                icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
                console=config.get("console", True),
                one_file=config.get("one_file", True),
                add_data=gui_assets
            )

        if not exe_path: return

        # SIGNIERUNG (Unverändert)
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
