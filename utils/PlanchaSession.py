import os
import json
import shutil
import pycountry
import pandas as pd
from tqdm import tqdm
from enum import Enum
from time import time
from pathlib import Path
from zipfile import ZipFile
from exiftool import ExifToolHelper

class BaseType(Enum):
    RGP = "RGP Station from IGN"
    REACH = "Emlid Reach RS2+"
    NONE = "No Base"

class DCIMType(Enum):
    NONE = "Nothing"
    VIDEO = "MP4 files"
    IMAGE = "JPG files"

class PlanchaSession:

    def __init__(self, session_path, temp_folder):
        # Basics path.
        self.session_path = Path(session_path)
        self.session_name = self.session_path.name

        # Create tmp folder.
        self.temp_folder = Path(temp_folder, self.session_name)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        
        # Compute informations.
        self.place, self.date, self.country = None, None, None
        self.compute_basics_info()
    
    def prepare_raw_data(self):
        self.cleanup()
        print("-- Prepare raw data... ")
        self.__zip_gps_raw()

        for folder in ["SENSORS", "DCIM"]:
            self.__zip_raw(folder)
    
    def prepare_processed_data(self, processed_folder, needFrames=False):
        self.cleanup()
        print("-- Prepare processed data... ")

        for folder in processed_folder:
            self.__zip_raw(folder)

        if needFrames:
            self.__zip_processed_frames()

        for file in self.session_path.iterdir():
            if file.suffix == ".pdf":
                shutil.copy(file, Path(self.temp_folder, file.name))

    def __zip_raw(self, folder):
        """ Zip all file in folder. """
        zip_folder = Path(self.temp_folder, folder.replace("/", "_"))
        raw_folder = Path(self.session_path, folder)
        if Path.exists(raw_folder) and raw_folder.is_dir() and len(list(raw_folder.iterdir())) > 0:
            print(f"Preparing {folder} folder")
            start_t = time()
            shutil.make_archive(zip_folder, "zip", raw_folder)
            print(f"Successful zipped {folder} folder in {time() - start_t} sec\n")
        else:
            print(f"[WARNING] {folder} folder not found or empty for {self.session_name}\n")
    
    def __zip_processed_frames(self):
        """ Zip frames folder without useless frames """
        frames_zip_path = Path(self.temp_folder, "PROCESSED_DATA_FRAMES.zip")
        frames_folder = Path(self.session_path, "PROCESSED_DATA/FRAMES")
        predictions_gps = Path(self.session_path, "METADATA/predictions_gps.csv")

        if not Path.exists(predictions_gps):
            print(f"No predictions_gps found for session {self.session_name}\n")
            return

        df_predictions_gps = pd.read_csv(predictions_gps)

        if len(df_predictions_gps) == 0: 
            print(f"Predictions GPS empty for session {self.session_name}\n")
            return

        filenames = df_predictions_gps["FileName"].to_list()
        if Path.exists(frames_folder) and frames_folder.is_dir() and len(list(frames_folder.iterdir())) > 0:
            print(f"Preparing FRAMES folder")
            with ZipFile(frames_zip_path, "w") as zip_object:
                for file in tqdm(sorted(list(frames_folder.iterdir()))):
                    if file.name in filenames:
                        zip_object.write(file, Path(file.parent.name, file.name))
            print(f"Successful zipped FRAMES folder\n")
        else:
            print(f"[WARNING] Frames folder not found or empty for {self.session_name}\n")


    def __zip_gps_raw(self):
        """ Zip all file in gps folder. """
        gps_zip_path = Path(self.temp_folder, "GPS.zip")
        gps_base_folder = Path(self.session_path, "GPS/BASE")
        gps_device_folder = Path(self.session_path, "GPS/DEVICE")

        if Path.exists(gps_base_folder) and gps_base_folder.is_dir() and Path.exists(gps_device_folder) and gps_device_folder.is_dir():
            print("Preparing GPS folder")
            with ZipFile(gps_zip_path, "w") as zip_object:
                # Device folder
                for file in sorted(list(gps_device_folder.iterdir())):
                    if file.suffix not in [".zip", ".gpx"]: continue
                    zip_object.write(file, Path(file.parent.name, file.name))
                
                # Base folder
                for file in sorted(list(gps_base_folder.iterdir())):
                    if file.suffix not in [".o", ".zip"]: continue
                    zip_object.write(file, Path(file.parent.name, file.name))
            print("Successful zipped GPS folder\n")
        else:
            print(f"[WARNING] GPS folder not found for {self.session_name}\n")
    
    def __set_place(self):
        place = self.session_name.split("_")[1].split("-")
        self.country = pycountry.countries.get(alpha_3=place[0])
        if self.country != None:
            self.country = self.country.name.lower().title()
        else:
            print("[WARNING] Error in country code")
        self.place = place[-1].lower().title()

    def __set_date(self):
        date = self.session_name.split("_")[0]
        if not date.isnumeric() or len(date) != 8: print("[WARNING] Error in session name")
        self.date = date

    def compute_basics_info(self):
        self.__set_place()
        self.__set_date()

    def cleanup(self):
        """ Remove all generated zipped file. """
        if not Path.exists(self.temp_folder) or not self.temp_folder.is_dir(): return

        for file in self.temp_folder.iterdir():
            print(f"[INFO] Deleting {file}")
            file.unlink()
    
    # Return True if ppk file else False
    def check_ppk(self):
        """ True or false if session is processed with ppk """
        gps_device_path = Path(self.session_path, "GPS", "DEVICE")
        if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
            return False
        
        for file in gps_device_path.iterdir():
            filename = file.name
            if "ppk_solution" in filename and ".pos" in filename:
                return True
        return False

    def read_and_extract_percentage(self, file):
        """ Extract and return Q1, Q2, Q5 %"""
        df = pd.read_csv(file, sep=",")
        if "fix" not in df or len(df) == 0: return 0, 0, 0

        q1 = round(len(df[df["fix"] == 1]) * 100 / len(df), 2)
        q2 = round(len(df[df["fix"] == 2]) * 100 / len(df), 2)
        q5 = round(len(df[df["fix"] == 5]) * 100 / len(df), 2)

        return q1, q2, q5

    # Return percentage for Q1, Q2, Q5
    def get_percentage(self, isPPK):
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

    def get_base_type(self):
        """ Return the base used """
        gps_base_path = Path(self.session_path, "GPS", "BASE")
        if not Path.exists(gps_base_path) or not gps_base_path.is_dir():
            return BaseType.NONE
        
        # Check for merged.o
        for file in gps_base_path.iterdir():
            if "merged.o" in file.name:
                return BaseType.RGP
        
        # Check for LLh
        for file in gps_base_path.iterdir():
            if "_RINEX" in file.name:
                return BaseType.REACH
        
        return BaseType.NONE

    def check_gpx(self):
        """ Return true is gpx file"""
        gps_device_path = Path(self.session_path, "GPS", "DEVICE")
        if not Path.exists(gps_device_path) or not gps_device_path.is_dir():
            return False
        
        for file in gps_device_path.iterdir():
            if ".gpx" in file.name:
                return True
        return False

    def check_sensor_file(self):
        sensor_path = Path(self.session_path, "SENSORS")
        if not Path.exists(sensor_path) or not sensor_path.is_dir():
            return False

        for file in sensor_path.iterdir():
            if ".bin" in file.name.lower() or ".log" in file.name.lower():
                return True
        return False

    def get_bathy_stat(self):
        bathy_path = Path(self.session_path, "PROCESSED_DATA", "BATHY")
        if not Path.exists(bathy_path) or not bathy_path.is_dir():
            return False

        return len(list(bathy_path.iterdir())) > 20 # Assumed if we have less than 20 files, we don't have processed bathy

    def is_video_or_images(self):
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

    def get_file_dcim_size(self, extension):
        """ Return Sum of filesize """
        dcim_path = Path(self.session_path, "DCIM")
        if not Path.exists(dcim_path) or not dcim_path.is_dir(): return 0

        size = 0
        for file in dcim_path.iterdir():
            if file.suffix.lower() in extension:
                size += round(os.path.getsize(str(file)) / 1000000000, 1)
        return size

    def check_frames(self):
        frames_path = Path(self.session_path, "PROCESSED_DATA", "FRAMES")
        if not Path.exists(frames_path) or not frames_path.is_dir():
            return 0, False

        nb_frames = len(list(frames_path.iterdir()))
        isGeoreferenced = False
        if nb_frames > 0:
            with ExifToolHelper() as et:
                metadata = et.get_metadata(next(frames_path.iterdir()))[0]
                if "Composite:GPSLongitude" in metadata and "Composite:GPSLatitude" in metadata:
                    isGeoreferenced = True

        return nb_frames, isGeoreferenced

    def get_jacques_stat(self):
        IA_path = Path(self.session_path, "PROCESSED_DATA", "IA")
        if not Path.exists(IA_path) or not IA_path.is_dir():
            return "", 0, 0

        jacques_name, useful, useless = "", 0, 0
        for file in IA_path.iterdir():
            if "jacques" in file.name:
                jacques_name = file.name.split("_")[-1].replace(".csv", "")
                df = pd.read_csv(file)
                if len(df) > 0:
                    useful = round(len(df[df["Useless"] == 0]) * 100 / len(df), 2)
                    useless = round(len(df[df["Useless"] == 1]) * 100 / len(df), 2)
        
        return jacques_name, useful, useless

    def get_hugging_face(self):
        IA_path = Path(self.session_path, "PROCESSED_DATA", "IA")
        if not Path.exists(IA_path) or not IA_path.is_dir():
            return ""
        
        for file in IA_path.iterdir():
            if "lombardata" in file.name:
                return file.name.replace(self.session_name + "_", "").replace(".csv", "")

        return ""
    
    def get_echo_sounder_name(self):
        asv_number = int(self.session_name.split("_")[2].replace("ASV-", ""))
        if asv_number == 1:
            return '<a href="https://www.echologger.com/products/single-frequency-echosounder-deep" _target="blank">ETC 400</a>'
        elif asv_number == 2:
            return '<a href="https://ceruleansonar.com/products/sounder-s500" _target="blank">S500</a>'
        else:
            return ""
    
    def get_prog_json(self):
        prog_path = Path(self.session_path, "PROCESSED_DATA", "BATHY", "prog_config.json")
        if not Path.exists(prog_path): return None

        with open(prog_path, "r") as f:
            prog_config = json.load(f)
        return prog_config