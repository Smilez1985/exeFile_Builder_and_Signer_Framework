import logging
import sys
from pathlib import Path
from colorama import init, Fore, Style

# Initialisiere Colorama
init(autoreset=True)

class FrameworkLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FrameworkLogger, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self.logger = logging.getLogger("ExeBuilderFramework")
        self.logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')

        # Console Output
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        
        # File Output
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / "framework.log", encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def info(self, msg):
        print(f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {msg}")
        self.logger.info(msg)

    def success(self, msg):
        print(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {msg}")
        self.logger.info(f"SUCCESS: {msg}")

    def warning(self, msg):
        print(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {msg}")
        self.logger.warning(msg)

    def error(self, msg):
        print(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {msg}")
        self.logger.error(msg)

    def debug(self, msg):
        self.logger.debug(msg)

log = FrameworkLogger()
