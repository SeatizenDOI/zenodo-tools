from pathlib import Path

from ..sql_connector.connector import SQLiteConnector
from ..sql_connector.database_dto import *

from ..zenodo_api.za_tokenless import get_all_versions_from_session_name

from ..seatizen_session.ss_manager import SessionManager
from ..utils.constants import TMP_PATH

class AtlasImport:

    def __init__(self, seatizen_atlas_gpkg: Path) -> None:

        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        
        # SQL Connector.
        self.sql_connector = SQLiteConnector()


    def import_seatizen_session(self, session_path: Path) -> None: # TODO Add choices by parameters

        if not Path.exists(session_path) or not session_path.is_dir():
            print("[ERROR] Session not found in importer. ")
        
        # Get all versions for a session_name.
        versions = get_all_versions_from_session_name(session_path.name)
        if len(versions) == 0:
            raise NameError("No associated version on zenodo.")

        # Get zip size for frames and predictions.
        folders_to_compare = ["PROCESSED_DATA/IA", "METADATA"]
        session = SessionManager(session_path, TMP_PATH)
        session.prepare_processed_data(folders_to_compare, needFrames=True)
        filename_with_zipsize = session.get_bit_size_zip_folder()
        # session.cleanup()

        # Found doi for frames and predictions.
        filename_with_doi = {}
        have_raw_data, have_processed_data = False, False
        for version in versions:
            
            if version["metadata"]["version"].replace(" ", "_").upper() == "PROCESSED_DATA":
                have_processed_data = True

            if version["metadata"]["version"].replace(" ", "_").upper() == "RAW_DATA":
                have_raw_data = True

            for file in version["files"]:
                if file["key"] in filename_with_zipsize and filename_with_zipsize[file["key"]] == file["size"]:
                    filename_with_doi[file["key"]] = version["id"]
        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_zipsize):
            raise NameError("Not enough doi to peuplate database")

        # Create or update deposit
        deposit = Deposit(doi=versions[0]["conceptrecid"], 
                          session_name=session_path.name, 
                          footprint=session.get_footprint(), 
                          have_raw_data=have_raw_data, 
                          have_processed_data=have_processed_data
                        )
        deposit.insert()

        # Insert versions
        for version in versions:
            v = Version(doi=version["doi"], deposit_doi=deposit.doi)
            v.insert()
        
        # Return if we don't need to add frames or multilabel predictions

        # Update frames.
        try:
            frame_key = list(set(list(filename_with_doi)) - set([f'{a.replace("/", "_")}.zip' for a in folders_to_compare]))[0]
        except Exception:
            print("Frame key not found")

        metadata_csv = session.get_metadata_csv()
        predictions_gps = session.get_predictions_gps()
        frame_doi = filename_with_doi[frame_key]
        version = Version(doi=frame_doi, deposit_doi=deposit.doi)