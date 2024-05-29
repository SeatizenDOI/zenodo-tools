import enum
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path

class Sources(enum.Enum):
    CSV_SESSION = 0
    FOLDER = 1
    SESSION = 2

def get_mode_from_opt(opt) -> Sources:
    """ Retrieve mode from input option """
    mode = None

    if opt.enable_csv: 
        mode = Sources.CSV_SESSION
    elif opt.enable_folder: 
        mode = Sources.FOLDER
    elif opt.enable_session: 
        mode = Sources.SESSION

    return mode

def get_src_from_mode(mode, opt) -> str:
    """ Retrieve src path from mode """
    src = ""

    if mode == Sources.CSV_SESSION:
        src = opt.path_csv_file
    elif mode == Sources.FOLDER:
        src = opt.path_folder
    elif mode == Sources.SESSION:
        src = opt.path_session

    return src

def get_list_sessions(opt) -> list:
    """ Retrieve list of sessions from input """

    list_sessions = []

    mode = get_mode_from_opt(opt)
    src = get_src_from_mode(mode, opt)

    if mode == Sources.SESSION:
        list_sessions = [src]

    elif mode == Sources.FOLDER:
        list_sessions = sorted(list(Path(src).iterdir()))
    
    elif mode == Sources.CSV_SESSION:
        src = Path(src)
        if Path.exists(src):
            df_ses = pd.read_csv(src)
            list_sessions = [str(Path(row.root_folder, row.session_name)) for row in df_ses.itertuples(index=False)]

    return list_sessions

def get_processed_folders_to_upload(opt):
    """ Parse input for processed folder """
    if opt.upload_processeddata == "": return [], False

    folder_to_upload, needFrames = [], False
    for letter in opt.upload_processeddata:
        if letter == "f": needFrames = True
        elif letter == "m": folder_to_upload.append("METADATA")
        elif letter == "g": folder_to_upload.append("GPS")
        elif letter == "b": folder_to_upload.append("PROCESSED_DATA/BATHY")
        elif letter == "i": folder_to_upload.append("PROCESSED_DATA/IA")
    
    return folder_to_upload, needFrames

def get_session_name_doi_from_opt(opt):
    """ Return a list who contains tuple (name, doi)"""

    def clean_doi(doi):
        if doi != doi or doi in ["", None, np.nan]: return None

        # In case user take the whole url 
        if "zenodo." in doi:
            doi = doi.split("zenodo.")[1]
        return int(doi)
    
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

def md5(fname):
    """ Return md5 checksum of a file. """
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()