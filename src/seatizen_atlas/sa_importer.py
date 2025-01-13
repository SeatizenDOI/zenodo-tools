import pandas as pd
from tqdm import tqdm
from pathlib import Path
from datetime import datetime, timedelta

from ..models.base_model import DataStatus
from ..models.frame_model import FrameDAO, FrameDTO
from ..models.ml_label_model import MultilabelLabelDAO
from ..models.ml_model_model import MultilabelModelDAO, MultilabelClassDAO
from ..models.deposit_model import DepositDAO, VersionDAO, DepositDTO, VersionDTO, DepositLinestringDAO, DepositLinestringDTO
from ..models.ml_predictions_model import MultilabelPredictionDAO, MultilabelPredictionDTO
from ..models.ml_annotation_model import MultilabelAnnotationDAO, MultilabelAnnotationSessionDAO, MultilabelAnnotationSessionDTO, MultilabelAnnotationDTO

from ..sql_connector.sc_connector import SQLiteConnector

from ..zenodo_api.za_tokenless import get_all_versions_from_session_name

from ..utils.constants import TMP_PATH, MULTILABEL_MODEL_NAME

from ..seatizen_session.ss_manager import SessionManager

class AtlasImport:

    def __init__(self, seatizen_atlas_gpkg: Path) -> None:

        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        
        # SQL Connector.
        self.sql_connector = SQLiteConnector()

        # Manager.
        self.deposit_manager = DepositDAO()
        self.deposit_linestring_manager = DepositLinestringDAO()
        self.version_manager = VersionDAO()
        self.frame_manager = FrameDAO()
        self.prediction_manager = MultilabelPredictionDAO()
        self.ml_classes_manager = MultilabelClassDAO()
        self.ml_anno_ses_manager = MultilabelAnnotationSessionDAO()
        self.ml_anno_manager = MultilabelAnnotationDAO()
        self.ml_label_manager = MultilabelLabelDAO()
        self.ml_model_manager = MultilabelModelDAO()


    def import_seatizen_session(self, session_path: Path, force_frames_insertion: bool) -> None: # TODO Add choices by parameters
        if not Path.exists(session_path) or not session_path.is_dir():
            print("[ERROR] Session not found in importer. ")
        
        # Get all versions for a session_name.
        versions = get_all_versions_from_session_name(session_path.name)
        if len(versions) == 0:
            raise NameError("No associated version on zenodo.")

        # Get zip size for frames and predictions.
        folders_to_compare = ["PROCESSED_DATA/IA", "METADATA"]
        session = SessionManager(session_path, TMP_PATH)
        session.prepare_processed_data(folders_to_compare, needFrames=False, with_file_at_root_folder=False)
        filename_with_zipsize = session.get_bit_size_zip_folder()
        session.cleanup()

        # Found doi for frames and predictions.
        filename_with_doi = {}
        have_raw_data, have_processed_data = False, False
        for version in sorted(versions, key=lambda d: d["id"]): # Order by id to always get the last version doi.
            if version["metadata"]["version"].replace(" ", "_").upper() == "PROCESSED_DATA":
                have_processed_data = True

            if version["metadata"]["version"].replace(" ", "_").upper() == "RAW_DATA":
                have_raw_data = True

            for file in version["files"]:
                if file["key"] in filename_with_zipsize and \
                   (filename_with_zipsize[file["key"]] == file["size"] or \
                   abs(filename_with_zipsize[file["key"]] - file["size"]) < 1000):
                    filename_with_doi[file["key"]] = version["id"]
        
        # Create or update deposit
        footprint_polygon, footprint_linestring = session.get_footprint()
        deposit = DepositDTO(doi=versions[0]["conceptrecid"], 
                          session_name=session_path.name, 
                          footprint=footprint_polygon,
                          have_raw_data=have_raw_data, 
                          have_processed_data=have_processed_data
                        )
        
        self.deposit_manager.insert(deposit)

        deposit_linestring = DepositLinestringDTO(deposit=deposit, footprint_linestring=footprint_linestring)
        self.deposit_linestring_manager.insert(deposit_linestring)

        # Insert versions
        for v in versions:
            # Do not insert version different from processed_data and raw_data
            if v["metadata"]["version"].upper().replace(" ", "_") not in ["PROCESSED_DATA", "RAW_DATA"]: continue
            self.version_manager.insert(VersionDTO(doi=v["id"], deposit=deposit))

        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_zipsize):
            print("\n[WARNING] Not enough doi to peuplate database")
            return
        
        # Iterate over frames.
        frame_version = VersionDTO(doi=filename_with_doi["METADATA.zip"], deposit=deposit)
        self.frames_importer(session, frame_version, force_frames_insertion)


        if "PROCESSED_DATA_IA.zip" not in filename_with_doi:
            print("[WARNING] No IA folder found, cannot add predictions.")
            return
        
        # Iterate and add predictions
        prediction_version = VersionDTO(
            doi=filename_with_doi["PROCESSED_DATA_IA.zip"],
            deposit=deposit
        )
        self.multilabel_prediction_importer(session, prediction_version, frame_version)


    def frames_importer(self, session: SessionManager, frame_version: VersionDTO, force_frames_insertion: bool) -> None:
        print("\nfunc: Importing frames")
        metadata_csv = session.get_metadata_csv(indexingByFilename=True)

        # Get all frames already in database for a specific version to avoid duplicata.
        frame_in_db_for_specific_version = self.frame_manager.get_frames_by_version(frame_version)

        # Get frame name
        frame_name_in_db = [f.filename for f in frame_in_db_for_specific_version]
        
        useful_frame = []
        if force_frames_insertion:
            useful_frame = list(metadata_csv.index) # Get all filename instead of finding the useful one.
        else:
            useful_frame = session.get_useful_frames_name()
            if len(useful_frame) == 0:
                print("[WARNING] No useful frame to add in database.")
                return

        frame_name_to_add_in_database = list(set(useful_frame) - set(frame_name_in_db))
        if len(frame_name_to_add_in_database) == 0:
            print("[WARNING] We already have all the frame for this specific version in database.")
            return
        
        frame_obj_to_add = []
        for frame_name in tqdm(frame_name_to_add_in_database):
    
            row = metadata_csv.loc[frame_name]
            
            original_filename = frame_name if "OriginalFileName" not in row else row["OriginalFileName"]
            # Check if session_name in frame_name, else add it.
            if session.session_name not in frame_name:
                frame_name = f"{session.session_name}_{frame_name}"

            # Datetime formatting
            creation_date = ""
            if "SubSecDateTimeOriginal" in row and "1970" not in row["SubSecDateTimeOriginal"].split(".")[0]: # Plancha with correct datetime
                date, time = row["SubSecDateTimeOriginal"].split(".")[0].split(" ")
                date = date.replace(":", "-")
                creation_date = date + " " + time
            elif "DateTimeOriginal" in row: # UAV
                date, time = row["DateTimeOriginal"].split(" ")
                date = date.replace(":", "-")
                creation_date = date + " " + time
            elif "GPSDateTime" in row: # 2015 Scuba diving
                date, time = row["GPSDateTime"].replace("Z", "").split(".")[0].split(" ")
                date = date.replace(":", "-")
                creation_date = date + " " + time
            elif "SubSecDateTimeOriginal" in row and "1970" in row["SubSecDateTimeOriginal"].split(".")[0]: # Plancha with 1970 as year replace with session date and add 12.
                _, time = row["SubSecDateTimeOriginal"].split(".")[0].split(" ")
                time = (datetime.strptime(time, "%H:%M:%S") + timedelta(hours=12)).strftime("%H:%M:%S")
                creation_date = session.date + " " + time
            else:
                creation_date = None

            frame = FrameDTO(
                version = frame_version,
                filename = frame_name,
                original_filename = original_filename,
                gps_latitude = None if "GPSLatitude" not in row else row["GPSLatitude"],
                gps_longitude = None if "GPSLongitude" not in row else row["GPSLongitude"],
                gps_altitude = None if "GPSAltitude" not in row else row["GPSAltitude"],
                gps_pitch = None if "GPSPitch" not in row else row["GPSPitch"],
                gps_roll = None if "GPSRoll" not in row else row["GPSRoll"],
                gps_track = None if "GPSTrack" not in row else row["GPSTrack"],
                gps_fix = None if "GPSfix" not in row else row["GPSfix"],
                gps_datetime =  creation_date,
                relative_path = None if "relative_file_path" not in row else row["relative_file_path"]
            )
            frame_obj_to_add.append(frame)
        self.frame_manager.insert(frame_obj_to_add)


    def multilabel_prediction_importer(self, session: SessionManager, pred_v: VersionDTO, 
                                       f_ver: VersionDTO) -> None:
        """ Method to import prediction multilabel. """
        print("\nfunc: Importing multilabel predictions")
        
        scores_csv = session.get_multilabel_csv(isScore=True, indexingByFilename=True)
        scores_csv_header = list(scores_csv)

        ml_model = self.ml_model_manager.get_model_by_name(MULTILABEL_MODEL_NAME)

        predictions_obj_to_add = []
        for frame_name in tqdm(session.get_useful_frames_name()):
            frame = self.frame_manager.get_frame_by_filename_and_version(frame_name, f_ver)

            # Manual check to avoid add duplicate data.
            preds = self.prediction_manager.get_pred_by_frame_version(pred_v, frame)
            if len(preds) == len(scores_csv_header): continue
            elif len(preds) > 0 and len(preds) < len(scores_csv_header):
                print(f"""[WARNING] Frame {frame_name} doesn't have the correct number of predictions in database. 
                        It's an error please fix.""")
                continue

            row = scores_csv.loc[frame_name]
            
            for cls_name in scores_csv_header:
                
                ml_class = self.ml_classes_manager.get_class_by_name_and_model(cls_name, ml_model)

                predictions_obj_to_add.append(MultilabelPredictionDTO(
                    score=row[cls_name],
                    frame=frame,
                    ml_class=ml_class,
                    version=pred_v
                ))
        self.prediction_manager.insert(predictions_obj_to_add)
    

    def multilabel_annotation_importer(self, annotation_file: Path) -> None:
        """ Method to import multilabel annotation. """
        print(f"\n\nfunc: Multilabel annotation importer with {annotation_file}")
        if not Path.exists(annotation_file) or not annotation_file.is_file() or annotation_file.suffix.lower() != ".csv": return


        # Extract datetime, dataset_name and author from filename.
        annotation_date, dataset_name, author_name = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "", ""
        try:
            splitting_name = annotation_file.name.split("__")
            annotation_date = datetime.strptime(splitting_name[0], "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            dataset_name = splitting_name[2].replace("_labels.csv", "").replace(".csv", "")
            author_name = splitting_name[1]
        except Exception:
            print("Cannot get datetime. Please start your file name like date_time__author-name__dataset-name__")

        # Read annotations from csv file.
        try:
            df_annotation = pd.read_csv(annotation_file)
        except Exception:
            print(f"[WARNING] Cannot open {annotation_file} when loading multilabel annotation.")
            return


        ml_annotation_session = MultilabelAnnotationSessionDTO(
            annotation_date=annotation_date, 
            author_name=author_name, 
            dataset_name=dataset_name, 
            id=None
        )
        
        annotation_session = self.ml_anno_ses_manager.insert_and_get_id(ml_annotation_session)
        if isinstance(annotation_session, DataStatus) and annotation_session == DataStatus.ALREADY:
            print("This annotation session is already in database.")
            return
        elif isinstance(annotation_session, DataStatus) and annotation_session == DataStatus.NO_DATA:
            print("[ERROR] Cannot insert annotation_session.")

        cpt_error, annotations_obj_to_add, label_not_found = 0, [], []
        # Iter on all annotation and insert in database.
        for _, row in tqdm(df_annotation.iterrows(), total=len(df_annotation)):
            
            # Check if we have frame in database.
            try:
                frame = self.frame_manager.get_frame_by_filename(row["FileName"])
            except NameError:
                cpt_error += 1
                continue
            
            for label_name in list(df_annotation):
                
                # Check if label exist.
                try:
                    label = self.ml_label_manager.get_label_by_name(label_name)
                except NameError:
                    if label_name not in label_not_found:
                        label_not_found.append(label_name)
                    continue

                annotations_obj_to_add.append(MultilabelAnnotationDTO(
                    value=row[label_name],
                    frame=frame,
                    ml_label=label,
                    ml_annotation_session=annotation_session
                ))
        if len(label_not_found) != 0:
            print(f"[WARNING] This label weren't in database : {', '.join(label_not_found)}")

        print(f"""{len(df_annotation) - cpt_error}/{len(df_annotation)} images, traduct by {len(annotations_obj_to_add)} annotations load in database.""")
        
        if len(annotations_obj_to_add) == 0:
            self.ml_anno_ses_manager.drop_annotation_session(annotation_session)
        else:
            self.ml_anno_manager.insert(annotations_obj_to_add)
