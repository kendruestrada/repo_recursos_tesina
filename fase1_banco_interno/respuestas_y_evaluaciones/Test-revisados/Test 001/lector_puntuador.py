import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
from datetime import datetime
import re

# ── Archivo de registro ──────────────────────────────────────────────────────
REGISTRO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registro_notas.json")

def cargar_registro():
    if os.path.exists(REGISTRO_PATH):
        with open(REGISTRO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_registro(datos):
    with open(REGISTRO_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def extraer_markdown(ruta):
    """Extract text and formatting from .md file.
    Returns: (contenido_text, lista_de_formatos)
    donde formatos es lista de tuplas: (inicio, fin, tipo_formato)
    """
    with open(ruta, "r", encoding="utf-8") as f:
        contenido = f.read()
    
    formatos = []  # lista de (inicio, fin, 'bold'/'italic'/'heading'/'list')
    
    # Procesar negrita (**texto**)
    for match in re.finditer(r'\*\*(.+?)\*\*', contenido):
        inicio = match.start()
        fin = match.end()
        formatos.append((inicio, fin, 'bold'))
    
    # Procesar cursiva (*texto* o _texto_)
    for match in re.finditer(r'[*_]([^*_]+?)[*_]', contenido):
        inicio = match.start()
        fin = match.end()
        formatos.append((inicio, fin, 'italic'))
    
    # Procesar títulos (# Título, ## Subtítulo, etc.)
    for match in re.finditer(r'^(#{1,6})\s+(.+?)$', contenido, re.MULTILINE):
        inicio = match.start()
        fin = match.end()
        nivel = len(match.group(1))
        formatos.append((inicio, fin, f'heading{nivel}'))
    
    # Procesar listas (- item, * item)
    for match in re.finditer(r'^[\-\*]\s+(.+?)$', contenido, re.MULTILINE):
        inicio = match.start()
        fin = match.end()
        formatos.append((inicio, fin, 'list'))
    
    return contenido, formatos

# ── Aplicación principal ─────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📄 Lector & Puntuador de Textos")
        self.geometry("950x680")
        self.configure(bg="#1a1a2e")
        self.resizable(True, True)

        self.registro = cargar_registro()
        self.archivo_actual = None
        # rating variable holds value from 1 to 5 (stars)
        self.puntuacion = tk.IntVar(value=5)
        # Additional evaluation fields
        # identifico_error: 1 = Sí, 0 = No (use Radiobuttons)
        self.identifico_error = tk.IntVar(value=0)
        self.calidad_explicacion = tk.IntVar(value=5)      # 1-5
        self.calidad_propuestas = tk.IntVar(value=5)       # 1-5
        self.nivel_alucinacion = tk.IntVar(value=5)        # 1-5 

        self._estilos()
        self._ui()
        self._actualizar_historial()

    # ── Estilos ──────────────────────────────────────────────────────────────
    def _estilos(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        BG   = "#1a1a2e"
        CARD = "#16213e"
        ACC  = "#e94560"
        FG   = "#eaeaea"
        SUB  = "#a0a0b0"

        style.configure("TFrame",       background=BG)
        style.configure("Card.TFrame",  background=CARD)
        style.configure("TLabel",       background=BG, foreground=FG,
                        font=("Georgia", 11))
        style.configure("Title.TLabel", background=BG, foreground=ACC,
                        font=("Georgia", 20, "bold"))
        style.configure("Sub.TLabel",   background=CARD, foreground=SUB,
                        font=("Courier", 9))
        style.configure("Info.TLabel",  background=CARD, foreground=FG,
                        font=("Georgia", 10))
        style.configure("Accent.TButton",
                        background=ACC, foreground="white",
                        font=("Georgia", 10, "bold"),
                        padding=(12, 6), relief="flat")
        style.map("Accent.TButton",
                  background=[("active", "#c73652")])
        style.configure("TScrollbar",   background=CARD, troughcolor=BG,
                        arrowcolor=FG)
        style.configure("Treeview",     background=CARD, fieldbackground=CARD,
                        foreground=FG, font=("Courier", 9),
                        rowheight=24)
        style.configure("Treeview.Heading",
                        background="#0f3460", foreground=ACC,
                        font=("Georgia", 10, "bold"))
        style.map("Treeview", background=[("selected", "#0f3460")])

        self.BG = BG; self.CARD = CARD; self.ACC = ACC; self.FG = FG; self.SUB = SUB

    # ── UI ───────────────────────────────────────────────────────────────────
    def _ui(self):
        # Título
        ttk.Label(self, text="Lector & Puntuador de Textos", style="Title.TLabel")\
            .pack(pady=(18, 4))
        ttk.Label(self, text="Abre un archivo · Léelo · Puntúalo · Regístralo",
                  foreground=self.SUB, background=self.BG,
                  font=("Georgia", 10, "italic")).pack(pady=(0, 12))

        # Panel principal (izq + der)
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=18, pady=(0, 14))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        self._panel_texto(main)
        self._panel_historial(main)

    def _panel_texto(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        # Barra superior
        top = ttk.Frame(frame, style="Card.TFrame")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        btn_abrir = tk.Button(top, text="📂  Abrir Archivo",
                              command=self._abrir_archivo,
                              bg=self.ACC, fg="white",
                              font=("Georgia", 10, "bold"),
                              relief="flat", cursor="hand2",
                              padx=14, pady=6)
        btn_abrir.pack(side="left")

        self.lbl_archivo = tk.Label(top, text="Ningún archivo abierto",
                                    bg=self.CARD, fg=self.SUB,
                                    font=("Courier", 9), anchor="w")
        self.lbl_archivo.pack(side="left", padx=12, fill="x", expand=True)

        # Área de texto
        txt_frame = tk.Frame(frame, bg=self.CARD)
        txt_frame.grid(row=1, column=0, sticky="nsew")
        txt_frame.rowconfigure(0, weight=1)
        txt_frame.columnconfigure(0, weight=1)

        self.texto = tk.Text(txt_frame,
                             bg="#0d1117", fg="#c9d1d9",
                             font=("Courier New", 11),
                             relief="flat", wrap="word",
                             selectbackground=self.ACC,
                             insertbackground=self.ACC,
                             padx=12, pady=10, state="disabled")
        self.texto.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(txt_frame, orient="vertical",
                           command=self.texto.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.texto.configure(yscrollcommand=sb.set)

        # Estadísticas rápidas
        self.lbl_stats = tk.Label(frame, text="",
                                  bg=self.CARD, fg=self.SUB,
                                  font=("Courier", 9))
        self.lbl_stats.grid(row=2, column=0, sticky="w", pady=(6, 0))

        # Puntuación
        self._panel_puntuacion(frame)

    def _panel_puntuacion(self, parent):
        pframe = tk.Frame(parent, bg="#0f3460", bd=0)
        pframe.grid(row=3, column=0, sticky="ew", pady=(14, 0))

        tk.Label(pframe, text="Puntuación", bg="#0f3460", fg=self.ACC,
                 font=("Georgia", 12, "bold")).pack(pady=(10, 4))

        # Estrellas
        star_frame = tk.Frame(pframe, bg="#0f3460")
        star_frame.pack()

        self.stars = []
        for i in range(1, 6):
            btn = tk.Button(star_frame, text="★", font=("Arial", 18),
                            bg="#0f3460", fg="#444", relief="flat",
                            cursor="hand2", bd=0,
                            command=lambda v=i: self._set_puntuacion(v))
            btn.pack(side="left", padx=1)
            self.stars.append(btn)

        self.lbl_puntuacion = tk.Label(pframe, text="3 / 5",
                                       bg="#0f3460", fg=self.FG,
                                       font=("Georgia", 11))
        self.lbl_puntuacion.pack(pady=4)
        # initialize to maximum (5 stars)
        self._set_puntuacion(5)

        # Comentario
        tk.Label(pframe, text="Comentario (opcional):",
             bg="#0f3460", fg=self.SUB,
             font=("Georgia", 9)).pack(anchor="w", padx=14)

        self.comentario = tk.Entry(pframe, bg="#1a1a2e", fg=self.FG,
                       font=("Courier", 10), relief="flat",
                       insertbackground=self.ACC)
        self.comentario.pack(fill="x", padx=14, pady=(2, 8))

        # Evaluación detallada
        det = tk.Frame(pframe, bg="#0f3460")
        det.pack(fill="x", padx=14, pady=(4, 8))

        # Identificó error (Sí / No) as Radiobuttons
        rb_frame = tk.Frame(det, bg="#0f3460")
        rb_frame.pack(anchor="w")
        tk.Label(rb_frame, text="Identificó error y causa raíz:", bg="#0f3460", fg=self.SUB,
                 font=("Georgia", 9)).pack(side="left")
        tk.Radiobutton(rb_frame, text="Sí", variable=self.identifico_error, value=1,
                       bg="#0f3460", fg=self.FG, selectcolor=self.CARD,
                       activebackground="#0f3460", font=("Georgia", 9), indicatoron=0,
                       width=4, command=lambda: None).pack(side="left", padx=(8, 4))
        tk.Radiobutton(rb_frame, text="No", variable=self.identifico_error, value=0,
                       bg="#0f3460", fg=self.FG, selectcolor=self.CARD,
                       activebackground="#0f3460", font=("Georgia", 9), indicatoron=0,
                       width=4, command=lambda: None).pack(side="left")

        # Calidad explicación (5 estrellas)
        tk.Label(det, text="Explicación error:", bg="#0f3460", fg=self.SUB,
                 font=("Georgia", 9)).pack(anchor="w", pady=(8, 0))
        frame_exp = tk.Frame(det, bg="#0f3460")
        frame_exp.pack(anchor="w")
        self.stars_explicacion = []
        for i in range(1, 6):
            btn = tk.Button(frame_exp, text="★", font=("Arial", 14),
                            bg="#0f3460", fg=(self.ACC if i <= self.calidad_explicacion.get() else "#444"),
                            relief="flat", cursor="hand2", bd=0,
                            command=lambda v=i: self._set_calidad_explicacion(v))
            btn.pack(side="left", padx=1)
            self.stars_explicacion.append(btn)
        self.lbl_calidad_explicacion = tk.Label(frame_exp, text=f"{self.calidad_explicacion.get()} / 5",
                                               bg="#0f3460", fg=self.FG, font=("Georgia", 9))
        self.lbl_calidad_explicacion.pack(side="left", padx=(8, 0))

        # Calidad propuestas (5 estrellas)
        tk.Label(det, text="Propuestas solución:", bg="#0f3460", fg=self.SUB,
                 font=("Georgia", 9)).pack(anchor="w", pady=(8, 0))
        frame_prop = tk.Frame(det, bg="#0f3460")
        frame_prop.pack(anchor="w")
        self.stars_propuestas = []
        for i in range(1, 6):
            btn = tk.Button(frame_prop, text="★", font=("Arial", 14),
                            bg="#0f3460", fg=(self.ACC if i <= self.calidad_propuestas.get() else "#444"),
                            relief="flat", cursor="hand2", bd=0,
                            command=lambda v=i: self._set_calidad_propuestas(v))
            btn.pack(side="left", padx=1)
            self.stars_propuestas.append(btn)
        self.lbl_calidad_propuestas = tk.Label(frame_prop, text=f"{self.calidad_propuestas.get()} / 5",
                                               bg="#0f3460", fg=self.FG, font=("Georgia", 9))
        self.lbl_calidad_propuestas.pack(side="left", padx=(8, 0))

        # Nivel de alucinación (5 estrellas)
        tk.Label(det, text="Realidad en analisis(no alucina):", bg="#0f3460", fg=self.SUB,
                 font=("Georgia", 9)).pack(anchor="w", pady=(8, 0))
        frame_al = tk.Frame(det, bg="#0f3460")
        frame_al.pack(anchor="w")
        self.stars_alucinacion = []
        for i in range(1, 6):
            btn = tk.Button(frame_al, text="★", font=("Arial", 14),
                            bg="#0f3460", fg=(self.ACC if i <= self.nivel_alucinacion.get() else "#444"),
                            relief="flat", cursor="hand2", bd=0,
                            command=lambda v=i: self._set_nivel_alucinacion(v))
            btn.pack(side="left", padx=1)
            self.stars_alucinacion.append(btn)
        self.lbl_nivel_alucinacion = tk.Label(frame_al, text=f"{self.nivel_alucinacion.get()} / 5",
                                             bg="#0f3460", fg=self.FG, font=("Georgia", 9))
        self.lbl_nivel_alucinacion.pack(side="left", padx=(8, 0))

        tk.Button(pframe, text="💾  Guardar Puntuación",
              command=self._guardar_puntuacion,
              bg=self.ACC, fg="white",
              font=("Georgia", 10, "bold"),
              relief="flat", cursor="hand2",
              padx=16, pady=7).pack(pady=(6, 12))

    def _panel_historial(self, parent):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=14)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        tk.Label(frame, text="Historial de Notas",
                 bg=self.CARD, fg=self.ACC,
                 font=("Georgia", 13, "bold")).grid(row=0, column=0,
                                                     sticky="w", pady=(0, 8))

        cols = ("Archivo", "Nota", "Fecha")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                  selectmode="browse")
        self.tree.heading("Archivo", text="Archivo")
        self.tree.heading("Nota",    text="Nota")
        self.tree.heading("Fecha",   text="Fecha")
        self.tree.column("Archivo", width=160, anchor="w")
        self.tree.column("Nota",    width=50,  anchor="center")
        self.tree.column("Fecha",   width=120, anchor="center")
        self.tree.grid(row=1, column=0, sticky="nsew")

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.bind("<<TreeviewSelect>>", self._ver_detalle)

        # Detalle seleccionado
        self.lbl_detalle = tk.Label(frame, text="Selecciona una entrada\npara ver el comentario.",
                                    bg=self.CARD, fg=self.SUB,
                                    font=("Courier", 9),
                                    justify="left", anchor="w",
                                    wraplength=240)
        self.lbl_detalle.grid(row=2, column=0, columnspan=2,
                               sticky="ew", pady=(10, 0))

        # Botón limpiar historial
        tk.Button(frame, text="🗑  Limpiar Historial",
                  command=self._limpiar_historial,
                  bg="#333", fg=self.SUB,
                  font=("Georgia", 9), relief="flat",
                  cursor="hand2", padx=10, pady=4)\
            .grid(row=3, column=0, columnspan=2, sticky="e", pady=(8, 0))

    # ── Lógica ───────────────────────────────────────────────────────────────
    def _abrir_archivo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo de texto",
            filetypes=[("Archivos Markdown", "*.md"),
                       ("Archivos de texto", "*.txt *.csv *.log *.py"),
                       ("Todos", "*.*")])
        if not path:
            return
        
        try:
            # Detectar si es .md
            if path.lower().endswith('.md'):
                contenido, formatos = extraer_markdown(path)
            else:
                # Leer archivo de texto plano
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
                formatos = []
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
            return

        self.archivo_actual = path
        self.lbl_archivo.config(text=os.path.basename(path))

        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", contenido)
        
        # Aplicar formatos si existen
        if formatos:
            # Definir tags de formato
            self.texto.tag_configure("bold", font=("Courier New", 11, "bold"))
            self.texto.tag_configure("italic", font=("Courier New", 11, "italic"))
            self.texto.tag_configure("heading1", font=("Courier New", 14, "bold"), foreground="#e94560")
            self.texto.tag_configure("heading2", font=("Courier New", 13, "bold"), foreground="#e94560")
            self.texto.tag_configure("heading3", font=("Courier New", 12, "bold"), foreground="#e94560")
            self.texto.tag_configure("heading4", font=("Courier New", 11, "bold"), foreground="#e94560")
            self.texto.tag_configure("heading5", font=("Courier New", 11, "bold"), foreground="#a0a0b0")
            self.texto.tag_configure("heading6", font=("Courier New", 11, "bold"), foreground="#a0a0b0")
            self.texto.tag_configure("list", foreground="#c9d1d9")
            
            # Aplicar cada formato
            for inicio, fin, tipo in formatos:
                inicio_idx = f"1.0+{inicio}c"
                fin_idx = f"1.0+{fin}c"
                self.texto.tag_add(tipo, inicio_idx, fin_idx)
        
        self.texto.config(state="disabled")

        palabras = len(contenido.split())
        lineas   = contenido.count("\n") + 1
        chars    = len(contenido)
        self.lbl_stats.config(
            text=f"  {chars} caracteres · {palabras} palabras · {lineas} líneas")

    def _set_puntuacion(self, valor):
        self.puntuacion.set(valor)
        # update label to display value out of 5
        self.lbl_puntuacion.config(text=f"{valor} / 5")
        for i, btn in enumerate(self.stars):
            btn.config(fg=self.ACC if i < valor else "#444")

    # Star setters for detailed evaluation
    def _set_calidad_explicacion(self, valor):
        self.calidad_explicacion.set(valor)
        if hasattr(self, 'lbl_calidad_explicacion'):
            self.lbl_calidad_explicacion.config(text=f"{valor} / 5")
        for i, btn in enumerate(getattr(self, 'stars_explicacion', [])):
            btn.config(fg=self.ACC if i < valor else "#444")

    def _set_calidad_propuestas(self, valor):
        self.calidad_propuestas.set(valor)
        if hasattr(self, 'lbl_calidad_propuestas'):
            self.lbl_calidad_propuestas.config(text=f"{valor} / 5")
        for i, btn in enumerate(getattr(self, 'stars_propuestas', [])):
            btn.config(fg=self.ACC if i < valor else "#444")

    def _set_nivel_alucinacion(self, valor):
        self.nivel_alucinacion.set(valor)
        if hasattr(self, 'lbl_nivel_alucinacion'):
            self.lbl_nivel_alucinacion.config(text=f"{valor} / 5")
        for i, btn in enumerate(getattr(self, 'stars_alucinacion', [])):
            btn.config(fg=self.ACC if i < valor else "#444")

    def _guardar_puntuacion(self):
        if not self.archivo_actual:
            messagebox.showwarning("Sin archivo",
                                   "Primero abre un archivo de texto.")
            return
        entrada = {
            "archivo":     self.archivo_actual,
            "nombre":      os.path.basename(self.archivo_actual),
            "puntuacion":  self.puntuacion.get(),
            "comentario":  self.comentario.get().strip(),
            "identifico_error": bool(self.identifico_error.get()),
            "calidad_explicacion": int(self.calidad_explicacion.get()),
            "calidad_propuestas": int(self.calidad_propuestas.get()),
            "realidad_diagnostico_(nivel_alucinacion)": int(self.nivel_alucinacion.get()),
            "fecha":       datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.registro.append(entrada)
        guardar_registro(self.registro)
        self._actualizar_historial()
        messagebox.showinfo("Guardado",
                            f"Nota {entrada['puntuacion']}/5 guardada para\n{entrada['nombre']}")
    def _actualizar_historial(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for entrada in reversed(self.registro):
            self.tree.insert("", "end", values=(
                entrada["nombre"],
                f"⭐ {entrada['puntuacion']}/5",
                entrada["fecha"]
            ))

    def _ver_detalle(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = len(self.registro) - 1 - self.tree.index(sel[0])
        e = self.registro[idx]
        ident = 'Sí' if e.get('identifico_error') else 'No'
        detalle = (f"📁 {e.get('nombre')}\n"
               f"⭐ {e.get('puntuacion', '?')}/5  ·  {e.get('fecha', '')}\n"
               f"🔎 Identificó error y causa raíz: {ident}\n"
               f"📝 Calidad explicación: {e.get('calidad_explicacion', '-')}/5\n"
               f"🛠 Calidad propuestas: {e.get('calidad_propuestas', '-')}/5\n"
               f"🤖 Realidad en diagnostico (Nivel de alucinación): {e.get('nivel_alucinacion', '-')}/5\n"
               f"💬 {e.get('comentario') or '(sin comentario)'}")
        self.lbl_detalle.config(text=detalle, fg=self.FG)

    def _limpiar_historial(self):
        if not self.registro:
            return
        if messagebox.askyesno("Confirmar",
                               "¿Eliminar todo el historial de notas?"):
            self.registro = []
            guardar_registro(self.registro)
            self._actualizar_historial()
            self.lbl_detalle.config(text="Historial eliminado.", fg=self.SUB)


if __name__ == "__main__":
    app = App()
    app.mainloop()
