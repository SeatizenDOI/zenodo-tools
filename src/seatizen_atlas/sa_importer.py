import datetime
from tqdm import tqdm
from pathlib import Path

from ..sql_connector.sc_connector import SQLiteConnector
from ..sql_connector.sc_base_dto import *
from ..sql_connector.sc_multilabel_dto import *

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
        session.prepare_processed_data(folders_to_compare, needFrames=False)
        filename_with_zipsize = session.get_bit_size_zip_folder()
        session.cleanup()

        
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
        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_zipsize):
            raise NameError("Not enough doi to peuplate database")

        # Iterate over frames.
        frame_version = Version(doi=filename_with_doi["METADATA.zip"], deposit_doi=deposit.doi)
        self.frames_importer(session, frame_version)

        # Iterate and add predictions
        prediction_version = Version(doi=filename_with_doi["PROCESSED_DATA_IA.zip"], deposit_doi=deposit.doi)
        self.multilabel_prediction_importer(session, prediction_version, frame_version)

    def frames_importer(self, session: SessionManager, frame_version: Version) -> None:
        print("\nImporting frames")
        metadata_csv = session.get_metadata_csv()
        framesManager = FrameManager() 
        
        for frame_name in tqdm(session.get_useful_frames_path()):
            
            row = metadata_csv[metadata_csv["FileName"] == frame_name].iloc[0]
            
            # Datetime formatting
            creation_date = ""
            if "SubSecDateTimeOriginal" not in row:
                creation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                date, time = row["SubSecDateTimeOriginal"].split(".")[0].split(" ")
                date = date.replace(":", "-")
                creation_date = date + " " + time


            frame = Frame(
                version_doi = frame_version.doi,
                filename = frame_name,
                original_filename = frame_name if "OriginalFileName" not in row else row["OriginalFileName"],
                gps_latitude = None if "GPSLatitude" not in row else row["GPSLatitude"],
                gps_longitude = None if "GPSLongitude" not in row else row["GPSLongitude"],
                gps_altitude = None if "GPSAltitude" not in row else row["GPSAltitude"],
                gps_pitch = None if "GPSPitch" not in row else row["GPSPitch"],
                gps_roll = None if "GPSRoll" not in row else row["GPSRoll"],
                gps_track = None if "GPSTrack" not in row else row["GPSTrack"],
                gps_datetime =  creation_date,
                relative_path = row["relative_file_path"]
            )
            framesManager.append(frame)
        framesManager.insert()
    
    def multilabel_prediction_importer(self, session: SessionManager, prediction_version: Version, frame_version: Version) -> None:
        print("\nImporting predictions")
        scores_csv = session.get_multilabel_csv(isScore=True)
        scores_csv_header = list(scores_csv)
        general_multilabel = GeneralMultilabelManager()
        frameManager = FrameManager()

        for _ , row in tqdm(scores_csv.iterrows(), total=len(scores_csv)):
            frame_id = frameManager.get_frame_id_from_filename(row["FileName"], frame_version.doi)
            if frame_id == -1: continue # No frames found

            
            for cls in scores_csv_header:
                
                class_id = general_multilabel.classIdMapByClassName.get(cls, None)
                if class_id == None: continue

                general_multilabel.append(MultilabelPrediction(
                    score=row[cls],
                    frame_id=frame_id,
                    prediction_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    multilabel_class_id=class_id,
                    version_doi=prediction_version.doi
                ))


        general_multilabel.insert_predictions()
