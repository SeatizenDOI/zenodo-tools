import enum
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

class Sources(enum.Enum):
    CSV_SESSION = 0
    FOLDER = 1
    SESSION = 2

def get_mode_from_opt(opt) -> Sources | None:
    """ Retrieve mode from input option """
    mode = None

    if opt.enable_csv: 
        mode = Sources.CSV_SESSION
    elif opt.enable_folder: 
        mode = Sources.FOLDER
    elif opt.enable_session: 
        mode = Sources.SESSION

    return mode

def get_src_from_mode(mode: Sources, opt) -> Path:
    """ Retrieve src path from mode """
    src = Path()

    if mode == Sources.CSV_SESSION:
        src = Path(opt.path_csv_file)
    elif mode == Sources.FOLDER:
        src = Path(opt.path_folder)
    elif mode == Sources.SESSION:
        src = Path(opt.path_session)

    return src

def get_list_sessions(opt) -> list[Path]:
    """ Retrieve list of sessions from input """

    list_sessions: list[Path] = []

    mode = get_mode_from_opt(opt)
    if mode == None: return list_sessions

    src = get_src_from_mode(mode, opt)

    if mode == Sources.SESSION:
        list_sessions = [src]

    elif mode == Sources.FOLDER:
        list_sessions = sorted(list(src.iterdir()))
    
    elif mode == Sources.CSV_SESSION:
        if src.exists():
            df_ses = pd.read_csv(src)
            list_sessions = [Path(row.root_folder, row.session_name) for row in df_ses.itertuples(index=False)]

    return list_sessions

def get_processed_folders_to_upload(opt) -> tuple[list, bool]:
    """ Parse input for processed folder """
    if opt.upload_processeddata == "": return [], False

    folder_to_upload, needFrames = [], False
    for letter in opt.upload_processeddata:
        if letter == "f": needFrames = True
        elif letter == "d": folder_to_upload.append("DCIM")
        elif letter == "m": folder_to_upload.append("METADATA")
        elif letter == "g": folder_to_upload.append("GPS")
        elif letter == "b": folder_to_upload.append("PROCESSED_DATA/BATHY")
        elif letter == "i": folder_to_upload.append("PROCESSED_DATA/IA")
        elif letter == "p": folder_to_upload.append("PROCESSED_DATA/PHOTOGRAMMETRY")
        elif letter == "c": folder_to_upload.append("PROCESSED_DATA/CPCE_ANNOTATION")
    return folder_to_upload, needFrames

def get_custom_folders_to_upload(opt) -> list:
    """ Parse input for custom folder """
    if opt.upload_custom == "": return []

    folder_to_upload = []
    for letter in opt.upload_custom:
        if letter == "f": folder_to_upload.append("PROCESSED_DATA/FRAMES")
        if letter == "d": folder_to_upload.append("DCIM")
        elif letter == "m": folder_to_upload.append("METADATA")
        elif letter == "g": folder_to_upload.append("GPS")
        elif letter == "b": folder_to_upload.append("PROCESSED_DATA/BATHY")
        elif letter == "i": folder_to_upload.append("PROCESSED_DATA/IA")
        elif letter == "p": folder_to_upload.append("PROCESSED_DATA/PHOTOGRAMMETRY")
        elif letter == "c": folder_to_upload.append("PROCESSED_DATA/CPCE_ANNOTATION")
        elif letter == "s": folder_to_upload.append("SENSORS")
    
    return folder_to_upload

def clean_doi(doi) -> str | None:
    # check for doi is not float nan
    if doi != doi or doi in ["", None, np.nan]: return None

    doi = str(doi)
    # In case user take the whole url 
    if "zenodo." in doi:
        doi = doi.split("zenodo.")[1]
    return doi

def get_session_name_doi_from_opt(opt) -> list[tuple[str | None, str | None]]:
    """ Return a list who contains tuple (name, doi)"""

    def clean_name(name):
        if name in ["", None, np.nan]: return None
        return name.replace("urn:", "")

    list_name_doi = []
    if opt.enable_doi:
        doi = clean_doi(opt.enable_doi)
        list_name_doi.append((None, doi))
    
    if opt.enable_name:
        name = clean_name(opt.enable_name)
        list_name_doi.append((name, None))
    
    if opt.enable_csv:
        csv_path = Path(opt.path_csv_file)
        if Path.exists(csv_path):
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                name = clean_name(row["session_name"]) if "session_name" in row else None
                doi = clean_doi(row["doi"]) if "doi" in row else None
                list_name_doi.append((name, doi))

    return list_name_doi


def get_doi_from_custom_frames_csv(opt) -> dict[str, list[str]]:
    """ Extract doi from custom_frames_csv """

    csv_path = Path(opt.path_custom_frames_csv)
    if not Path.exists(csv_path) or not csv_path.is_file(): return {}
    
    df = pd.read_csv(csv_path)
    if "version_doi" not in df or "relative_file_path" not in df:
        print("If you want to download specific frames, you will need to have version_doi column and relative_file_path column.")
        return {}

    data = {}
    for doi_unformatted in list(set(df["version_doi"].to_list())):
        doi = clean_doi(doi_unformatted)
        if doi == None: continue

        frames = df[df["version_doi"] == doi_unformatted]["relative_file_path"].to_list()
        data[doi] = frames
    return data


def md5(fname: Path) -> str:
    """ Return md5 checksum of a file. """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def haversine(lat1, lon1, lat2, lon2):
    """ Compute the distance between two points in degrees in meters """
    R = 6371000  # Eartch radius in meters.
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c

# https://docs.digi.com/resources/documentation/digidocs/90001488-13/reference/r_iso_8601_duration_format.htm
def compute_duration_iso8601(start_date: datetime, stop_date: datetime) -> str:
    """ Compute duration and return it in iso8601 format like P3DT4H"""

    elapsed_time = stop_date - start_date
    seconds_elapsed = elapsed_time.seconds

    hours = seconds_elapsed // 3600
    minutes = (seconds_elapsed % 3600) // 60
    seconds = seconds_elapsed % 60 

    string_iso8601 = ""
    if elapsed_time.days > 0:
        string_iso8601 = f"P{elapsed_time.days}DT{hours}H{minutes}M{seconds}S"
    else:
        string_iso8601 = f"PT{hours}H{minutes}M{seconds}S"

    return string_iso8601


def compute_duration(start_date: datetime, stop_date: datetime) -> str:
    """ Compute the duration and return in format like 1 day 00h 32min 15sec """

    elapsed_time = stop_date - start_date
    seconds_elapsed = elapsed_time.seconds

    hours = seconds_elapsed // 3600
    minutes = (seconds_elapsed % 3600) // 60
    seconds = seconds_elapsed % 60

    datestring = ""
    if elapsed_time.days == 1:
        datestring += f"{elapsed_time.days} day "
    elif elapsed_time.days > 1:
        datestring += f"{elapsed_time.days} days "
    
    datestring += f"{hours}h {minutes}min {seconds}sec"

    return datestring