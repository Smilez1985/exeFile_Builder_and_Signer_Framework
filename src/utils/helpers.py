import logging
import sys
from pathlib import Path
from colorama import init, Fore, Style

# Initialisiere Colorama für Windows CMD Support
init(autoreset=True)

class Logger:
    """Zentraler Logger, der sowohl in die Konsole (bunt) als auch in Dateien schreibt."""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self.logger = logging.getLogger("PySignBuilder")
        self.logger.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Console Handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        # Wir färben die Ausgabe im Code direkt, daher hier einfacher Formatter
        ch.setFormatter(formatter)
        
        # File Handler
        log_dir = Path("logs")
        if not log_dir.exists():
            log_dir.mkdir(exist_ok=True)
            
        fh = logging.FileHandler(log_dir / "build.log", encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def info(self, msg):
        print(f"{Fore.CYAN}[INFO] {Style.RESET_ALL}{msg}")
        self.logger.info(msg)

    def success(self, msg):
        print(f"{Fore.GREEN}[SUCCESS] {Style.RESET_ALL}{msg}")
        self.logger.info(f"SUCCESS: {msg}")

    def warning(self, msg):
        print(f"{Fore.YELLOW}[WARN] {Style.RESET_ALL}{msg}")
        self.logger.warning(msg)

    def error(self, msg):
        print(f"{Fore.RED}[ERROR] {Style.RESET_ALL}{msg}")
        self.logger.error(msg)
        
    def debug(self, msg):
        self.logger.debug(msg)

# Singleton Instanz
log = Logger()

def ensure_dir(path: Path):
    """Stellt sicher, dass ein Verzeichnis existiert."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
