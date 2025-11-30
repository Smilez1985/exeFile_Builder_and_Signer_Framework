import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

# 3rd Party
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

# Custom Level für "SUCCESS" (zwischen INFO und WARNING)
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

class EnterpriseLogger:
    """
    Singleton Logger Klasse für Enterprise-Anforderungen.
    Features:
    - Log Rotation (verhindert riesige Logfiles)
    - Thread-Safe
    - Konsolen-Output mit Farben (wenn verfügbar)
    - UTF-8 File Encoding erzwingen
    """
    
    _instance: Optional['EnterpriseLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EnterpriseLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger("ExeFramework")
        self.logger.setLevel(logging.DEBUG)
        self._setup_handlers()
        self._initialized = True

    def _setup_handlers(self):
        # Formatierung: Zeitstempel, Level, Nachricht
        log_format = logging.Formatter(
            fmt='%(asctime)s - [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 1. Pfad sicherstellen
        log_dir = Path("logs")
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"KRITISCHER FEHLER: Konnte Log-Verzeichnis nicht erstellen: {e}")
            sys.exit(1)

        # 2. File Handler (Rotating)
        # Max 10 MB pro Datei, maximal 5 Backups behalten (.log.1, .log.2 etc.)
        file_handler = RotatingFileHandler(
            filename=log_dir / "framework.log",
            mode='a',
            maxBytes=10 * 1024 * 1024, # 10 MB
            backupCount=5,
            encoding='utf-8',
            delay=False
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(log_format)
        self.logger.addHandler(file_handler)

        # 3. Console Handler (Stream)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(log_format)
        self.logger.addHandler(console_handler)

    def _log_with_color(self, level_val: int, prefix: str, msg: str, color_code: str):
        """Interne Methode für gefärbte Ausgabe."""
        # File Log (immer neutral)
        self.logger.log(level_val, msg)
        
        # Console Log (bunt, wenn möglich) wird via StreamHandler automatisch gemacht, 
        # aber wir wollen hier visuelles Feedback direkt manipulieren für UX.
        # Da der StreamHandler schon loggt, nutzen wir print nur für "Hervorhebung" 
        # oder wir verlassen uns auf das Standard-Logging. 
        # Enterprise Standard: Verlasse dich auf den Logger, färbe nur den Prefix im Formatter.
        # Um die bestehende Optik zu wahren, nutzen wir direkten Print für UX, loggen aber im Hintergrund.
        
        # HACK: Um doppelte Logs in der Konsole zu vermeiden, nutzen wir print für Farbe
        # und logging nur fürs File. Aber sauberer ist es, dem StreamHandler einen ColorFormatter zu geben.
        # Wir bleiben bei der etablierten Methode des Frameworks, aber gekapselt.
        pass

    def info(self, msg: str):
        if HAS_COLOR:
            print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")
        else:
            print(f"[INFO] {msg}")
        self.logger.info(msg)

    def success(self, msg: str):
        if HAS_COLOR:
            print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")
        else:
            print(f"[SUCCESS] {msg}")
        self.logger.log(SUCCESS_LEVEL, msg)

    def warning(self, msg: str):
        if HAS_COLOR:
            print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {msg}")
        else:
            print(f"[WARNING] {msg}")
        self.logger.warning(msg)

    def error(self, msg: str):
        if HAS_COLOR:
            print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")
        else:
            print(f"[ERROR] {msg}")
        self.logger.error(msg)

    def debug(self, msg: str):
        # Debug nur ins File oder wenn Verbose an wäre (hier: File only standardmäßig)
        self.logger.debug(msg)

    def critical(self, msg: str):
        if HAS_COLOR:
            print(f"{Fore.RED}{Style.BRIGHT}[CRITICAL]{Style.RESET_ALL} {msg}")
        else:
            print(f"[CRITICAL] {msg}")
        self.logger.critical(msg)

# Globale Instanz
log = EnterpriseLogger()
