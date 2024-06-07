from pathlib import Path

from ..sql_connector.connector import SQLiteConnector

class AtlasImport:

    def __init__(self, seatizen_atlas_gpkg: Path):

        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        
        # SQL Connector.
        self.sql_connector = SQLiteConnector()


    def import_seatizen_session(self, session_path: Path):

        if not Path.exists(session_path) or not session_path.is_dir():
            print("[ERROR] Session not found in importer. ")
        
        
        # Zip actual frames folder without useless file to get md5 sum.

        # Zip metadata