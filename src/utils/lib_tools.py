import enum
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path

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