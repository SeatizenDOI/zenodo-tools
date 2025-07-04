import os
import json
import shutil
import pycountry
import pandas as pd
pd.set_option("display.precision", 12)
from tqdm import tqdm
from enum import Enum
from pathlib import Path
from datetime import datetime
from natsort import natsorted
from abc import ABC, abstractmethod
from scipy.spatial import ConvexHull
from zipfile import ZipFile, ZIP_DEFLATED
from shapely.geometry import LineString, Polygon

from pygeometa.core import read_mcf, validate_mcf
from pygeometa.schemas.iso19139_2 import ISO19139_2OutputSchema 

from ..ss_zipper import SessionZipper
from ...utils.lib_tools import compute_duration_iso8601
from ...utils.constants import MAXIMAL_DEPOSIT_FILE_SIZE, IMG_EXTENSION, BYTE_TO_GIGA_BYTE, MULTILABEL_MODEL_NAME, JACQUES_MODEL_NAME

class BaseType(Enum):
    RGP = "RGP Station from IGN"
    REACH_RS2 = "Emlid Reach RS2+"
    REACH_RS3 = "Emlid Reach RS3"
    NONE = "No Base"

class DCIMType(Enum):
    NONE = "Nothing"
    VIDEO = "MP4 files"
    IMAGE = "JPG files"

class BaseSessionManager(ABC):

    def __init__(self, session_path: str, temp_folder: str) -> None:
        # Basics path.
        self.session_path = Path(session_path)
        self.session_name = self.session_path.name

        # Create tmp folder.
        self.temp_folder = Path(temp_folder, self.session_name)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        
        # Compute informations.
        self.place, self.date, self.country, self.platform = "", "", "", ""
        self.mission_start_str, self.mission_stop_str = "", ""
        
        self.compute_basics_info()

    @abstractmethod
    def get_raw_access_right(self) -> str: # TODO Better tipying with enum
        """ Access right to raw data. """
        pass

    @abstractmethod
    def get_processed_access_right(self) -> str:
        """ Access right to processed data. """
        pass

    @abstractmethod
    def build_raw_description(self) -> str:
        """ Description for raw data. """
        pass

    @abstractmethod
    def build_processed_description(self) -> str:
        """ Description for processed data. """
        pass

    @abstractmethod
    def zip_raw_data(self) -> None:
        """ Folder to zip for raw data. """
        pass

    @abstractmethod
    def get_restricted_files_on_zenodo(self) -> list[str]:
        """ Restricted files to not propagate in PROCESSED_DATA version"""
        pass

    @abstractmethod
    def set_start_stop_mission_str(self) -> None:
        """ Set mission start and stop as str in format %Y:%m:%d %H:%M:%S. """
        pass
    
    # !WARNING mission_start_str and mission_stop_str can be not set (metadata file not found) but no error is raised. 
    # !If you call this property, you will get an error but that was a choice.
    @property
    def mission_start_date(self) -> datetime:
        return datetime.strptime(self.mission_start_str, "%Y:%m:%d %H:%M:%S")
    
    @property
    def mission_stop_date(self) -> datetime:
        return datetime.strptime(self.mission_stop_str, "%Y:%m:%d %H:%M:%S")
    

    def prepare_raw_data(self) -> list[Path]:
        """ Zip all file in a tmp folder. """
        self.cleanup()
        print("-- Prepare raw data... ")
        
        self.zip_raw_data()
        
        print("-- Sort and move to sub folder if needed... ")
        return self.move_into_subfolder_if_needed()
        
    
    def prepare_processed_data(self, processed_folder: list, needFrames: bool = False, with_file_at_root_folder: bool = False) -> None:
        """ Zip all processed data in tmp folder. """
        self.cleanup()
        print("-- Prepare processed data... ")

        for folder in processed_folder:
            self._zip_folder(folder)

        if needFrames:
            self._zip_processed_frames()

        # Copy all file in root session like pdf or other file.
        if with_file_at_root_folder:
            for file in self.session_path.iterdir(): # TODO better filter ? may be on pdf
                if file.is_file():
                    shutil.copy(file, Path(self.temp_folder, file.name))
        
        # Check if tmp folder is > MAX_SIZE_FILE_DEPOSIT to avoid error
        size_gb = round(sum([os.stat(file).st_size for file in self.temp_folder.iterdir()]) / BYTE_TO_GIGA_BYTE, 6)
        if size_gb > MAXIMAL_DEPOSIT_FILE_SIZE:
            raise NameError("The sum total of processed data file sizes is greater than the Zenodo limit.")


    def prepare_custom_data(self, folder_to_zip: list) -> None:
        """ Zip all processed data in tmp folder. """
        self.cleanup()
        print("-- Prepare custom data... ")

        for folder in folder_to_zip:
            self._zip_folder(folder)

        # Check if tmp folder is > MAX_SIZE_FILE_DEPOSIT to avoid error
        size_gb = round(sum([os.stat(file).st_size for file in self.temp_folder.iterdir()]) / BYTE_TO_GIGA_BYTE, 6)
        if size_gb > MAXIMAL_DEPOSIT_FILE_SIZE:
            raise NameError("The sum total of processed data file sizes is greater than the Zenodo limit.")


    def _zip_folder(self, folder_to_zip: str)-> None:
        """ Zip all file in folder. """
        zip_folder = Path(self.temp_folder, folder_to_zip.replace("/", "_"))
        raw_folder = Path(self.session_path, folder_to_zip)
        
        if not Path.exists(raw_folder) or not raw_folder.is_dir() or not len(list(raw_folder.iterdir())) > 0:
            print(f"[WARNING] {folder_to_zip} folder not found or empty for {self.session_name}\n")
            return
        
        # Before zip, remove all file with extension
        for file in raw_folder.iterdir():
            if file.is_file() and ".tif.aux.xml" in file.name:
                file.unlink()
        
        t_start = datetime.now()
        print(f"Preparing {folder_to_zip} folder")
        shutil.make_archive(str(zip_folder), "zip", raw_folder)

        # Add photog report in preview files.
        if "PHOTOGRAMMETRY" in folder_to_zip:
            photog_report_path = Path(raw_folder, "odm_report", "report.pdf")
            if photog_report_path.exists():
                shutil.copy(photog_report_path, Path(self.temp_folder, "000_photogrammetry_report.pdf"))

        print(f"Successful zipped {folder_to_zip} folder in {datetime.now() - t_start} sec\n")


    def send_specific_file(self, file_to_send: str) -> None:
        """ Copy specific file to the temp folder. """
        file = Path(self.session_path, file_to_send)

        if file.exists():
            print(f"Copying {file} to {self.temp_folder}")
            shutil.copy(file, Path(self.temp_folder, file.name))


    def _zip_dcim(self) -> None:
        """ Zip all file in dcim folder. """
        dcim_folder = Path(self.session_path, "DCIM")
        dcim_files = natsorted(list(dcim_folder.iterdir()))
        
        if not Path.exists(dcim_folder) or not dcim_folder.is_dir() or not len(dcim_files) > 0:
            print(f"[WARNING] DCIM folder not found or empty for {self.session_name}\n")
            return
        
        t_start = datetime.now()
        print(f"Preparing DCIM folder")
        zipper = SessionZipper(Path(self.temp_folder, "DCIM.zip"))
        for file in dcim_files:
            if file.is_dir() and "GOPRO" in file.name:
                for gopro_file in natsorted(list(file.iterdir())):
                    zipper.add_file(gopro_file, Path(gopro_file.parent.name, gopro_file.name))
            else:
                zipper.add_file(file, file.name)
        zipper.close()
        print(f"Successful zipped DCIM folder in {datetime.now() - t_start} split in {zipper.nb_zip_file} archive\n")


    def _zip_processed_frames(self) -> None:
        """ Zip frames folder without useless frames """

        # Retrieve relative path of frame.
        frames_list = self.get_frames_list()
        if len(frames_list) == 0:
            print("[WARNING] No frames.")
            return
        
        # Get all useful images.
        useful_frames = self.get_useful_frames_name()        
        
        frame_parent_folder = self.get_frame_parent_folder(frames_list)
        frames_zip_path = Path(self.temp_folder, f"{frame_parent_folder.replace('/', '_')}.zip")
        frames_folder = Path(self.session_path, frame_parent_folder)

        if not Path.exists(frames_folder) or not frames_folder.is_dir() or len(list(frames_folder.iterdir())) == 0:
            print(f"[WARNING] Frames folder not found or empty for {self.session_name}\n")
            return 
        
        t_start = datetime.now()
        print(f"Preparing FRAMES folder")
        with ZipFile(frames_zip_path, "w", compression=ZIP_DEFLATED) as zip_object:
            for file in tqdm(frames_list):
                file = Path(file)
                if file.name in useful_frames:
                    zip_object.write(file, file.relative_to(frames_folder))
        print(f"Successful zipped FRAMES folder in {datetime.now() - t_start}\n")


    def _zip_gps_raw(self) -> None:
        """ Zip all file in gps folder. """
        gps_zip_path = Path(self.temp_folder, "GPS.zip")
        gps_base_folder = Path(self.session_path, "GPS/BASE")
        gps_device_folder = Path(self.session_path, "GPS/DEVICE")
        
        print("Preparing GPS folder")
        devices_file = natsorted(list(gps_device_folder.iterdir())) if Path.exists(gps_device_folder) and gps_device_folder.is_dir() else []
        base_files = natsorted(list(gps_base_folder.iterdir())) if Path.exists(gps_base_folder) and gps_base_folder.is_dir() else []

        if len(devices_file) == 0 and len(base_files) == 0:
            print(f"[WARNING] GPS folder empty\n")
            return
        
        t_start = datetime.now()
        with ZipFile(gps_zip_path, "w", compression=ZIP_DEFLATED) as zip_object:
            # Device folder
            for file in devices_file:
                if file.suffix not in [".zip", ".gpx"]: continue
                zip_object.write(file, Path(file.parent.name, file.name))
            
            # Base folder
            for file in base_files:
                if file.suffix not in [".o", ".zip"]: continue
                zip_object.write(file, Path(file.parent.name, file.name))
        print(f"Successful zipped GPS folder in {datetime.now() - t_start}\n")
        
    
    def __set_place(self) -> None:
        """ Set country and place as variable from session_name. """
        place = self.session_name.split("_")[1].split("-")
        country = pycountry.countries.get(alpha_3=place[0])
        if country != None:
            self.country = country.name.lower().title()
        else:
            print("[WARNING] Error in country code")
        self.place = "-".join([a.lower().title() for a in place[1:]])


    def __set_date(self) -> None:
        """ Set date as variable from session_name. """
        date = self.session_name.split("_")[0]
        if not date.isnumeric() or len(date) != 8: print("[WARNING] Error in session name")
        self.date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    

    def __set_platform(self) -> None:
        """ Set platform as variable from session_name. """
        self.platform = self.session_name.split("_")[2].split("-")[0].upper()


    def compute_basics_info(self) -> None:
        """ Compute basics information to avoid complication. """
        self.__set_place()
        self.__set_date()
        self.__set_platform()
        self.set_start_stop_mission_str()

    def cleanup(self) -> None:
        """ Remove all generated zipped file. """
        if not Path.exists(self.temp_folder) or not self.temp_folder.is_dir(): return

        for file in self.temp_folder.iterdir():
            if file.is_dir():
                for subfile in file.iterdir():
                    print(f"[INFO] Deleting {file}")
                    subfile.unlink()
                file.rmdir()
            else:
                print(f"[INFO] Deleting {file}")
                file.unlink()
    
    
    def move_into_subfolder_if_needed(self) -> list[Path]:
        zip_file_with_size = {}
        for file in self.temp_folder.iterdir():
            file_size = round(os.path.getsize(str(file)) / BYTE_TO_GIGA_BYTE, 3)
            zip_file_with_size[str(file)] = file_size

        # Total size of zip file can fit into one zenodo version
        if sum([zip_file_with_size[file] for file in zip_file_with_size]) < MAXIMAL_DEPOSIT_FILE_SIZE:
            return [self.temp_folder]
        
        # We need to move file to subdir
        cum_size, nb_ses = 0.0, 1.0
        f_to_move = Path(self.temp_folder, "RAW_DATA")
        f_to_move.mkdir(exist_ok=True)
        folders_to_upload = [f_to_move]

        for filename, size in natsorted(zip_file_with_size.items()):
            if size + cum_size >= MAXIMAL_DEPOSIT_FILE_SIZE:
                nb_ses += 1
                f_to_move = Path(self.temp_folder, f"RAW_DATA_{nb_ses}")
                f_to_move.mkdir(exist_ok=True)
                folders_to_upload.append(f_to_move)
                cum_size = size
            else:
                cum_size += size
            shutil.move(filename, Path(f_to_move, Path(filename).name))
        
        print(f"We will have {nb_ses} versions for RAW DATA")
        return folders_to_upload

    def get_jacques_csv(self) -> pd.DataFrame:
        """ Return jacques model data from csv."""
        IA_path = Path(self.session_path, "PROCESSED_DATA", "IA")
        if not IA_path.exists() or not IA_path.is_dir(): return pd.DataFrame()

        jacques_name = None
        for file in IA_path.iterdir():
            if JACQUES_MODEL_NAME in file.name:
                jacques_name = file
                break
        
        if jacques_name == None:
            print("[WARNING] Cannot find jacques predictions file.")
            return pd.DataFrame()

        jacques_csv = pd.read_csv(jacques_name)
        if len(jacques_csv) == 0: return pd.DataFrame()

        return jacques_csv


    def get_jacques_stat(self) -> tuple[float, float]:
        """ Return proportion of useful/useless. """
        
        jacques_csv = self.get_jacques_csv()
        if len(jacques_csv) == 0: return 0, 0
        
        useful = round(len(jacques_csv[jacques_csv["Useless"] == 0]) * 100 / len(jacques_csv), 2)
        useless = round(len(jacques_csv[jacques_csv["Useless"] == 1]) * 100 / len(jacques_csv), 2)
        
        return useful, useless


    def get_useful_frames_name(self) -> list[str]:
            """ Return a list of frames path predicted useful by jacques. """
            useful_frames = []
            try_ia = False
            # Get frame predictions.
            df_predictions_gps = self.get_predictions_gps()
            if len(df_predictions_gps) == 0: 
                print(f"Predictions GPS empty for session {self.session_name}\n")
                try_ia = True
            else:
                useful_frames = df_predictions_gps["FileName"].to_list() # CSV without useless images
            
            if not try_ia: return useful_frames

            print("We didn't find predictions gps, so we try with jacques csv annotations to select useful frames.")
            # Cannot find predictions_gps, try with jacques annotation_files
            
            df_jacques = self.get_jacques_csv()
            if len(df_jacques) == 0: return useful_frames

            useful_frames = df_jacques[df_jacques["Useless"] == 0]["FileName"].to_list()

            return useful_frames   


    def is_video_or_images(self) -> tuple[DCIMType, float]:
        """ Return media type of raw data. """
        dcim_path = Path(self.session_path, "DCIM")
        if not Path.exists(dcim_path) or not dcim_path.is_dir():
            return DCIMType.NONE, 0
        
        isVideoOrImagesOrNothing = DCIMType.NONE # None: Nothing, video: Video (priority), image: Images
        for file in dcim_path.iterdir():
            if ".mp4" in file.name.lower():
                return DCIMType.VIDEO, self.get_file_dcim_size([".mp4"])
            if ".jpg" in file.name.lower() or ".jpeg" in file.name.lower():
                isVideoOrImagesOrNothing = DCIMType.IMAGE

        return isVideoOrImagesOrNothing, 0 if isVideoOrImagesOrNothing == DCIMType.NONE else self.get_file_dcim_size([".mp4"] if isVideoOrImagesOrNothing == DCIMType.VIDEO else [".jpg", ".jpeg"])


    def get_file_dcim_size(self, extension: list[str]) -> float:
        """ Return Sum of filesize in Gb"""
        dcim_path = Path(self.session_path, "DCIM")
        if not Path.exists(dcim_path) or not dcim_path.is_dir(): return 0

        size = 0.0
        for file in dcim_path.iterdir():
            if file.suffix.lower() in extension:
                size += os.path.getsize(str(file)) / BYTE_TO_GIGA_BYTE
        return round(size, 2)
    

    def get_multilabel_csv(self, isScore: bool = False, indexingByFilename: bool = False) -> pd.DataFrame:
        """ Return multilabel model data from csv. """

        IA_path = Path(self.session_path, "PROCESSED_DATA", "IA")
        if not Path.exists(IA_path) or not IA_path.is_dir():
            return pd.DataFrame()
        
        multilabel_model_filename = None
        for file in IA_path.iterdir():
            if MULTILABEL_MODEL_NAME not in file.name: continue
            if not isScore and "_scores" in file.name or isScore and "_scores" not in file.name: continue
            
            multilabel_model_filename = file
        
        if multilabel_model_filename == None: return pd.DataFrame()
        
        index_col = None
        if indexingByFilename:
            with open(multilabel_model_filename, "r") as f:
                try:
                    index_col = f.readline().strip('\n').split(",").index("FileName")
                except ValueError:
                    print("[WARNING] FileName column not found in csv file.")


        multilabel_model_csv = pd.read_csv(multilabel_model_filename, index_col=index_col)
        if len(multilabel_model_csv) == 0: return pd.DataFrame()
        return multilabel_model_csv


    def get_predictions_gps(self) -> pd.DataFrame:
        """ Return predictions_gps content else {} if not found. """
        predictions_gps_path = Path(self.session_path, "METADATA", "predictions_gps.csv")
        if not Path.exists(predictions_gps_path): return pd.DataFrame()
        predictions_gps = pd.read_csv(predictions_gps_path)

        return predictions_gps if len(predictions_gps) != 0 else pd.DataFrame() # Avoid dataframe with just header and no data.
    

    def get_predictions_gps_with_filtering(self) -> pd.DataFrame:
        """ Return predictions_gps content else {} if empty or not exist or all point are in the same place. """

        predictions_gps = self.get_predictions_gps()
        
        if "GPSLongitude" not in predictions_gps or "GPSLatitude" not in predictions_gps: return pd.DataFrame() # No GPS coordinate
        if round(predictions_gps["GPSLatitude"].std(), 10) == 0.0 or round(predictions_gps["GPSLongitude"].std(), 10) == 0.0: return pd.DataFrame() # All frames have the same gps coordinate

        return predictions_gps


    def get_frames_list(self) -> list[Path]:
        """ Return list of frames from relative path in metadata csv. """
        frames_path: list[Path] = []

        # Get frame relative path.
        metadata_df = self.get_metadata_csv()
        if len(metadata_df) == 0: return frames_path
    
        try:
            relative_path_key = [key for key in list(metadata_df) if "relative_file_path" in key][0]
        except KeyError:
            raise NameError(f"Cannot find relative path key for {self.session_path}")

        # Iter on each file
        for _, row in metadata_df.iterrows():
            path_img = Path(Path(self.session_path).parent, *[x for x in row[relative_path_key].split("/") if x]) # Sometimes relative path start with /
            # Check if it's a file and if ended with image extension
            if path_img.is_file() and path_img.suffix.lower() in IMG_EXTENSION:
                frames_path.append(path_img)

        return frames_path


    def get_frame_parent_folder(self, list_frames: list) -> str:
        """ Extract common parent name from all relative path. """

        if len(list_frames) == 0: return ""

        # Remove image name and remove session name to get only intermediate folder.
        list_parents = list(set([str(Path(frame).parent).split(self.session_path.name)[1] for frame in list_frames]))

        # While we don't have a unique intermediate folder we keep reducing path
        avoid_stay_stuck = 0
        while len(list_parents) != 1 and avoid_stay_stuck < 10:
            list_parents = list(set([str(Path(p).parent) for p in list_parents]))
            avoid_stay_stuck += 1

        if avoid_stay_stuck == 10: return ""

        # Remove first underscore.
        return list_parents[0][1:] if list_parents[0][0] == "/" else list_parents[0]
    
    
    def get_metadata_csv(self, indexingByFilename: bool = False) -> pd.DataFrame:
        """ Getter to access metadata csv file. """
        metadata_path = Path(self.session_path, "METADATA/metadata.csv")
        if not Path.exists(metadata_path):
            print(f"No metadata_csv found for session {self.session_name}\n")
            return pd.DataFrame()

        index_col: bool | int = False
        if indexingByFilename:
            with open(metadata_path, "r") as f:
                try:
                    index_col = f.readline().strip('\n').replace('"', "").split(",").index("FileName")
                except ValueError:
                    print("[WARNING] FileName column not found in csv file.")
        return pd.read_csv(metadata_path, index_col=index_col)
    
    
    def get_waypoints_file(self) -> pd.DataFrame:
        """ Getter to acces waypoints file. """
        sensors_path = Path(self.session_path, "SENSORS")
        if not Path.exists(sensors_path) or not sensors_path.is_dir():
            print(f"No SENSORS folder for session {self.session_name}")
            return pd.DataFrame()
        
        
        for file in sensors_path.iterdir():
            if file.suffix != ".waypoints": continue

            waypoints = []
            with open(file, "r") as f:
                for row in f:
                    # Extract row and filter if not a gps row
                    row = row.replace("\n", "").split("\t")
                    if len(row) < 12 or row[2] != '3' or row[3] != '16': continue # 3 is the line for gps coordinate, 16 is more navigation
                    
                    # Check if coordinates is not 0,0 due to bad filtering.
                    lat, lon = float(row[8]), float(row[9])
                    if lat != 0 and lon != 0: continue # Avoid 0,0 point 
                    
                    waypoints.append((lat, lon))
                    
            return pd.DataFrame(waypoints, columns=["GPSLatitude", "GPSLongitude"])

        print(f"No waypoints file found for session {self.session_name}")
        return pd.DataFrame()


    def get_bit_size_zip_folder(self) -> dict:
        """ Return a dict of filename: size in TMP Folder. """
        print("func: Get size of zip file in temp_folder")
        filename_with_size = {}
        for file in self.temp_folder.iterdir():
            if file.suffix.lower() != ".zip": continue

            filename_with_size[file.name] = os.path.getsize(str(file))
            print(f"{file.name} : {filename_with_size[file.name]} bits")

        return filename_with_size


    def get_footprint(self) -> tuple[Polygon | None, LineString | None]:
        """Return the footprint of the session"""

        coordinates = self.get_metadata_csv() # With metadata, we get the real footprint of the image acquisition.
        if len(coordinates) == 0 or "GPSLatitude" not in coordinates or "GPSLongitude" not in coordinates: 
            coordinates = self.get_waypoints_file()
            if len(coordinates) == 0: return None, None

        if round(coordinates["GPSLatitude"].std(), 10) == 0.0 or round(coordinates["GPSLongitude"].std(), 10) == 0.0: 

            return None, None # All coordinates are the same.
        
        points = [[lat ,lon] for lat, lon in coordinates[['GPSLongitude', 'GPSLatitude']].values if lat != 0.0 and lon != 0.0] # Remove 0, 0 coordinates

        # Compute the convex hull for the original points
        hull = ConvexHull(points)
        polylist = []
        for idx in hull.vertices: # Indices of points forming the vertices of the convex hull.
            polylist.append(list(points[idx]))
        
        polygon = Polygon(polylist)
        
        # Compute all the general line.
        linestring = LineString([[lat ,lon] for i, (lat, lon) in enumerate(coordinates[['GPSLongitude', 'GPSLatitude']].values) if lat != 0.0 and lon != 0.0 and i % 10 != 0])

        # Return a collection of Polygon, LineString
        return polygon, linestring
    
    def _compute_odm_parameters_diff_with_default(self) -> dict | None:
        """ Return orthophoto parameters different from defautl if exist. """

        options = self._get_orthophoto_parameters()
        if options == None: return None

        # Get default parameters to compare.
        default_parameters = {}
        with open(Path(Path.cwd(), "src/seatizen_session/default_odm_parameters.json"), "r") as file:
            default_parameters = json.load(file)
        
        # Get the diff between the two dict.
        diff = {}
        for key in default_parameters:
            if key not in options: continue
            if default_parameters.get(key, None) == options.get(key, None): continue
            
            diff[key] = options.get(key, None)
        return diff
    

    def _get_orthophoto_parameters(self) -> dict | None:
        """ Return None if no photog else dict with parameters. """
        
        # Load options from log.json generate by ODM.
        ortho_parameters_path = Path(self.session_path, "PROCESSED_DATA", "PHOTOGRAMMETRY", "log.json")
        if not ortho_parameters_path.exists() or not ortho_parameters_path.is_file(): return None
        
        logs_json = {}
        with open(ortho_parameters_path, "r") as file:
            logs_json = json.load(file)
    
        if len(logs_json) == 0 or "options" not in logs_json: return None
        options = logs_json.get("options", {})

        return options

    def _build_photog_description(self) -> str:
        """ Build Photog description. """

        diff_options = self._compute_odm_parameters_diff_with_default()
        if diff_options == None: return ""

        return f"""
            <h2>Photogrammetry</h2>

            OpenDroneMap software was used to create an orthophoto from the raw images. <br>
            Here is the list of parameters different from the default values for the orthophoto generation. <br>
            For more details, you can read the log.json file or the 000_photogrammatry_report.pdf report. <br><br>

            <code>
                {diff_options}
            </code>
        """
    
    # https://geopython.github.io/pygeometa/reference/mcf/
    def generate_metadata_iso19115(self, metadata: dict, conceptrecid: int) -> None:
        """ Generate an ISO 19115 metadata file. """
        print("func: Generate the iso19115 file.")
        try:
            # Path of the default file.
            iso_path = Path("src/seatizen_session/default_iso_19115_file.yml")
            if not iso_path.exists():
                raise FileNotFoundError(f"Cannot find default iso 19115 file at {iso_path}")

            mcf_dict = read_mcf(iso_path)

            # Change the metadata.
            mcf_dict["metadata"]["identifier"] = self.session_name

            # Change identification.
            polygon, _ = self.get_footprint()
            mcf_dict["identification"]["doi"] = conceptrecid
            mcf_dict["identification"]["title"]["en"] = metadata["metadata"]["title"]
            mcf_dict["identification"]["abstract"]["en"] = metadata["metadata"]["description"]
            mcf_dict["identification"]["url"] = f"https://doi.org/10.5281/zenodo.{conceptrecid}"
            
            mcf_dict["identification"]["extents"]["spatial"][0]["bbox"] = polygon.bounds if polygon else []
            mcf_dict["identification"]["extents"]["temporal"][0]["begin"] = self.mission_start_str
            mcf_dict["identification"]["extents"]["temporal"][0]["resolution"] = compute_duration_iso8601(self.mission_start_date, self.mission_stop_date)
            
            mcf_dict["identification"]["keywords"]["default"]["keywords"]["en"] = metadata["metadata"]["keywords"]

            # Add all contributors
            for i, creator in enumerate(metadata["metadata"]["creators"]):
                mcf_dict["contact"][f"creators_{i}'"] = {
                    "organization": creator["affiliation"],
                    "url": f'https://orcid.org/{creator["orcid"]}' if "orcid" in creator else "",
                    "individualname": creator["name"],
                    "positionname": "", "phone": "", "fax": "", "address": "", "city": "", 
                    "administrativearea": "", "postalcode": "", "country": "", "email": ""
                }

            counter = {}
            for contributor in metadata["metadata"]["contributors"]:
                if contributor["type"] not in counter:
                    counter[contributor["type"]] = 0
                counter[contributor["type"]] += 1

                mcf_dict["contact"][f'{contributor["type"]}_{counter[contributor["type"]]}'] = {
                    "organization": contributor["affiliation"],
                    "url": f'https://orcid.org/{contributor["orcid"]}' if "orcid" in contributor else "",
                    "individualname": contributor["name"],
                    "positionname": "", "phone": "", "fax": "", "address": "", "city": "", 
                    "administrativearea": "", "postalcode": "", "country": "", "email": ""
                }

            
            # Add platform.
            platform_description = {
                "ASV": "Autonomous Surface Vehicle",
                "UAV": "Unmanned Aerial Vehicle",
                "SCUBA": "Scuba diving",
                "MASK": "Mask",
                "KITE": "Kite surf",
                "PADDLE": "Paddle",
                "UVC": "Underwater Vision Census"
            }
            mcf_dict["acquisition"]["platforms"][0]["identifier"] = self.platform
            mcf_dict["acquisition"]["platforms"][0]["description"] = platform_description[self.platform]
            mcf_dict["acquisition"]["platforms"][0]["instruments"] = []

            # Validate if the iso19115 file is correct.
            validate_mcf(mcf_dict)

            # Transform the dict into a string chain.
            iso_os = ISO19139_2OutputSchema()
            xml_string = iso_os.write(mcf_dict)
            
            # Export the data at the root of the session.
            iso19115_filepath = Path(self.session_path, f"{self.session_name}_iso_19115.xml")
            with open(iso19115_filepath, "w") as f:
                f.write(xml_string)
        
        except Exception as e:
            print(e)
            print(f"Cannot produce iso 19115 file.")
            return