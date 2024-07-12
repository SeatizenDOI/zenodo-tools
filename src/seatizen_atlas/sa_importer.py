import datetime
import pandas as pd
from tqdm import tqdm
from pathlib import Path

from ..sql_connector.sc_base_dto import *
from ..sql_connector.sc_multilabel_dto import *
from ..sql_connector.sc_connector import SQLiteConnector

from ..zenodo_api.za_tokenless import get_all_versions_from_session_name

from ..utils.constants import TMP_PATH

from ..seatizen_session.ss_manager import SessionManager

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
            v = Version(doi=version["id"], deposit_doi=deposit.doi)
            v.insert()
        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_zipsize):
            print("\n[WARNING] Not enough doi to peuplate database")
            return
        
        # Iterate over frames.
        frame_version = Version(doi=filename_with_doi["METADATA.zip"], deposit_doi=deposit.doi)
        self.frames_importer(session, frame_version)


        if "PROCESSED_DATA_IA.zip" not in filename_with_doi:
            print("[WARNING] No IA folder found, cannot add predictions.")
            return
        
        # Iterate and add predictions
        prediction_version = Version(doi=filename_with_doi["PROCESSED_DATA_IA.zip"], deposit_doi=deposit.doi)
        self.multilabel_prediction_importer(session, prediction_version, frame_version)


    def frames_importer(self, session: SessionManager, frame_version: Version) -> None:
        print("\nfunc: Importing frames")
        metadata_csv = session.get_metadata_csv(indexingByFilename=True)
        framesManager = FrameManager() 

        # Get all frames already in database for a specific version to avoid duplicata.
        frame_in_database_for_specific_version = framesManager.get_all_frame_name_for_specific_version(frame_version.doi)
        
        useful_frame = session.get_useful_frames_path()
        if len(useful_frame) == 0:
            print("[WARNING] No useful frame to add in database.")
            return

        frame_to_add_in_database = list(set(useful_frame) - set(frame_in_database_for_specific_version))
        if len(frame_to_add_in_database) == 0:
            print("[WARNING] We already have all the frame for this specific version in database.")
            return
        
        for frame_name in tqdm(frame_to_add_in_database):
    
            row = metadata_csv.loc[frame_name]
            
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
        """ Method to import prediction multilabel. """
        print("\nfunc: Importing multilabel predictions")
        
        scores_csv = session.get_multilabel_csv(isScore=True, indexingByFilename=True)
        scores_csv_header = list(scores_csv)
        general_multilabel = GeneralMultilabelManager()
        frameManager = FrameManager()

        for frame_name in tqdm(session.get_useful_frames_path()):
            frame_id = frameManager.get_frame_id_from_filename(frame_name, frame_version.doi)
            if frame_id == -1: continue # No frames found
            
            # Manual check to avoid add duplicate data.
            predictions_number = general_multilabel.get_number_of_predictions_for_specific_version(prediction_version.doi, frame_id)
            if predictions_number == len(scores_csv_header): continue
            elif predictions_number > 0 and predictions_number < len(scores_csv_header):
                print(f"[WARNING] Frame {frame_name} doesn't have the correct number of predictions in database. It's an error please fix.")
                continue

            row = scores_csv.loc[frame_name]
            
            for cls in scores_csv_header:
                
                class_id = general_multilabel.classIdMapByClassName.get(cls, None)
                if class_id == None: continue

                general_multilabel.append(MultilabelPrediction(
                    score=row[cls],
                    frame_id=frame_id,
                    ml_class_id=class_id,
                    version_doi=prediction_version.doi
                ))
        general_multilabel.insert_predictions()
    

    def multilabel_annotation_importer(self, annotation_file: Path) -> None:
        """ Method to import multilabel annotation. """
        print(f"\n\nfunc: Multilabel annotation importer with {annotation_file}")
        if not Path.exists(annotation_file) or not annotation_file.is_file() or annotation_file.suffix.lower() != ".csv": return


        # Extract datetime, dataset_name and author from filename.
        annotation_date, dataset_name, author_name = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", ""
        try:
            splitting_name = annotation_file.name.split("__")
            annotation_date = datetime.datetime.strptime(splitting_name[0], "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            dataset_name = splitting_name[2].replace("_labels.csv", "")
            author_name = splitting_name[1]
        except Exception:
            print("Cannot get datetime. Please start your file name like date_time__author-name__dataset-name__")

        # Read annotations from csv file.
        try:
            df_annotation = pd.read_csv(annotation_file)
        except Exception:
            print(f"[WARNING] Cannot open {annotation_file} when loading multilabel annotation.")
            return


        general_multilabel = GeneralMultilabelManager()
        ml_annotation_session = MultilabelAnnotationSession(annotation_date=annotation_date, author_name=author_name, dataset_name=dataset_name, id=None)
        
        id_annotation_session = general_multilabel.insert_annotations_session(ml_annotation_session)
        if id_annotation_session == -1:
            print("This annotation session is already in database.")
            return

        cpt_error = 0
        # Iter on all annotation and insert in database.
        for _, row in tqdm(df_annotation.iterrows(), total=len(df_annotation)):
            
            # Check if we have frame in database.
            frame_id = general_multilabel.get_frame_id_from_frame_name(row["FileName"])
            if frame_id == None:
                cpt_error += 1
                continue
            
            for label_name in list(df_annotation):
                
                # Check if label exist.
                label_id = general_multilabel.labelIdMapByLabelName.get(label_name, None)
                if label_id == None: continue
                
                general_multilabel.append(MultilabelAnnotation(
                    value=row[label_name],
                    frame_id=frame_id,
                    ml_label_id=label_id,
                    ml_annotation_session_id=id_annotation_session
                ))

        print(f"{len(df_annotation) - cpt_error}/{len(df_annotation)} images, traduct by {general_multilabel.annotations_size} annotations load in database.")
        if general_multilabel.annotations_size == 0:
            general_multilabel.drop_annotation_session(id_annotation_session)
        else:
            general_multilabel.insert_annotations()
