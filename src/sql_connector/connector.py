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
            self._connection = sqlite3.connect(sqlite_filepath)
            self._connection.enable_load_extension(True)    
            self._connection.execute('SELECT load_extension("mod_spatialite")')
            # Enable spatial features
            self._connection.execute('PRAGMA application_id = 0x47504B47;')  # GP = GeoPackage in hex
            self._connection.execute('PRAGMA user_version = 10300;')  # GeoPackage version 1.3
        except sqlite3.Error:
            print(traceback.format_exc())
            print(f"Cannot connect to {sqlite_filepath}")


    def create(self, query, params=None):
        """ Add data in database """
        if params is None:
            params = []
        self._execute(query, params)


    def read(self, query, params=None):
        if params is None:
            params = []
        return self._query(query, params)


    def update(self, query, params=None):
        if params is None:
            params = []
        self._execute(query, params)


    def delete(self, query, params=None):
        if params is None:
            params = []
        self._execute(query, params)


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
    

    def execute_query(self, query, params=None):
        """ Perform custom query. """
        
        if params is None:
            params = []
        if query.strip().lower().startswith('select'):
            return self._query(query, params)
        else:
            self._execute(query, params)
            return None
    
    def generate(self, sqlite_filepath):
        """ Regenerate gpkg file. """

        self.connect(sqlite_filepath)
        
        if not Path.exists(Path(SQL_FILE)):
            raise NameError(f"File {SQL_FILE} not found")

        # Lire le contenu du fichier SQL
        with open(SQL_FILE, 'r') as file:
            sql_script = file.read()

        # Exécuter le script SQL
        self._connection.executescript(sql_script)
    
    def close(self):
        if self._connection is not None:
            self._connection.close()
            SQLiteConnector._instance = None