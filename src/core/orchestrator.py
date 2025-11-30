import shutil
import time
import importlib.util
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Any

# Framework Module
from src.core.environment import EnvironmentManager
from src.core.certs import CertificateManager
from src.core.signer import AuthenticodeSigner
from src.core.builder import PyBuilder
from src.utils.logger import log

class BuildOrchestrator:
    """
    Enterprise Orchestrator.
    
    Steuert den gesamten Build-Lebenszyklus:
    1. Environment Check (Tools & Deps)
    2. Zertifikats-Management (Erstellung/Laden)
    3. Build-Prozess (GUI-basiert oder Config-basiert)
    4. Signierung (Authenticode)
    5. Packaging (Distributions-Ordner mit Anleitung)
    """
    
    def __init__(self):
        self.env_manager = EnvironmentManager()
        # Pfad hartkodiert relativ zum Framework-Root, um Konsistenz zu sichern
        self.cert_manager = CertificateManager(cert_store_path=Path("certs_store"))
        self.signer = AuthenticodeSigner()
        self.builder = PyBuilder()
        
    def setup_environment(self, project_root: Path) -> bool:
        """Bereitet die Build-Umgebung vor."""
        return self.env_manager.prepare_environment(project_root)

    def get_cert_tuple(self, config: dict) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Ermittelt das zu verwendende Zertifikat (Private Key PFX + Public Key CER).
        """
        mode = config.get("cert_mode", "auto")
        password = config.get("cert_password", "")
        
        try:
            if mode == "file":
                pfx_path = Path(config.get("pfx_path", ""))
                if not pfx_path.exists():
                    log.error(f"PFX Datei nicht gefunden: {pfx_path}")
                    return None, None
                
                # Versuch, die .cer daneben zu finden (Best Effort)
                cer_path = pfx_path.with_suffix(".cer")
                if not cer_path.exists():
                    log.warning("Keine .cer Datei neben der PFX gefunden. Auto-Install Script wird eingeschränkt sein.")
                    return pfx_path, None
                    
                return pfx_path, cer_path
            else:
                # Auto-Mode: Cache oder Neu
                name = config.get("cert_name", "MySelfSignedCert")
                use_openssl = config.get("use_openssl", False)
                
                # Check Cache
                pfx = self.cert_manager.store_path / f"{name}.pfx"
                cer = self.cert_manager.store_path / f"{name}.cer"
                
                if pfx.exists() and cer.exists():
                    log.info(f"♻️ Zertifikat aus Cache verwenden: {name}")
                    return pfx, cer
                
                log.info(f"✨ Erstelle neues Zertifikat: {name}")
                return self.cert_manager.create_certificate(name, password, use_openssl=use_openssl)
                
        except Exception as e:
            log.error(f"Fehler im Zertifikats-Management: {e}")
            return None, None

    def create_distribution_package(self, exe_path: Path, pfx_name: str, cer_path: Optional[Path]):
        """
        Erstellt das finale Paket für den Endanwender.
        Enthält: Signierte EXE, Public Key, Install-Script, Anleitung.
        """
        dist_dir = exe_path.parent
        log.info("📦 Schnüre Distributions-Paket...")

        # 1. Public Key kopieren
        final_cer_path = None
        if cer_path and cer_path.exists():
            try:
                final_cer_path = dist_dir / cer_path.name
                shutil.copy(cer_path, final_cer_path)
                log.debug(f"Public Key kopiert: {final_cer_path.name}")
            except OSError as e:
                log.warning(f"Konnte CER nicht kopieren: {e}")

        # 2. Install-Script generieren
        if final_cer_path:
            self.cert_manager.create_install_script(dist_dir, pfx_name, final_cer_path)

        # 3. Readme erstellen
        self._write_readme(dist_dir)

        log.success("✅ BUILD & SIGN SUCCESSFUL!")
        log.info(f"Ausgabe-Verzeichnis: {dist_dir.absolute()}")
        print("\n[INHALT DES PAKETS]")
        print(f" - {exe_path.name} (Anwendung)")
        if final_cer_path:
            print(f" - {final_cer_path.name} (Zertifikat)")
            print(f" - install_cert.bat (Setup)")
            print(f" - ANLEITUNG_LESEN.txt")
        print("-" * 40)

    def _write_readme(self, output_dir: Path):
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
        except OSError:
            pass

    def detect_config_from_assets(self, assets: List[str]) -> Tuple[List[str], Path, Optional[str]]:
        """
        Analysiert Assets auf Python-Konfigurationsdateien (Goldstandard).
        Rückgabe: (Argumente, ProjectRoot, ConfigFilePath)
        """
        for asset_path in assets:
            path_obj = Path(asset_path)
            
            # Nur existierende .py Dateien prüfen
            if not path_obj.exists() or path_obj.suffix.lower() != ".py":
                continue
            
            try:
                # 1. Quick Scan (Textsuche) für Performance
                with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    if "PYINSTALLER_CMD_ARGS" not in f.read():
                        continue
                
                log.info(f"🔧 Build-Config erkannt: {path_obj.name}")
                
                # 2. Dynamischer Import
                spec = importlib.util.spec_from_file_location("dynamic_build_config", str(path_obj))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    
                    if hasattr(mod, "PYINSTALLER_CMD_ARGS"):
                        args = getattr(mod, "PYINSTALLER_CMD_ARGS")
                        
                        # Root-Erkennung: Wenn Datei in 'scripts'/'config', ist Root ../
                        project_root = path_obj.parent
                        if project_root.name.lower() in ["scripts", "config", "configs"]:
                            project_root = project_root.parent
                            
                        log.success(f"✅ Konfiguration geladen! Projekt-Root: {project_root}")
                        return args, project_root, str(path_obj)
                        
            except Exception as e:
                log.warning(f"Konnte Asset {path_obj.name} nicht verarbeiten: {e}")
                continue
        
        return [], Path("."), None

    def run_full_pipeline(self, config: dict):
        """Hauptmethode: Führt den kompletten Prozess aus."""
        log.info("=== START PIPELINE ===")
        
        # 1. Basis-Validierung
        script_input = Path(config.get("script_file", ""))
        if not script_input.exists():
            log.error("Haupt-Script nicht gefunden.")
            return

        # 2. Environment (Tools laden)
        if not self.setup_environment(Path(".")):
            log.error("Environment Setup fehlgeschlagen.")
            return

        # 3. Zertifikate
        pfx_path, cer_path = self.get_cert_tuple(config)
        if not pfx_path:
            return # Fehler wurde bereits geloggt
        
        cert_pass = config.get("cert_password", "")

        # 4. Build-Strategie wählen (Config vs. GUI)
        gui_assets = config.get("assets", [])
        config_args, project_root, config_file_path = self.detect_config_from_assets(gui_assets)
        
        exe_path = None
        
        if config_args:
            # --- STRATEGIE A: Goldstandard (Config) ---
            log.info("Starte Build mit externer Konfiguration...")
            
            # Alle Assets außer der Config selbst hinzufügen
            extra_assets = []
            for item in gui_assets:
                if item == config_file_path: continue
                
                p = Path(item)
                if p.is_file(): extra_assets.append(f"--add-data={item};.")
                elif p.is_dir(): extra_assets.append(f"--add-data={item};{p.name}")
            
            if extra_assets:
                log.info(f"Füge {len(extra_assets)} manuelle Assets hinzu.")
                config_args.extend(extra_assets)

            exe_path = self.builder.build_with_config(config_args, project_root)
            
        else:
            # --- STRATEGIE B: GUI Fallback ---
            log.info("Keine externe Config gefunden. Nutze Standard-GUI-Modus.")
            
            # Assets formatieren
            clean_assets = []
            for item in gui_assets:
                p = Path(item)
                if p.is_file(): clean_assets.append(f"--add-data={item};.")
                elif p.is_dir(): clean_assets.append(f"--add-data={item};{p.name}")

            exe_path = self.builder.build_from_gui(
                script_path=script_input,
                app_name=config.get("app_name", "MyApp"),
                icon_path=Path(config.get("icon_path")) if config.get("icon_path") else None,
                console=config.get("console", True),
                one_file=config.get("one_file", True),
                add_data=clean_assets
            )

        if not exe_path:
            return

        # 5. Signierung
        log.info("Initialisiere Signierung (Warte auf Dateisystem)...")
        time.sleep(2) # Anti-Virus/Lock-Schutz
        
        if self.signer.sign_exe(exe_path, pfx_path, cert_pass):
            # 6. Distribution erstellen
            self.create_distribution_package(
                exe_path=exe_path,
                pfx_name=pfx_path.stem,
                cer_path=cer_path
            )
        else:
            log.error("Signierung fehlgeschlagen. Build ist unvollständig.")
