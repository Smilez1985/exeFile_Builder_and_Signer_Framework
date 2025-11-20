import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import threading
from pathlib import Path

# Framework Imports
from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

# Optionaler DND Import für Type-Hinting (Laufzeit-Check passiert in main_gui.py)
try:
    from tkinterdnd2 import DND_FILES
except ImportError:
    pass

class ConsoleRedirector:
    """Leitet Stdout/Stderr in das Text-Widget der GUI um."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str_val):
        try:
            self.text_widget.configure(state='normal')
            self.text_widget.insert('end', str_val)
            self.text_widget.see('end')
            self.text_widget.configure(state='disabled')
        except:
            pass
        # Auch in die echte Konsole schreiben
        sys.__stdout__.write(str_val)

    def flush(self):
        sys.__stdout__.flush()

class AppGUI:
    def __init__(self, root, dnd_enabled=False):
        self.root = root
        self.dnd_enabled = dnd_enabled
        self.root.title("ExeFile Builder & Signer Framework")
        self.root.geometry("950x750")
        self.root.configure(bg="#2b2b2b")

        self.orchestrator = BuildOrchestrator()

        self._setup_styles()
        self._create_widgets()
        
        if self.dnd_enabled:
            self._setup_dnd()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Farben & Fonts
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        entry_bg = "#3c3c3c"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TButton", background=accent_color, foreground=fg_color, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[('active', '#005f9e')])
        
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', bg_color)], indicatorcolor=[('selected', accent_color)])
        
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#555555")
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Segoe UI", 9, "bold"))

    def _create_widgets(self):
        # --- Hauptcontainer ---
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Banner
        lbl_banner = ttk.Label(main_frame, text="EXE BUILDER FRAMEWORK", font=("Segoe UI", 18, "bold"), foreground="#007acc")
        lbl_banner.pack(pady=(0, 20))

        # --- Sektion 1: Datei Auswahl ---
        file_frame = ttk.LabelFrame(main_frame, text=" 1. Quellcode & Assets (Drag & Drop möglich) ", padding=15)
        file_frame.pack(fill='x', pady=(0, 15))

        self._create_file_entry(file_frame, "Python Script (.py):", "script_path", 0, "*.py")
        self._create_file_entry(file_frame, "Icon Datei (.ico):", "icon_path", 1, "*.ico")
        
        # --- Sektion 2: Konfiguration ---
        config_frame = ttk.LabelFrame(main_frame, text=" 2. Build Einstellungen ", padding=15)
        config_frame.pack(fill='x', pady=(0, 15))

        # Zeile 1
        ttk.Label(config_frame, text="App Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_app_name = ttk.Entry(config_frame, width=30)
        self.entry_app_name.insert(0, "MyApplication")
        self.entry_app_name.grid(row=0, column=1, sticky='w', padx=10, pady=5)

        # Zeile 2 - Checkboxen
        self.var_onefile = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="OneFile (Einzelne .exe)", variable=self.var_onefile).grid(row=0, column=2, padx=20)

        self.var_console = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Konsole anzeigen (Debug)", variable=self.var_console).grid(row=0, column=3, padx=20)
        
        # Zeile 3 - OpenSSL Switch
        self.var_openssl = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="Benutze OpenSSL Engine (statt PowerShell)", variable=self.var_openssl).grid(row=1, column=0, columnspan=3, sticky='w', pady=(10,0))

        # --- Sektion 3: Zertifikat ---
        cert_frame = ttk.LabelFrame(main_frame, text=" 3. Code Signing ", padding=15)
        cert_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(cert_frame, text="Zertifikat Name (CN):").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_cert_name = ttk.Entry(cert_frame, width=30)
        self.entry_cert_name.insert(0, "SelfSignedCert")
        self.entry_cert_name.grid(row=0, column=1, sticky='w', padx=10)

        ttk.Label(cert_frame, text="Passwort:").grid(row=1, column=0, sticky='w', pady=5)
        self.entry_cert_pass = ttk.Entry(cert_frame, width=30, show="*")
        self.entry_cert_pass.insert(0, "123456")
        self.entry_cert_pass.grid(row=1, column=1, sticky='w', padx=10)

        # --- Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(0, 15))

        btn_start = ttk.Button(btn_frame, text="🚀 START BUILD & SIGN", command=self.start_build_process, width=30)
        btn_start.pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="Nur Zertifikat erstellen", command=self.create_cert_only, width=25).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Beenden", command=self.root.quit).pack(side='right')

        # --- Konsole ---
        console_frame = ttk.LabelFrame(main_frame, text=" Log Ausgabe ", padding=10)
        console_frame.pack(fill='both', expand=True)

        self.txt_console = tk.Text(console_frame, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 9), state='disabled')
        self.txt_console.pack(fill='both', expand=True)

        # Stdout umleiten
        sys.stdout = ConsoleRedirector(self.txt_console)
        sys.stderr = ConsoleRedirector(self.txt_console)

    def _create_file_entry(self, parent, label, attr_name, row, filetype):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=5)
        entry = ttk.Entry(parent, width=60)
        entry.grid(row=row, column=1, padx=10, pady=5)
        setattr(self, f"entry_{attr_name}", entry)
        
        btn = ttk.Button(parent, text="📂", width=4, command=lambda: self._browse_file(entry, filetype))
        btn.grid(row=row, column=2, padx=5)

    def _browse_file(self, entry_widget, filetypes):
        if "*.ico" in filetypes:
            filename = filedialog.askopenfilename(filetypes=[("Icon Files", "*.ico"), ("All Files", "*.*")])
        else:
            filename = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        
        if filename:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, filename)

    def _setup_dnd(self):
        """Registriert Drag & Drop Events für die Entry Felder."""
        # Helper Funktion für das Drop-Event
        def drop_script(event):
            path = event.data.strip("{}") # Windows Pfade kommen oft in {}
            if path.endswith(".py"):
                self.entry_script_path.delete(0, 'end')
                self.entry_script_path.insert(0, path)
                # Auto-Fill App Name basierend auf Dateiname
                name = Path(path).stem
                self.entry_app_name.delete(0, 'end')
                self.entry_app_name.insert(0, name)
                self.entry_cert_name.delete(0, 'end')
                self.entry_cert_name.insert(0, f"{name}_Cert")

        def drop_icon(event):
            path = event.data.strip("{}")
            if path.endswith(".ico"):
                self.entry_icon_path.delete(0, 'end')
                self.entry_icon_path.insert(0, path)

        # Events binden
        self.entry_script_path.drop_target_register(DND_FILES)
        self.entry_script_path.dnd_bind('<<Drop>>', drop_script)

        self.entry_icon_path.drop_target_register(DND_FILES)
        self.entry_icon_path.dnd_bind('<<Drop>>', drop_icon)
        
        log.info("Drag & Drop aktiviert: Ziehe .py oder .ico Dateien in die Felder.")

    def start_build_process(self):
        script = self.entry_script_path.get()
        if not script:
            messagebox.showerror("Fehler", "Bitte ein Python-Script auswählen!")
            return

        config = {
            "script_file": script,
            "app_name": self.entry_app_name.get(),
            "icon_path": self.entry_icon_path.get(),
            "console": self.var_console.get(),
            "one_file": self.var_onefile.get(),
            "cert_name": self.entry_cert_name.get(),
            "cert_password": self.entry_cert_pass.get(),
            "use_openssl": self.var_openssl.get()
        }

        t = threading.Thread(target=self._run_orchestrator, args=(config,))
        t.start()

    def create_cert_only(self):
        name = self.entry_cert_name.get()
        pwd = self.entry_cert_pass.get()
        use_ssl = self.var_openssl.get()
        
        def run():
            try:
                self.orchestrator.create_or_get_cert(name, pwd, use_openssl=use_ssl)
                log.success(f"Zertifikat '{name}' erstellt.")
            except Exception as e:
                log.error(f"Fehler: {e}")

        t = threading.Thread(target=run)
        t.start()

    def _run_orchestrator(self, config):
        self.txt_console.configure(state='normal')
        self.txt_console.delete(1.0, 'end')
        self.txt_console.configure(state='disabled')
        
        log.info("--- Starte Build Pipeline ---")
        try:
            self.orchestrator.run_full_pipeline(config)
        except Exception as e:
            log.error(f"Kritischer Fehler: {e}")
