import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import threading
from pathlib import Path

# Framework Imports
from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

class ConsoleRedirector:
    """Leitet Stdout/Stderr in das Text-Widget der GUI um."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, str_val):
        self.text_widget.configure(state='normal')
        self.text_widget.insert('end', str_val)
        self.text_widget.see('end')
        self.text_widget.configure(state='disabled')
        # Auch in die echte Konsole schreiben
        sys.__stdout__.write(str_val)

    def flush(self):
        sys.__stdout__.flush()

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ExeFile Builder & Signer Framework")
        self.root.geometry("900x700")
        self.root.configure(bg="#2b2b2b")

        self.orchestrator = BuildOrchestrator()

        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Farben
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TButton", background=accent_color, foreground=fg_color, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[('active', '#005f9e')])
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor=fg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)

    def _create_widgets(self):
        # --- Hauptcontainer ---
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)

        # --- Sektion 1: Datei Auswahl ---
        file_frame = ttk.LabelFrame(main_frame, text=" Quellcode & Assets ", padding=15)
        file_frame.pack(fill='x', pady=(0, 15))

        self._create_file_entry(file_frame, "Python Script:", "script_path", 0, "*.py")
        self._create_file_entry(file_frame, "Icon (.ico):", "icon_path", 1, "*.ico")
        
        # --- Sektion 2: Konfiguration ---
        config_frame = ttk.LabelFrame(main_frame, text=" Build Konfiguration ", padding=15)
        config_frame.pack(fill='x', pady=(0, 15))

        # App Name
        ttk.Label(config_frame, text="App Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_app_name = ttk.Entry(config_frame, width=30)
        self.entry_app_name.insert(0, "MyApplication")
        self.entry_app_name.grid(row=0, column=1, sticky='w', padx=10, pady=5)

        # Optionen
        self.var_onefile = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="OneFile (Einzelne .exe)", variable=self.var_onefile).grid(row=0, column=2, padx=20)

        self.var_console = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Konsole anzeigen", variable=self.var_console).grid(row=0, column=3, padx=20)

        # --- Sektion 3: Zertifikat ---
        cert_frame = ttk.LabelFrame(main_frame, text=" Code Signing Zertifikat ", padding=15)
        cert_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(cert_frame, text="Zertifikat Name:").grid(row=0, column=0, sticky='w', pady=5)
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

        ttk.Button(btn_frame, text="START BUILD & SIGN", command=self.start_build_process, width=25).pack(side='left', padx=5)
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
        entry = ttk.Entry(parent, width=50)
        entry.grid(row=row, column=1, padx=10, pady=5)
        setattr(self, f"entry_{attr_name}", entry)
        
        btn = ttk.Button(parent, text="Durchsuchen", command=lambda: self._browse_file(entry, filetype))
        btn.grid(row=row, column=2, padx=5)

    def _browse_file(self, entry_widget, filetypes):
        if "*.ico" in filetypes:
            filename = filedialog.askopenfilename(filetypes=[("Icon Files", "*.ico"), ("All Files", "*.*")])
        else:
            filename = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        
        if filename:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, filename)

    def start_build_process(self):
        # Validierung
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
            "cert_password": self.entry_cert_pass.get()
        }

        # Threading damit GUI nicht einfriert
        t = threading.Thread(target=self._run_orchestrator, args=(config,))
        t.start()

    def create_cert_only(self):
        name = self.entry_cert_name.get()
        pwd = self.entry_cert_pass.get()
        
        def run():
            try:
                self.orchestrator.create_or_get_cert(name, pwd)
                log.success(f"Zertifikat '{name}' wurde geprüft/erstellt.")
            except Exception as e:
                log.error(f"Fehler: {e}")

        t = threading.Thread(target=run)
        t.start()

    def _run_orchestrator(self, config):
        self.txt_console.configure(state='normal')
        self.txt_console.delete(1.0, 'end')
        self.txt_console.configure(state='disabled')
        
        log.info("--- Starte automatisierten Prozess ---")
        try:
            self.orchestrator.run_full_pipeline(config)
        except Exception as e:
            log.error(f"Unerwarteter Fehler im GUI Thread: {e}")
