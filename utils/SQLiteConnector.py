import sqlite3
import traceback
from pathlib import Path
from .constants import SQL_FILE

class SQLiteConnector:

    def __init__(self, sqlite_filepath):

        self.sqlite_filepath = sqlite_filepath
        
        self.con, self.cur = None, None

        self.setup()
    
    def setup(self):
        try:
            self.con = sqlite3.connect(self.sqlite_filepath)
            self.con.enable_load_extension(True)
            self.con.execute('SELECT load_extension("mod_spatialite")')
            self.cur = self.con.cursor()
        except sqlite3.Error:
            print(f"Cannot connect to {self.sqlite_filepath}")


    def get_all_deposit(self):
        deposit = []
        try:
            res = self.cur.execute("SELECT * FROM deposit")
            deposit = res.fetchall()
            print(deposit)

        except sqlite3.Error:
            print(traceback.format_exc(), end="\n\n")

        return deposit
    
    def insert_deposit(self):
        data = [
            (1, "test"),
            (2, "test"),
            (3, "test"),
        ]
        self.cur.executemany("INSERT INTO deposit VALUES(?, ?)", data)
        self.con.commit()  # Remember to commit the transaction after executing INSERT.
    
    def generate(self):
        """ Regenerate gpkg file. """

        self.setup()
        
        if not Path.exists(Path(SQL_FILE)):
            raise NameError(f"File {SQL_FILE} not found")

        # Lire le contenu du fichier SQL
        with open(SQL_FILE, 'r') as file:
            sql_script = file.read()

        # Exécuter le script SQL
        self.con.executescript(sql_script)
    
    def close(self):
        self.con.close()