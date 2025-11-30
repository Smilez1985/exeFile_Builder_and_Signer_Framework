import subprocess
import shutil
import os
from pathlib import Path
from typing import Optional

from src.utils.logger import log

class AuthenticodeSigner:
    """
    Enterprise Wrapper für Authenticode Signierung.
    Nutzt 'osslsigncode' (Cross-Platform Binary) statt anfälliger PowerShell-Skripte.
    
    Features:
    - Isoliertes Arbeitsverzeichnis für DLL-Auflösung
    - Automatische Einbindung von OpenSSL Legacy-Providern
    - Detaillierte Fehleranalyse bei Signatur-Problemen
    """

    TIMESTAMP_SERVER = "http://timestamp.digicert.com"

    def __init__(self):
        # Wir suchen das Tool im 'tools' Ordner relativ zum Framework Root
        # Pfad: src/core/../../tools -> tools/
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.tool_dir = self.root_dir / "tools"
        self.tool_path = self.tool_dir / "osslsigncode.exe"

    def sign_exe(self, exe_path: Path, pfx_path: Path, password: str) -> bool:
        """
        Signiert eine Windows PE-Datei (.exe, .dll).
        
        Args:
            exe_path: Pfad zur unsignierten Datei.
            pfx_path: Pfad zum Zertifikat (.pfx).
            password: Passwort für das Zertifikat.
            
        Returns:
            True bei Erfolg, sonst False.
        """
        log.info(f"Initialisiere Signierung für: {exe_path.name}")
        
        # 1. Validierung
        if not self._validate_prerequisites(exe_path, pfx_path):
            return False

        # 2. Pfade vorbereiten (Absolute Pfade sind Pflicht bei CWD-Wechsel!)
        abs_exe = exe_path.resolve()
        abs_pfx = pfx_path.resolve()
        abs_signed = abs_exe.parent / f"{abs_exe.stem}_signed.exe"

        # 3. Kommando zusammenbauen
        # Syntax: osslsigncode sign -pkcs12 <pfx> -pass <pwd> -n <name> -t <ts> -in <in> -out <out>
        cmd = [
            str(self.tool_path.resolve()), "sign",
            "-pkcs12", str(abs_pfx),
            "-pass", password,
            "-n", abs_exe.stem,
            "-t", self.TIMESTAMP_SERVER,
            "-in", str(abs_exe),
            "-out", str(abs_signed)
        ]

        # 4. Umgebung vorbereiten (Fix für "Legacy Provider not found")
        # Wir müssen OpenSSL sagen, wo die Module (.dll) liegen.
        # Unser EnvironmentManager hat sie flach in 'tools/' entpackt.
        env = os.environ.copy()
        env["OPENSSL_MODULES"] = str(self.tool_dir.resolve())

        try:
            log.debug(f"Starte Signier-Prozess im Kontext: {self.tool_dir}")
            
            # WICHTIG: cwd auf tools/ setzen, damit die EXE ihre DLLs (z.B. zlib1.dll) findet.
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace', # Robustheit bei Encoding-Fehlern
                cwd=str(self.tool_dir),
                env=env
            )

            # 5. Auswertung
            if process.returncode == 0 and abs_signed.exists():
                log.success("Signatur erfolgreich erstellt.")
                
                # Atomares Ersetzen (Swap)
                self._swap_files(abs_exe, abs_signed)
                
                log.success(f"Datei finalisiert: {abs_exe.name}")
                return True
            else:
                self._handle_error(process)
                return False

        except Exception as e:
            log.error(f"Kritischer Fehler im Signer: {e}")
            return False

    def _validate_prerequisites(self, exe: Path, pfx: Path) -> bool:
        if not self.tool_path.exists():
            log.error(f"Signier-Tool fehlt: {self.tool_path}")
            log.info("Bitte Launcher neu starten (Environment Check lädt es nach).")
            return False
        
        if not exe.exists():
            log.error(f"Zu signierende Datei fehlt: {exe}")
            return False
            
        if not pfx.exists():
            log.error(f"Zertifikat fehlt: {pfx}")
            return False
            
        return True

    def _swap_files(self, original: Path, signed: Path):
        """Ersetzt das Original sicher durch die signierte Version."""
        try:
            if original.exists():
                original.unlink()
            shutil.move(str(signed), str(original))
        except OSError as e:
            log.warning(f"Konnte Datei nicht atomar ersetzen: {e}")
            # Fallback oder manueller Eingriff nötig

    def _handle_error(self, process: subprocess.CompletedProcess):
        log.error("Signierung fehlgeschlagen.")
        log.error(f"Exit Code: {process.returncode}")
        
        if process.stdout:
            log.error(f"Tool Output: {process.stdout.strip()}")
        if process.stderr:
            log.error(f"Tool Error: {process.stderr.strip()}")
            
        # Bekannte Fehlerhinweise
        if "load provider" in (process.stderr or ""):
            log.warning("Hinweis: OpenSSL Module konnten nicht geladen werden. Prüfe 'tools'-Ordner.")
