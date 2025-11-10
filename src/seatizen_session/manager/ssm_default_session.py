import json
import pandas as pd
pd.set_option("display.precision", 12)
from pathlib import Path
from datetime import datetime

from ...utils.constants import MULTILABEL_AUTHOR, JACQUES_MODEL_NAME, MULTILABEL_MODEL_NAME
from .ssm_base_manager import BaseType, DCIMType, BaseSessionManager

class DefaultSession(BaseSessionManager):

    def __init__(self, session_path: str, temp_folder: str) -> None:
        super().__init__(session_path, temp_folder)

    # -- Mandatory methods
    def get_restricted_files_on_zenodo(self) -> list[str]:
        return ["DCIM"]


    def get_raw_access_right(self) -> str:
        return "restricted"


    def get_processed_access_right(self) -> str:
        return "open"


    def build_raw_description(self) -> str:
        return ""


    def build_processed_description(self) -> str:
        
        return f"""
                {self.__get_image_acquisition_text()}
                                       
                {self.__get_gps_text()}
                    
                {self.__get_bathymetry_text()}

                {self._build_photog_description()}
            """


    def set_start_stop_mission_str(self) -> None:

        metadata_csv = self.get_metadata_csv()
        if metadata_csv.empty: return
        
        date_key = "SubSecDateTimeOriginal" if "SubSecDateTimeOriginal" in metadata_csv else "GPSDateTime"
        if metadata_csv[metadata_csv[date_key].notna()].empty:
            date_key = "DateTimeOriginal"
        metadata_csv = metadata_csv[metadata_csv[date_key].notna()]

        self.mission_start_str = metadata_csv[date_key].min().split(".")[0].replace('-', ':')
        self.mission_stop_str = metadata_csv[date_key].max().split(".")[0].replace('-', ':')


    def zip_raw_data(self) -> None:
        self._zip_gps_raw()
        self._zip_dcim()
        self._zip_folder("SENSORS")


    def __get_image_acquisition_text(self) -> str:
        # Check for video
        isVideo, size_media = self.is_video_or_images()
        if isVideo == DCIMType.NONE: return ""

        # Check for frames and georeferenced frames
        nb_frames, isGeoreferenced = self.check_frames()
        if nb_frames == 0: return f"This session has {size_media} GB of {isVideo.value}, but no images were trimmed."

        # Check for predictions
        j_useful, j_useless = self.get_jacques_stat()
        link_hugging = f"https://huggingface.co/{MULTILABEL_AUTHOR}/{MULTILABEL_MODEL_NAME}"
        
        prog_json = self.get_prog_json()
        if len(prog_json) == 0: return ""
        fps = prog_json["dcim"]["frames_per_second"]


        return f"""
                <h2>Image acquisition</h2>
                This session has {size_media} GB of {isVideo.value}, which were trimmed into {nb_frames} frames (at {fps} fps). <br> 
                The frames are {'' if isGeoreferenced else 'not'} georeferenced. <br>
                {j_useful}% of these extracted images are useful and {j_useless}% are useless, according to predictions made by <a href="{JACQUES_MODEL_NAME}" target="_blank">Jacques model</a>. <br>
                Multilabel predictions have been made on useful frames using <a href="{link_hugging}" target="_blank">DinoVd'eau</a> model. <br>
            """


    def __get_gps_text(self) -> str:
        # Find if we do ppk
        isPPK = self.check_ppk() 
        q1, q2, q5 = self.get_percentage(isPPK)
        isGPX = self.check_gpx() # LLH from reach or LLH generated from gpx file (Garmin watch)

        if (q1 + q2 + q5) == 0:
            return f"""
                <h2> GPS information: </h2>

                {"GPX file from Garmin watch." if isGPX else "No GPS."}
            """
        
        basetype = self.get_base_type() if isPPK else BaseType.NONE

        return f"""
            <h2> GPS information: </h2>
            {"The data was processed with a PPK workflow to achieve centimeter-level GPS accuracy. <br>" if isPPK else ""}
            Base : {"Files coming from rtk a GPS-fixed station or any static positioning instrument which can provide with correction frames." if basetype != BaseType.NONE else basetype.value} <br>
            Device GPS : {"GPX file from Garmin watch" if isGPX else "Emlid Reach M2"} <br>
            Quality of our data - Q1: {q1} %, Q2: {q2} %, Q5: {q5} % <br>

        """

    def __get_bathymetry_text(self) -> str:

        prog_json = self.get_prog_json()
        haveSensorFile = self.check_sensor_file()
        isBathyGenerated = self.get_bathy_stat()

        if not haveSensorFile or not isBathyGenerated or len(prog_json) == 0: return ""

        return f"""
                <h2> Bathymetry </h2>

                The data are collected using a single-beam echosounder {self.get_echo_sounder_name()}. <br>

                {"We only keep the values which have a GPS correction in Q1.<br>" if prog_json["gps"]["filt_rtkfix"] else ""}
                {"We keep the points that are the waypoints.<br>" if prog_json["gps"]["filt_waypoint"] else ""}

                We keep the raw data where depth was estimated between {prog_json["bathy"]["dpth_range"]["min"]} m and {prog_json["bathy"]["dpth_range"]["max"]} m deep. <br>
                The data are first referenced against the {prog_json["gps"]["utm_ellips"]} ellipsoid. {"Then we apply the local geoid if available." if prog_json["bathy"]["use_geoid"] else ""}<br>
                At the end of processing, the data are projected into a homogeneous grid to create a raster and a shapefiles. <br>
                The size of the grid cells is {prog_json["mesh"]["spacing_m"]} m. <br>
                The raster and shapefiles are generated by {prog_json["mesh"]["method"]} interpolation. The 3D reconstruction algorithm is {prog_json["mesh"]["3Dalgo"]}. <br>
            """


    def check_ppk(self) -> bool:
        """ True or false if session is processed with ppk """
        gps_device_path = Path(self.session_path, "GPS", "DEVICE")
        if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
            return False
        
        for file in gps_device_path.iterdir():
            filename = file.name
            if "ppk_solution" in filename and ".pos" in filename:
                return True
        return False


    def read_and_extract_percentage(self, file: Path) -> tuple[float, float, float]:
        """ Extract and return Q1, Q2, Q5 %"""
        df = pd.read_csv(file, sep=",")
        if "fix" not in df or len(df) == 0: return 0, 0, 0

        q1 = round(len(df[df["fix"] == 1]) * 100 / len(df), 2)
        q2 = round(len(df[df["fix"] == 2]) * 100 / len(df), 2)
        q5 = round(len(df[df["fix"] == 5]) * 100 / len(df), 2)

        return q1, q2, q5


    # Return percentage for Q1, Q2, Q5
    def get_percentage(self, isPPK: bool) -> tuple[float, float, float]:
        """ Choose the right file to extract Q1, Q2, Q5"""
        gps_device_path = Path(self.session_path, "GPS", "DEVICE")
        if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
            return 0,0,0
        
        for file in gps_device_path.iterdir():
            if isPPK and "ppk_solution" in file.name and ".txt" in file.name:
                return self.read_and_extract_percentage(file)
            elif not isPPK and "_LLH" in file.name and file.is_dir():
                for subfile in file.iterdir():
                    if ".txt" in subfile.name:
                        return self.read_and_extract_percentage(subfile)
            elif not isPPK and ".txt" in file.name and Path.exists(Path(file.parent, file.name.replace(".txt", ".LLH"))):
                return self.read_and_extract_percentage(file)
        
        return 0, 0, 0


    def get_base_type(self) -> BaseType:
        """ Return the base used """
        gps_base_path = Path(self.session_path, "GPS", "BASE")
        if not Path.exists(gps_base_path) or not gps_base_path.is_dir():
            return BaseType.NONE
        
        # Check for merged.o
        for file in gps_base_path.iterdir():
            if "merged.o" in file.name:
                return BaseType.RGP
        
        # Check for RS3
        for file in gps_base_path.iterdir():
            if "RS3" in file.name:
                return BaseType.REACH_RS3
            
        # Check for LLh
        for file in gps_base_path.iterdir():
            if "_RINEX" in file.name:
                return BaseType.REACH_RS2
        
        return BaseType.NONE


    def check_gpx(self) -> bool:
        """ Return true is gpx file"""
        gps_device_path = Path(self.session_path, "GPS", "DEVICE")
        if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
            return False
        
        for file in gps_device_path.iterdir():
            if ".gpx" in file.name:
                return True
        return False


    def check_sensor_file(self) -> bool:
        """ Return true or false if sensor file exist. """
        sensor_path = Path(self.session_path, "SENSORS")
        if not Path.exists(sensor_path) or not sensor_path.is_dir():
            return False

        for file in sensor_path.iterdir():
            if ".bin" in file.name.lower() or ".log" in file.name.lower():
                return True
        return False


    def get_bathy_stat(self) -> bool:
        """ Return true or false if bathy workflow succeed. """
        bathy_path = Path(self.session_path, "PROCESSED_DATA", "BATHY")
        if not Path.exists(bathy_path) or not bathy_path.is_dir():
            return False

        return len(list(bathy_path.iterdir())) > 20 # Assumed if we have less than 20 files, we don't have processed bathy
    

    def check_frames(self) -> tuple[int, bool]:
        """ Check if we have split some frames and if they are georefenreced. """
        
        # Get frame relative path.
        metadata_df = self.get_metadata_csv()
        if len(metadata_df) == 0: return 0, False

        nb_frames = len(metadata_df)
        
        # Drop NA columns, sometimes, GPSLatitude is filled with NA value
        metadata_df.replace("", float("NaN"), inplace=True)
        metadata_df.dropna(how='all', axis=1, inplace=True)
        isGeoreferenced = "GPSLongitude" in metadata_df and "GPSLatitude" in metadata_df
        return nb_frames, isGeoreferenced
    

    def get_echo_sounder_name(self) -> str:
        """ Return echo sounder name based on ASV number. """
        asv_number = int(self.session_name.split("_")[2].replace("ASV-", ""))
        if asv_number == 1:
            return '<a href="https://www.echologger.com/products/single-frequency-echosounder-deep" target="_blank">ETC 400</a>'
        elif asv_number == 2:
            return '<a href="https://ceruleansonar.com/products/sounder-s500" target="_blank">S500</a>'
        else:
            return ""


    def get_prog_json(self) -> dict:
        """ Return plancha config of the session. """
        prog_path = Path(self.session_path, "METADATA", "prog_config.json")
        if not Path.exists(prog_path): return {}

        with open(prog_path, "r") as f:
            prog_config = json.load(f)
        return prog_config     