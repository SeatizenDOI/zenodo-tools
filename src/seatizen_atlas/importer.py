import shutil
import zipfile
from pathlib import Path

from ..sql_connector.connector import SQLiteConnector
from ..sql_connector.database_dto import *

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

        # Get zip size for frames and predictions.
        folders_to_compare = ["PROCESSED_DATA/IA", "METADATA"]
        session = SessionManager(session_path, TMP_PATH)
        # session.prepare_processed_data(folders_to_compare, needFrames=True)
        filename_with_md5 = session.get_bit_size_zip_folder()
        # session.cleanup()

        # Found doi for frames and predictions.
        filename_with_doi = {}
        for version in versions:
            for file in version["files"]:
                if file["key"] in filename_with_md5 and filename_with_md5[file["key"]] == file["size"]:
                    filename_with_doi[file["key"]] = version["id"]
        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_md5):
            raise NameError("Not enough doi to peuplate database")
        

        # Create or update deposit
        deposit = Deposit(doi=versions[0]["conceptrecid"], session_name=session_path.name, footprint=session.get_footprint())
        deposit.insert()
        return
        # Update frames.
        frame_doi = ""

        metadata = session.get_metadata()

        frame_doi = filename_with_doi["PROCESSED"]
        for filename in filename_with_doi:
            version = Version(doi=filename_with_doi[filename], deposit_doi=deposit.doi)
            version.insert()