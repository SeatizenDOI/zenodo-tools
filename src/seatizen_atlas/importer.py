from pathlib import Path

from ..sql_connector.connector import SQLiteConnector

from ..zenodo_api.tokenless import get_all_versions_from_session_name
from ..seatizen_session.manager import SessionManager
from ..utils.constants import TMP_PATH

class AtlasImport:

    def __init__(self, seatizen_atlas_gpkg: Path):

        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        
        # SQL Connector.
        self.sql_connector = SQLiteConnector()


    def import_seatizen_session(self, session_path: Path):

        if not Path.exists(session_path) or not session_path.is_dir():
            print("[ERROR] Session not found in importer. ")
        
        # Get all versions for a session_name.
        versions = get_all_versions_from_session_name(session_path.name)
        if len(versions) == 0:
            raise NameError("No associated version on zenodo.")

        # Get checksum for frames and predictions.
        session = SessionManager(session_path, TMP_PATH)
        session.prepare_processed_data(["PROCESSED_DATA/IA", "METADATA"], needFrames=True)
        filename_with_md5 = session.get_md5_checksum_zip_folder()
        session.cleanup()

        # Found doi for frames and predictions.
        for version in versions:
            for file in version["files"]:
                if file["key"] in filename_with_md5 and filename_with_md5[file["key"]] == file["checksum"].replace("md5:", ""):
                    print(file["key"], version["id"])
        
        # for metadata and ia, we may be need to download zip files to check file md5sum because 
        # the way file are compressed, the zip file md5sum change between hardisk 