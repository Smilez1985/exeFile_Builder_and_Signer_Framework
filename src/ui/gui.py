import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import threading
from pathlib import Path

# Framework Imports
from src.core.orchestrator import BuildOrchestrator
from src.utils.helpers import log

# DND Support
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
        sys.__stdout__.write(str_val)

    def flush(self):
        sys.__stdout__.flush()

class AppGUI:
    def __init__(self, root, dnd_enabled=False):
        self.root = root
        self.dnd_enabled = dnd_enabled
        self.root.title("ExeFile Builder & Signer Framework - Professional Edition")
        self.root.geometry("1000x850")
        self.root.configure(bg="#2b2b2b")

        self.orchestrator = BuildOrchestrator()

        self._setup_styles()
        self._create_widgets()
        
        if self.dnd_enabled:
            self._setup_dnd()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#007acc"
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.configure("TButton", background=accent_color, foreground=fg_color, borderwidth=0, font=("Segoe UI", 10, "bold"))
        style.map("TButton", background=[('active', '#005f9e')])
        
        style.configure("TCheckbutton", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[('active', bg_color)], indicatorcolor=[('selected', accent_color)])
        
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor="#555555")
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Segoe UI", 9, "bold"))
        
        # Notebook (Tabs) Styles
        style.configure("TNotebook", background=bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background="#3c3c3c", foreground="#aaaaaa", padding=[10, 5])
        style.map("TNotebook.Tab", background=[("selected", accent_color)], foreground=[("selected", "#ffffff")])

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Header
        ttk.Label(main_frame, text="EXE BUILDER & SIGNER", font=("Segoe UI", 18, "bold"), foreground="#007acc").pack(pady=(0, 20))

        # --- 1. SOURCE & ASSETS ---
        file_frame = ttk.LabelFrame(main_frame, text=" 1. Quellen & Daten ", padding=15)
        file_frame.pack(fill='x', pady=(0, 15))

        self._create_file_entry(file_frame, "Start Script (.py):", "script_path", 0, "*.py")
        self._create_file_entry(file_frame, "Icon (.ico):", "icon_path", 1, "*.ico")
        
        # Extra Assets (Ordner oder Dateien)
        ttk.Label(file_frame, text="Zusatz-Daten (Ordner/Datei):").grid(row=2, column=0, sticky='w', pady=5)
        self.entry_assets = ttk.Entry(file_frame, width=60)
        self.entry_assets.grid(row=2, column=1, padx=10, pady=5)
        ttk.Button(file_frame, text="📂", width=4, command=self._browse_folder_or_file).grid(row=2, column=2, padx=5)
        ttk.Label(file_frame, text="(Optional: Wird mit in die EXE gepackt)").grid(row=3, column=1, sticky='w', padx=10)

        # --- 2. SETTINGS ---
        config_frame = ttk.LabelFrame(main_frame, text=" 2. Build Optionen ", padding=15)
        config_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(config_frame, text="App Name:").grid(row=0, column=0, sticky='w')
        self.entry_app_name = ttk.Entry(config_frame, width=30)
        self.entry_app_name.insert(0, "MyTool")
        self.entry_app_name.grid(row=0, column=1, sticky='w', padx=10)

        self.var_onefile = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="OneFile (.exe)", variable=self.var_onefile).grid(row=0, column=2, padx=20)
        
        self.var_console = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Konsole zeigen", variable=self.var_console).grid(row=0, column=3, padx=20)

        # --- 3. SIGNING (TABS) ---
        cert_group = ttk.LabelFrame(main_frame, text=" 3. Digitale Signatur ", padding=15)
        cert_group.pack(fill='x', pady=(0, 15))

        self.notebook = ttk.Notebook(cert_group)
        self.notebook.pack(fill='both', expand=True)

        # TAB A: Auto / Neu / Cache
        tab_auto = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab_auto, text="Automatisch / Cache")
        
        ttk.Label(tab_auto, text="Zertifikats-Name (ID):").grid(row=0, column=0, sticky='w', pady=5)
        self.entry_cert_name = ttk.Entry(tab_auto, width=40)
        self.entry_cert_name.insert(0, "MySelfSignedCert")
        self.entry_cert_name.grid(row=0, column=1, padx=10)
        ttk.Label(tab_auto, text="(Erstellt neu oder nutzt Cache)").grid(row=0, column=2, sticky='w')

        # TAB B: Existing File
        tab_file = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(tab_file, text="Vorhandene PFX Datei")
        
        self._create_file_entry(tab_file, "PFX Datei:", "pfx_path", 0, "*.pfx")
        
        # Passwort (für beide Tabs gültig)
        pass_frame = ttk.Frame(cert_group, padding=(15, 5))
        pass_frame.pack(fill='x')
        ttk.Label(pass_frame, text="Zertifikats-Passwort:").pack(side='left')
        self.entry_cert_pass = ttk.Entry(pass_frame, width=30, show="*")
        self.entry_cert_pass.insert(0, "123456")
        self.entry_cert_pass.pack(side='left', padx=10)
        
        # OpenSSL Switch
        self.var_openssl = tk.BooleanVar(value=False)
        ttk.Checkbutton(pass_frame, text="OpenSSL Engine nutzen (statt PowerShell)", variable=self.var_openssl).pack(side='right')

        # --- ACTION ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(0, 10))
        ttk.Button(btn_frame, text="🚀 START PROCESS", command=self.start_build, width=30).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="EXIT", command=self.root.quit).pack(side='right')

        # --- CONSOLE ---
        self.txt_console = tk.Text(main_frame, bg="#1e1e1e", fg="#00ff00", height=10, font=("Consolas", 9), state='disabled')
        self.txt_console.pack(fill='both', expand=True)
        sys.stdout = ConsoleRedirector(self.txt_console)
        sys.stderr = ConsoleRedirector(self.txt_console)

    def _create_file_entry(self, parent, label, attr_name, row, filetype):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky='w', pady=5)
        entry = ttk.Entry(parent, width=50)
        entry.grid(row=row, column=1, padx=10, pady=5)
        setattr(self, f"entry_{attr_name}", entry)
        btn = ttk.Button(parent, text="📂", width=4, command=lambda: self._browse_file(entry, filetype))
        btn.grid(row=row, column=2, padx=5)

    def _browse_file(self, entry, ftype):
        f = filedialog.askopenfilename(filetypes=[("Files", ftype), ("All", "*.*")])
        if f:
            entry.delete(0, 'end')
            entry.insert(0, f)

    def _browse_folder_or_file(self):
        # Einfacher Hack: Wir fragen erst, ob Ordner oder Datei
        # Für DAU: Wir nehmen einfach Folder Dialog, weil das für "Assets" meistens stimmt.
        f = filedialog.askdirectory(title="Ordner mit Assets wählen")
        if f:
            self.entry_assets.delete(0, 'end')
            self.entry_assets.insert(0, f)

    def _setup_dnd(self):
        def drop_generic(event, entry):
            path = event.data.strip("{}")
            entry.delete(0, 'end')
            entry.insert(0, path)
            
        self.entry_script_path.drop_target_register(DND_FILES)
        self.entry_script_path.dnd_bind('<<Drop>>', lambda e: drop_generic(e, self.entry_script_path))
        
        self.entry_icon_path.drop_target_register(DND_FILES)
        self.entry_icon_path.dnd_bind('<<Drop>>', lambda e: drop_generic(e, self.entry_icon_path))
        
        self.entry_pfx_path.drop_target_register(DND_FILES)
        self.entry_pfx_path.dnd_bind('<<Drop>>', lambda e: drop_generic(e, self.entry_pfx_path))

    def start_build(self):
        # Welcher Tab ist aktiv?
        current_tab = self.notebook.index(self.notebook.select())
        cert_mode = "auto" if current_tab == 0 else "file"

        config = {
            "script_file": self.entry_script_path.get(),
            "app_name": self.entry_app_name.get(),
            "icon_path": self.entry_icon_path.get(),
            "asset_path": self.entry_assets.get(), # NEU
            "console": self.var_console.get(),
            "one_file": self.var_onefile.get(),
            "cert_mode": cert_mode,
            "cert_name": self.entry_cert_name.get(),
            "pfx_path": self.entry_pfx_path.get(),
            "cert_password": self.entry_cert_pass.get(),
            "use_openssl": self.var_openssl.get()
        }
        
        if not config["script_file"]:
            messagebox.showerror("Fehler", "Kein Script ausgewählt!")
            return

        t = threading.Thread(target=self._run, args=(config,))
        t.start()

    def _run(self, config):
        self.txt_console.configure(state='normal')
        self.txt_console.delete(1.0, 'end')
        self.txt_console.configure(state='disabled')
        try:
            self.orchestrator.run_full_pipeline(config)
        except Exception as e:
            log.error(f"CRITICAL ERROR: {e}")
