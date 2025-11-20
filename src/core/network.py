import time
import socket
import subprocess
import sys
from src.utils.helpers import log

class NetworkGuard:
    """
    Stellt sicher, dass eine Netzwerkverbindung besteht, bevor Aktionen ausgeführt werden.
    Implementiert einen 'Pause & Resume' Mechanismus.
    """

    def __init__(self, target="8.8.8.8", port=53, timeout=3):
        self.target = target
        self.port = port
        self.timeout = timeout

    def check_connection(self) -> bool:
        """Prüft die Verbindung via Socket Connect (schneller als ICMP Ping)."""
        try:
            # Wir nutzen DNS Port 53, da ICMP oft blockiert ist
            socket.setdefaulttimeout(self.timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((self.target, self.port))
            return True
        except socket.error:
            return False

    def wait_for_network(self):
        """
        Blockiert die Ausführung solange, bis das Netzwerk verfügbar ist.
        Zeigt einen Status an.
        """
        if self.check_connection():
            return

        log.warning("Netzwerkverbindung verloren! Warte auf Wiederherstellung...")
        
        start_time = time.time()
        while not self.check_connection():
            elapsed = int(time.time() - start_time)
            sys.stdout.write(f"\rWarte auf Netzwerk... ({elapsed}s)")
            sys.stdout.flush()
            time.sleep(2) # Prüfe alle 2 Sekunden
        
        print() # Newline nach dem Counter
        log.success("Netzwerkverbindung wiederhergestellt. Setze fort.")

    def run_with_retry(self, func, *args, **kwargs):
        """
        Wrapper, um eine Funktion auszuführen. Wenn sie wegen Netzwerk failt, 
        wird gewartet und neu versucht.
        """
        max_retries = 5
        attempt = 0
        
        while attempt < max_retries:
            self.wait_for_network()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Einfache Heuristik: Wenn es ein Netzwerkfehler zu sein scheint
                if "Connection" in str(e) or "Network" in str(e) or "Timeout" in str(e):
                    attempt += 1
                    log.warning(f"Fehler bei Ausführung (Versuch {attempt}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    raise e
        raise ConnectionError("Maximale Anzahl an Wiederholungen überschritten.")
