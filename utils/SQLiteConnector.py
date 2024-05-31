import sqlite3
import traceback
from pathlib import Path

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
    
    def generate(self, sql_path):
        """ Regenerate gpkg file. """

        if Path.exists(self.sqlite_filepath) and self.sqlite_filepath.is_file():
            self.sqlite_filepath.unlink()
            self.setup()
        
        if not Path.exists(sql_path):
            raise NameError(f"File {sql_path} not found")

        # Lire le contenu du fichier SQL
        with open(sql_path, 'r') as file:
            sql_script = file.read()

        # Exécuter le script SQL
        self.con.executescript(sql_script)
    
    def close(self):
        self.con.close()

def main():
    
    sql_path = Path("sqllite/test.gpkg")

    sqlconnector = SQLiteConnector(sql_path)

    try:
        sqlconnector.generate()
        sqlconnector.get_all_deposit()
    except :
        print(traceback.format_exc(), end="\n\n")
    finally:
        sqlconnector.close() # Always close