import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import re
import configparser


class RarSeekerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RarSeeker")
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Carregue o caminho do banco de dados a partir do arquivo de configuração
        self.config = configparser.ConfigParser()
        self.config_file = "rarseeker_config.ini"
        self.db_path = None

        if os.path.isfile(self.config_file):
            self.config.read(self.config_file)
            if "Settings" in self.config:
                self.db_path = self.config["Settings"].get("db_path", None)

        # Campos de pesquisa no lado esquerdo
        search_frame = ttk.Frame(root)
        search_frame.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    # Adicione o dropdown para selecionar o campo de pesquisa
        self.search_field_label = ttk.Label(search_frame, text="Search by:")
        self.search_field_label.grid(row=0, column=0, padx=5, pady=5)

        self.search_field_var = tk.StringVar()
        self.search_field_var.set("name")  # Inicialmente definido como "name"

        self.name_search_radio = ttk.Radiobutton(search_frame, text="Name", variable=self.search_field_var,
                                                 value="name")
        self.imdb_search_radio = ttk.Radiobutton(search_frame, text="IMDB Tag", variable=self.search_field_var,
                                                 value="imdb tag")

        self.name_search_radio.grid(row=0, column=1, padx=5, pady=5)
        self.imdb_search_radio.grid(row=0, column=2, padx=5, pady=5)

        #self.name_label = ttk.Label(search_frame, text="Name:")
        self.name_field = ttk.Entry(search_frame, width=40)
        self.name_field.bind('<Return>', lambda event=None: self.search_db())
        self.search_button = ttk.Button(search_frame, text="Search", command=self.search_db)

        #self.name_label.grid(row=0, column=2, padx=5, pady=5)
        self.name_field.grid(row=0, column=3, padx=5, pady=5)
        self.search_button.grid(row=0, column=4, padx=5, pady=5)



        self.category_label = ttk.Label(search_frame, text="Category:")
        self.category_label.grid(row=0, column=5, padx=5, pady=5)

        self.category_combo = ttk.Combobox(search_frame,
                                           values=["All", "ebooks", "games_pc_iso", "games_pc_rip", "games_ps3",
                                                   "games_ps4", "games_xbox360", "movies", "movies_bd_full",
                                                   "movies_bd_remux", "movies_x264", "movies_x264_3d",
                                                   "movies_x264_4k", "movies_x264_720", "movies_x265",
                                                   "movies_x265_4k", "movies_x265_4k_hdr", "movies_xvid",
                                                   "movies_xvid_720", "music_flac", "music_mp3",
                                                   "software_pc_iso", "tv", "tv_sd", "tv_uhd", "xxx"])
        self.category_combo.set("All")
        self.category_combo.grid(row=0, column=6, padx=5, pady=5)
        self.column_widths = [220, 560, 50, 55, 2, 3, 4]
        # Área de exibição dos resultados
        self.treeview = ttk.Treeview(root, columns=(
            "Hash", "Title", "DT", "Category", "Size", "Resolution", "IMDB Tag"), show="headings")
        # self.treeview.heading("ID", text="ID")
        self.treeview.heading("Hash", text="Hash", command=lambda: self.treeview_sort_column("Hash", False))
        self.treeview.heading("Title", text="Title", command=lambda: self.treeview_sort_column("Title", False))
        self.treeview.heading("DT", text="Date", command=lambda: self.treeview_sort_column("DT", False))
        self.treeview.heading("Category", text="Category", command=lambda: self.treeview_sort_column("Category", False))
        self.treeview.heading("Size", text="Size", command=lambda: self.treeview_sort_size())
        self.treeview.heading("Resolution", text="Resolution", command=lambda: self.treeview_sort_resolution())
        self.treeview.heading("IMDB Tag", text="IMDB Tag", command=lambda: self.treeview_sort_column("IMDB Tag", False))
        self.treeview.grid(row=1, column=0, columnspan=5, padx=5, pady=5, sticky="nsew")

        self.treeview.bind("<Double-1>", lambda event: None)
        self.treeview.bind("<Button-3>", self.show_context_menu)

        self.scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.treeview.yview)
        self.scrollbar.grid(row=1, column=5, padx=5, pady=5, sticky="ns")
        self.treeview.configure(yscrollcommand=self.scrollbar.set)
        for i, col in enumerate(self.treeview["columns"]):
            self.treeview.column(col, width=self.column_widths[i])
        self.search_count_label = ttk.Label(root, text="Records Found: 0")
        self.search_count_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Botão de conexão e carregamento do banco de dados
        button_frame = ttk.Frame(root)
        button_frame.grid(row=2, column=0, columnspan=5, padx=5, pady=5)

        self.connect_load_button = ttk.Button(button_frame, text="Connect & Load DB", command=self.connect_and_load_db)
        self.connect_load_button.grid(row=0, column=0, padx=5, pady=5)

        self.resolution_filter_label = ttk.Label(button_frame, text="Resolution Filter:")
        self.resolution_filter_label.grid(row=0, column=1, padx=5, pady=5)

        self.resolution_combo = ttk.Combobox(button_frame, values=["All"])
        self.resolution_combo.set("All")
        self.resolution_combo.grid(row=0, column=2, padx=5, pady=5)

        self.sort_column = None
        self.sort_descending = False
        # Bloquear os campos de pesquisa antes da conexão com o banco de dados
        self.resolution_combo.config(state="disabled")
        self.name_field.config(state="disabled")
        self.category_combo.config(state="disabled")
        self.search_button.config(state="disabled")
        self.name_search_radio.config(state="disabled")
        self.imdb_search_radio.config(state="disabled")
        self.resolution_combo.bind("<<ComboboxSelected>>", self.update_resolution_filter)

        self.db_file = None
        self.db_connection = None
        self.current_db = None

    def save_config(self):
        if self.db_path:
            if not os.path.isfile(self.config_file):
                open(self.config_file, 'w').close()  # Crie o arquivo de configuração se ele não existir

            self.config["Settings"] = {"db_path": self.db_path}
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)

    def connect_and_load_db(self):
        if self.db_path and not os.path.exists(self.db_path):
            self.db_path = None  # Define o caminho do banco de dados como None para permitir ao usuário selecionar um novo
            self.save_config()

        if not self.db_path:
            db_path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.sqlite")])
            if db_path:
                self.db_path = db_path
                self.save_config()
            else:
                return

        if not os.path.exists(self.db_path):
            messagebox.showerror("Error", "Database not found at the specified path.")
            return

        self.db_connection = sqlite3.connect(self.db_path)
        # Habilitar os campos após a conexão com o banco de dados
        self.name_field.config(state="normal")
        self.category_combo.config(state="normal")
        self.search_button.config(state="normal")
        self.name_search_radio.config(state="normal")
        self.imdb_search_radio.config(state="normal")
        self.resolution_combo["state"] = "readonly"  # Definir como "readonly"
        self.category_combo["state"] = "readonly"  # Definir como "readonly"
        self.current_db = self.db_path
        self.connect_load_button.config(state="disabled")

    def load_db(self):
        if not self.current_db:
            return
        search_input = self.name_field.get()
        selected_category = self.category_combo.get()
        search_field = self.search_field_var.get()

        # Dividir a entrada do usuário em palavras individuais
        search_words = search_input.split()

        # Combine as palavras usando '%' para criar um único critério "LIKE"
        search_query = '%' + '%'.join(search_words) + '%'

        # Construa a consulta SQL
        if search_field == "name":  # Verifique o campo selecionado
            query = f"SELECT * FROM items WHERE title LIKE '{search_query}'"
        elif search_field == "imdb tag":
            query = f"SELECT * FROM items WHERE imdb = '{search_input}'"

        if selected_category != "All":
            query += f" AND cat = '{selected_category}'"

        cursor = self.db_connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()  # Buscar todos os resultados, sem limite

        self.treeview.delete(*self.treeview.get_children())

        for row in rows:
            id, hash, title, dt, cat, size, ext_id, imdb = row
            resolution = self.extract_resolution(title)
            size_str = self.format_size(size)
            imdb = "" if imdb is None else imdb
            self.treeview.insert("", "end", values=(hash, title, dt, cat, size_str, resolution, imdb))

        distinct_resolutions = self.get_distinct_resolutions(rows)
        self.resolution_combo["values"] = ["All"] + distinct_resolutions

        # Atualize a contagem e exiba-a
        self.search_count = len(rows)
        self.update_search_count_label()

    def treeview_sort_column(self, col, descending):
        data = [(self.treeview.set(child, col), child) for child in self.treeview.get_children('')]
        data.sort(reverse=descending)
        for i, item in enumerate(data):
            self.treeview.move(item[1], '', i)
        self.treeview.heading(col, command=lambda: self.treeview_sort_column(col, not descending))

    def treeview_sort_resolution(self):
        items = [(self.treeview.set(child, "Resolution"), child) for child in self.treeview.get_children('')]
        items.sort(key=lambda x: int(re.search(r'\d+', x[0]).group()) if re.search(r'\d+', x[0]) else 0,
                   reverse=self.sort_descending)
        for i, (val, child) in enumerate(items):
            self.treeview.move(child, '', i)
        self.sort_descending = not self.sort_descending

    def treeview_sort_size(self):
        items = [(self.treeview.set(child, "Size"), child) for child in self.treeview.get_children('')]
        sizes = {"KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3, "TB": 1024 ** 4, "PB": 1024 ** 5, "EB": 1024 ** 6}

        # Modificação para evitar a conversão de 'N/A' em float
        def get_size_key(x):
            size_str = x[0]
            size_parts = size_str.split()
            if len(size_parts) == 2:
                size_value, size_unit = size_parts
                return float(size_value) * sizes.get(size_unit, -1)
            else:
                return -1  # Retorna -1 para 'N/A' ou tamanhos inválidos

        items.sort(key=get_size_key, reverse=self.sort_descending)

        for i, (val, child) in enumerate(items):
            self.treeview.move(child, '', i)
        self.sort_descending = not self.sort_descending

    def update_search_count_label(self):
        self.search_count_label.config(text=f"Records Found: {self.search_count}")

    def resize_columns(self):
        # Redimensionar colunas de acordo com as larguras atuais da Treeview
        for i, col in enumerate(self.treeview["columns"]):
            self.column_widths[i] = self.treeview.column(col, option="width")

    def show_context_menu(self, event):
        item = self.treeview.identify("item", event.x, event.y)
        if item:
            self.treeview.selection_set(item)  # Seleciona o item clicado com o botão direito
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Copy HASH", command=lambda: self.copy_hash(item))
            menu.add_command(label="Copy Name", command=lambda: self.copy_name(item))
            menu.add_command(label="Copy IMDB Tag", command=lambda: self.copy_imdb_tag(item))
            menu.add_command(label="Copy Magnet Link",
                             command=lambda: self.copy_magnet_link(item))  # Adicione esta linha
            menu.add_command(label="Open in QBitTorrent", command=lambda: self.open_in_qbittorrent(item))
            menu.post(event.x_root, event.y_root)

    def copy_imdb_tag(self, item):
        content = self.treeview.item(item, "values")[6]  # Get the value of the "IMDB Tag" column
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()

    def copy_hash(self, item):
        content = self.treeview.item(item, "values")[0]  # Get the value of the Hash column
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()  # This is necessary for it to work on some systems

    def copy_name(self, item):
        content = self.treeview.item(item, "values")[1]  # Get the value of the Title column
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update()

    def copy_magnet_link(self, item):
        torrent_hash = self.treeview.item(item, "values")[0]  # Get the value of the Hash column
        if torrent_hash:
            magnet_link = f"magnet:?xt=urn:btih:{torrent_hash}"
            self.root.clipboard_clear()
            self.root.clipboard_append(magnet_link)
            self.root.update()

    def format_size(self, size):
        if size is None:
            return "N/A"
        if size < 1024:
            return f"{int(size)} bytes"  # Remove as casas decimais
        elif size < 1024 ** 2:
            return f"{int(size / 1024)} KB"  # Remove as casas decimais
        elif size < 1024 ** 3:
            return f"{int(size / (1024 ** 2))} MB"  # Remove as casas decimais
        elif size < 1024 ** 4:
            return f"{size / (1024 ** 3):.2f} GB"
        elif size < 1024 ** 5:
            return f"{size / (1024 ** 4):.2f} TB"
        else:
            return "Too big"

    def extract_resolution(self, title):
        resolution_pattern = re.compile(r"(\d{3,4}p)")
        match = resolution_pattern.search(title)
        if match:
            return match.group(0)
        return ""

    def get_distinct_resolutions(self, rows):
        resolutions = set()
        for row in rows:
            title = row[2]
            resolution = self.extract_resolution(title)
            if resolution:
                resolutions.add(resolution)

        # Extrair e classificar apenas os números da resolução
        resolutions = sorted(list(resolutions),
                             key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0,
                             reverse=True)

        return resolutions

    def search_db(self):
        if self.db_connection:
            # Verificar se o usuário digitou algo antes de realizar a pesquisa
            search_input = self.name_field.get().strip()
            if not search_input:
                messagebox.showinfo("Empty Search", "Please enter a search query.")
                return

            self.load_db()
            self.update_search_count_label()

            # Verifique se nenhum resultado foi encontrado
            if self.search_count == 0:
                messagebox.showinfo("No Results", "No results found for the given search criteria.")

            # Restaure o filtro de resolução para "All" após cada pesquisa
            self.resolution_combo.set("All")
        else:
            messagebox.showerror("Error", "Database not connected.")

    def open_in_qbittorrent(self, event):
        selected_item = self.treeview.selection()
        if selected_item:
            torrent_hash = self.treeview.item(selected_item, "values")[0]  # Get the value of the Hash column
            if torrent_hash:
                qbittorrent_path = "C:/Program Files/qBittorrent/qbittorrent.exe"
                os.system(f'"{qbittorrent_path}" {torrent_hash}')

    def update_resolution_filter(self, event=None):
        selected_resolution = self.resolution_combo.get()
        search_input = self.name_field.get()
        search_field = self.search_field_var.get()
        search_words = search_input.split()

        if selected_resolution == "All":
            # Defina a cláusula de filtro de resolução vazia para carregar todos os resultados
            resolution_query = ""
        else:
            resolution_query = f"AND title LIKE '%{selected_resolution}%'"

        # Construa a consulta SQL com base na cláusula de filtro de resolução
        if search_field == "name":
            search_query = '%' + '%'.join(search_words) + '%'  # Construa o critério "LIKE" para o nome
            query = f"SELECT * FROM items WHERE title LIKE '{search_query}' {resolution_query}"
        elif search_field == "imdb tag":
            query = f"SELECT * FROM items WHERE imdb = '{search_input}' {resolution_query}"

        if self.db_connection:
            cursor = self.db_connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()

            self.treeview.delete(*self.treeview.get_children())

            for row in rows:
                id, hash, title, dt, cat, size, ext_id, imdb = row
                resolution = self.extract_resolution(title)
                size_str = self.format_size(size)
                imdb = "" if imdb is None else imdb
                self.treeview.insert("", "end", values=(hash, title, dt, cat, size_str, resolution, imdb))

            # Atualize a contagem e exiba-a
            self.search_count = len(rows)
            self.update_search_count_label()


if __name__ == "__main__":
    root = tk.Tk()
    root.state('zoomed')
    app = RarSeekerApp(root)
    root.mainloop()
