import sqlite3
import traceback
from pathlib import Path
from ..utils.constants import SQL_FILE

class SQLiteConnector:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
            cls._instance._connection = None
        return cls._instance


    def connect(self, sqlite_filepath):
        """ Establishes connection with database """
        try:
            self._connection = sqlite3.connect(sqlite_filepath, check_same_thread=False)
            self._connection.enable_load_extension(True)
            self._connection.execute('SELECT load_extension("mod_spatialite")')
            self._connection.execute('PRAGMA threading_mode = "MULTI-THREAD"')

        except sqlite3.Error:
            print(traceback.format_exc())
            print(f"Cannot connect to {sqlite_filepath}")


    def _query(self, query, params):
        if self._connection is None:
            print("Error: database connection not established")
            return None
        
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        
        return results


    def _execute(self, query, params):
        if self._connection is None:
            print("Error: database connection not established")
            return None
        
        cursor = self._connection.cursor()
        cursor.execute(query, params)
        self._connection.commit()
        cursor.close()
    
    def _executemany(self, query, params):
        if self._connection is None:
            print("Error: database connection not established")
            return None
        
        cursor = self._connection.cursor()
        cursor.executemany(query, params)
        self._connection.commit()
        cursor.close()
    

    def execute_query(self, query: str, params=None):
        """ Perform custom query. """
        
        if params is None:
            params = []
        if query.strip().lower().startswith('select') or query.strip().lower().startswith('with'):
            return self._query(query, params)
        else:
            if isinstance(params, tuple) or len(params) == 0:
                self._execute(query, params)
            else:
                self._executemany(query, params)
            return None
    
    def generate(self, sqlite_filepath: Path):
        """ Regenerate gpkg file. """

        self.connect(sqlite_filepath)
        
        if not Path.exists(Path(SQL_FILE)):
            raise NameError(f"File {SQL_FILE} not found")

        # Lire le contenu du fichier SQL
        with open(SQL_FILE, 'r') as file:
            sql_script = file.read()

        # Exécuter le script SQL
        self._connection.execute('PRAGMA application_id = 0x47504B47;')  # GP = GeoPackage in hex
        self._connection.execute('PRAGMA user_version = 10300;')  # GeoPackage version 1.3
        self._connection.executescript(sql_script)
    
    def close(self):
        if self._connection is not None:
            self._connection.close()
            SQLiteConnector._instance = None