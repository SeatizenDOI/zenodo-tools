import os
import json
import shutil
import pycountry
import pandas as pd
from tqdm import tqdm
from enum import Enum
from pathlib import Path
from zipfile import ZipFile
from datetime import datetime
from natsort import natsorted

from .PlanchaZipper import PlanchaZipper
from .constants import MAXIMAL_DEPOSIT_FILE_SIZE, IMG_EXTENSION, BYTE_TO_GIGA_BYTE

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
        self.place, self.date, self.country, self.platform = None, None, None, None
        self.compute_basics_info()


    def prepare_raw_data(self):
        """ Zip all file in a tmp folder. """
        self.cleanup()
        print("-- Prepare raw data... ")
        self.__zip_gps_raw()
        self.__zip_dcim()
        self.__zip_raw("SENSORS")
        
        print("-- Sort and move to sub folder if needed... ")
        return self.move_into_subfolder_if_needed()
        
    
    def prepare_processed_data(self, processed_folder, needFrames=False):
        """ Zip all processed data in tmp folder. """
        self.cleanup()
        print("-- Prepare processed data... ")

        for folder in processed_folder:
            self.__zip_raw(folder)

        if needFrames:
            self.__zip_processed_frames()

        for file in self.session_path.iterdir():
            if file.is_file():
                shutil.copy(file, Path(self.temp_folder, file.name))
        
        # Check if tmp folder is > MAX_SIZE_FILE_DEPOSIT to avoid error
        size_gb = round(sum([os.stat(file).st_size for file in self.temp_folder.iterdir()]) / BYTE_TO_GIGA_BYTE, 6)
        if size_gb > MAXIMAL_DEPOSIT_FILE_SIZE:
            raise NameError("The sum total of processed data file sizes is greater than the Zenodo limit.")


    def __zip_raw(self, folder):
        """ Zip all file in folder. """
        zip_folder = Path(self.temp_folder, folder.replace("/", "_"))
        raw_folder = Path(self.session_path, folder)
        
        if not Path.exists(raw_folder) or not raw_folder.is_dir() or not len(list(raw_folder.iterdir())) > 0:
            print(f"[WARNING] {folder} folder not found or empty for {self.session_name}\n")
            return
        
        # Before zip, remove all file with extension
        for file in raw_folder.iterdir():
            if file.is_file() and ".tif.aux.xml" in file.name:
                file.unlink()
        
        t_start = datetime.now()
        print(f"Preparing {folder} folder")
        shutil.make_archive(zip_folder, "zip", raw_folder)
        print(f"Successful zipped {folder} folder in {datetime.now() - t_start} sec\n")


    def __zip_dcim(self):
        """ Zip all file in dcim folder. """
        dcim_folder = Path(self.session_path, "DCIM")
        dcim_files = natsorted(list(dcim_folder.iterdir()))
        
        if not Path.exists(dcim_folder) or not dcim_folder.is_dir() or not len(dcim_files) > 0:
            print(f"[WARNING] DCIM folder not found or empty for {self.session_name}\n")
            return
        
        t_start = datetime.now()
        print(f"Preparing DCIM folder")
        zipper = PlanchaZipper(Path(self.temp_folder, "DCIM.zip"))
        for file in dcim_files:
            if file.is_dir() and "GOPRO" in file.name:
                for gopro_file in natsorted(list(file.iterdir())):
                    zipper.add_file(gopro_file, Path(gopro_file.parent.name, gopro_file.name))
            else:
                zipper.add_file(file, file.name)
        zipper.close()
        print(f"Successful zipped DCIM folder in {datetime.now() - t_start} split in {zipper.nb_zip_file} archive\n")


    def __zip_processed_frames(self):
        """ Zip frames folder without useless frames """

        # Retrieve relative path of frame.
        frames_list = self.get_frames_list()
        
        # Get frame predictions.
        predictions_gps_path = Path(self.session_path, "METADATA/predictions_gps.csv")
        if not Path.exists(predictions_gps_path):
            print(f"No predictions_gps found for session {self.session_name}\n")
            return
        
        df_predictions_gps = pd.read_csv(predictions_gps_path)
        if len(df_predictions_gps) == 0: 
            print(f"Predictions GPS empty for session {self.session_name}\n")
            return
        filenames = df_predictions_gps["FileName"].to_list() # CSV without useless images
        
        frame_parent_folder = self.get_frame_parent_folder(frames_list)
        frames_zip_path = Path(self.temp_folder, f"{frame_parent_folder.replace('/', '_')}.zip")
        frames_folder = Path(self.session_path, frame_parent_folder)

        if not Path.exists(frames_folder) or not frames_folder.is_dir() or len(list(frames_folder.iterdir())) == 0:
            print(f"[WARNING] Frames folder not found or empty for {self.session_name}\n")
            return 
        
        t_start = datetime.now()
        print(f"Preparing FRAMES folder")
        with ZipFile(frames_zip_path, "w") as zip_object:
            for file in tqdm(frames_list):
                file = Path(file)
                if file.name in filenames:
                    zip_object.write(file, file.relative_to(frames_folder))
        print(f"Successful zipped FRAMES folder in {datetime.now() - t_start}\n")


    def __zip_gps_raw(self):
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
        with ZipFile(gps_zip_path, "w") as zip_object:
            # Device folder
            for file in devices_file:
                if file.suffix not in [".zip", ".gpx"]: continue
                zip_object.write(file, Path(file.parent.name, file.name))
            
            # Base folder
            for file in base_files:
                if file.suffix not in [".o", ".zip"]: continue
                zip_object.write(file, Path(file.parent.name, file.name))
        print(f"Successful zipped GPS folder in {datetime.now() - t_start}\n")
        
    
    def __set_place(self):
        """ Set country and place as variable. """
        place = self.session_name.split("_")[1].split("-")
        self.country = pycountry.countries.get(alpha_3=place[0])
        if self.country != None:
            self.country = self.country.name.lower().title()
        else:
            print("[WARNING] Error in country code")
        self.place = "-".join([a.lower().title() for a in place[1:]])


    def __set_date(self):
        """ Set data as variable. """
        date = self.session_name.split("_")[0]
        if not date.isnumeric() or len(date) != 8: print("[WARNING] Error in session name")
        self.date = f"{date[0:4]}-{date[4:6]}-{date[6:8]}"
    

    def __set_platform(self):
        """ Set platform as variable. """
        self.platform = self.session_name.split("_")[2].split("-")[0].upper()


    def compute_basics_info(self):
        """ Compute basics information to avoid complication. """
        self.__set_place()
        self.__set_date()
        self.__set_platform()


    def cleanup(self):
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
    
    
    def move_into_subfolder_if_needed(self):
        zip_file_with_size = {}
        for file in self.temp_folder.iterdir():
            file_size = round(os.path.getsize(str(file)) / BYTE_TO_GIGA_BYTE, 3)
            zip_file_with_size[str(file)] = file_size

        # Total size of zip file can fit into one zenodo version
        if sum([zip_file_with_size[file] for file in zip_file_with_size]) < MAXIMAL_DEPOSIT_FILE_SIZE:
            return [self.temp_folder]
        
        # We need to move file to subdir
        cum_size, nb_ses = 0, 1
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
        """ Return true or false if sensor file exist. """
        sensor_path = Path(self.session_path, "SENSORS")
        if not Path.exists(sensor_path) or not sensor_path.is_dir():
            return False

        for file in sensor_path.iterdir():
            if ".bin" in file.name.lower() or ".log" in file.name.lower():
                return True
        return False


    def get_bathy_stat(self):
        """ Return true or false if bathy workflow succeed. """
        bathy_path = Path(self.session_path, "PROCESSED_DATA", "BATHY")
        if not Path.exists(bathy_path) or not bathy_path.is_dir():
            return False

        return len(list(bathy_path.iterdir())) > 20 # Assumed if we have less than 20 files, we don't have processed bathy


    def is_video_or_images(self):
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


    def get_file_dcim_size(self, extension):
        """ Return Sum of filesize """
        dcim_path = Path(self.session_path, "DCIM")
        if not Path.exists(dcim_path) or not dcim_path.is_dir(): return 0

        size = 0
        for file in dcim_path.iterdir():
            if file.suffix.lower() in extension:
                size += round(os.path.getsize(str(file)) / BYTE_TO_GIGA_BYTE, 1)
        return size


    def check_frames(self):
        """ Check if we have split some frames and if they are georefenreced. """
        
        # Get frame relative path.
        metadata_path = Path(self.session_path, "METADATA/metadata.csv")
        if not Path.exists(metadata_path):
            print(f"No metadata_csv found for session {self.session_name}\n")
            return 0, False
        metadata_df = pd.read_csv(metadata_path)

        nb_frames = len(metadata_df)
        
        # Drop NA columns, sometimes, GPSLatitute is filled with NA value
        metadata_df.replace("", float("NaN"), inplace=True)
        metadata_df.dropna(how='all', axis=1, inplace=True)
        isGeoreferenced = "GPSLongitude" in metadata_df and "GPSLatitude" in metadata_df
        return nb_frames, isGeoreferenced


    def get_jacques_stat(self):
        """ Get jacques model name and return proportion of useful/useless. """
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
        """ Return hugging face model name"""
        IA_path = Path(self.session_path, "PROCESSED_DATA", "IA")
        if not Path.exists(IA_path) or not IA_path.is_dir():
            return ""
        
        for file in IA_path.iterdir():
            if "lombardata" in file.name:
                return file.name.replace(self.session_name + "_", "").replace(".csv", "")

        return ""


    def get_echo_sounder_name(self):
        """ Return echo sounder name based on ASV number. """
        asv_number = int(self.session_name.split("_")[2].replace("ASV-", ""))
        if asv_number == 1:
            return '<a href="https://www.echologger.com/products/single-frequency-echosounder-deep" _target="blank">ETC 400</a>'
        elif asv_number == 2:
            return '<a href="https://ceruleansonar.com/products/sounder-s500" _target="blank">S500</a>'
        else:
            return ""


    def get_prog_json(self):
        """ Return plancha config of the session. """
        prog_path = Path(self.session_path, "METADATA", "prog_config.json")
        if not Path.exists(prog_path): return None

        with open(prog_path, "r") as f:
            prog_config = json.load(f)
        return prog_config


    def get_predictions_gps(self):
        """ Return predictions_gps content else {} if empty or not exist or all point are in the same place. """
        predictions_gps_path = Path(self.session_path, "METADATA", "predictions_gps.csv")
        if not Path.exists(predictions_gps_path): return {}

        predictions_gps = pd.read_csv(predictions_gps_path)
        if len(predictions_gps) == 0: return {} # No predictions
        if "GPSLongitude" not in predictions_gps or "GPSLatitude" not in predictions_gps: return {} # No GPS coordinate
        if round(predictions_gps["GPSLatitude"].std(), 10) == 0.0 or round(predictions_gps["GPSLongitude"].std(), 10) == 0.0: return {} # All frames have the same gps coordinate

        return predictions_gps


    def get_frames_list(self):
        """ Return list of frames from relative path in metadata csv. """
        frames_path = []

        # Get frame relative path.
        metadata_path = Path(self.session_path, "METADATA/metadata.csv")
        if not Path.exists(metadata_path):
            print(f"No metadata_csv found for session {self.session_name}\n")
            return frames_path
        metadata_df = pd.read_csv(metadata_path)
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

    def get_frame_parent_folder(self, list_frames):
        """ Extract common parent name from all relative path. """

        # Remove image name and remove session name to get only intermediate folder.
        list_parents = list(set([str(Path(frame).parent).split(self.session_path.name)[1] for frame in list_frames]))

        # While we don't have a unique intermediate folder we keep reducing path
        while len(list_parents) != 1:
            list_parents = list(set([str(Path(p).parent) for p in list_parents]))

        # Remove first underscore.
        return list_parents[0][1:] if list_parents[0][0] == "/" else list_parents[0]