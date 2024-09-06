import shutil
import traceback
from pathlib import Path

from ..seatizen_session.ss_manager import SessionManager

from ..zenodo_api.za_token import ZenodoAPI
from ..zenodo_api.za_tokenless import get_version_from_doi, download_manager_without_token, get_version_from_session_name

from .lib_tools import get_session_name_doi_from_opt, get_doi_from_custom_frames_csv

def download_with_token(opt, config_json: dict) -> None:
    print("Using downloader with token")

    # Create output_folder
    path_output = Path(opt.path_folder_out)
    path_output.mkdir(exist_ok=True, parents=True)
    
    # Stat.
    sessions_fail = []
    list_name_doi = get_session_name_doi_from_opt(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_name_doi) else 0
    index_position = int(opt.index_position)-1 if opt.index_position.isnumeric() and \
                                            int(opt.index_position) > 0 and \
                                            int(opt.index_position) <= len(list_name_doi) else -1
    selected_name_doi = list_name_doi[index_start:] if index_position == -1 else [list_name_doi[index_position]]
    
    for i, (session_name, doi) in enumerate(selected_name_doi):
        try:
            print(f"\n\nWorking with input: session name {session_name} and doi {doi}")
            zenodoAPI, conceptrecid = None, None
            if doi:
                zenodoAPI = ZenodoAPI("", config_json)
                conceptrecid = zenodoAPI.get_conceptrecid_from_idOrConceptrecid(doi)
                if conceptrecid == None: zenodoAPI = None
            
            if session_name and zenodoAPI == None:
                zenodoAPI = ZenodoAPI(session_name, config_json)
                if zenodoAPI.deposit_id == None:
                    raise NameError(f"No id for session name {session_name}")
                conceptrecid = zenodoAPI.get_conceptrecid_specific_deposit()
            
            if conceptrecid == None:
                raise NameError(f"Cannot find conceptrecid so continue")
            
            print(f"Conceptid: {conceptrecid}")

            raw_data_ids, processed_data_ids, _ = zenodoAPI.get_all_version_ids_for_deposit(conceptrecid)
            
            for id in raw_data_ids if opt.download_rawdata else []:
                print(f"Working for RAW DATA Version {id}")
                zenodoAPI.deposit_id = id
                zenodoAPI.zenodo_download_files(path_output)

            # For processed data we don't need to download all version but only the last or the specified one.
            if opt.download_processed_data and len(processed_data_ids) != 0:
                id_processed_data = doi if doi and doi in processed_data_ids else max(processed_data_ids)
                
                print(f"Working for PROCESSED DATA Version {id_processed_data}")
                zenodoAPI.deposit_id = id_processed_data
                zenodoAPI.zenodo_download_files(path_output)

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append((i, session_name, doi))

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(selected_name_doi), len(sessions_fail)))
    if (len(sessions_fail)):
        [print(f"\t* {i}, {session_name}, {doi} failed") for i, session_name, doi in sessions_fail]



def download_without_token(opt) -> None:
    print("Using downloader without token")
    
    # Create output_folder
    path_output = Path(opt.path_folder_out)
    path_output.mkdir(exist_ok=True, parents=True)

    # Stat.
    sessions_fail = []
    list_name_doi = get_session_name_doi_from_opt(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_name_doi) else 0
    index_position = int(opt.index_position)-1 if opt.index_position.isnumeric() and \
                                            int(opt.index_position) > 0 and \
                                            int(opt.index_position) <= len(list_name_doi) else -1
    selected_name_doi = list_name_doi[index_start:] if index_position == -1 else [list_name_doi[index_position]]

    for i, (session_name, doi) in enumerate(selected_name_doi):
        try:
            if doi == None and session_name == None:
                print("No doi or session_name provide to find session.")
                continue
            
            version_json = get_version_from_doi(doi) if doi != None else get_version_from_session_name(session_name)
            if version_json == {} or "files" not in version_json:
                continue
            list_files = version_json["files"]

            # Continue if no files to download due to access_right not open.
            if len(list_files) == 0 and version_json["metadata"]["access_right"] != "open":
                print("[WARNING] No files to download, version is not open.")
                continue
            
            # In case we get a conceptrecid from the user, get doi
            doi = version_json["id"]

            # Get session_name.
            if session_name == None:
                try:
                    for identifier_obj in version_json["metadata"]["alternate_identifiers"]:
                        if "urn:" in identifier_obj["identifier"]:
                            session_name = identifier_obj["identifier"].replace("urn:", "")
                            break
                except Exception:
                    pass

            if session_name == None:
                print("[WARNING] Cannot find session_name.")
                session_name = ""

            download_manager_without_token(list_files, path_output, session_name, doi)

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append((i, session_name, doi))

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(selected_name_doi), len(sessions_fail)))
    if (len(sessions_fail)):
        [print(f"\t* {i}, {session_name}, {doi} failed") for i, session_name, doi in sessions_fail]


def download_specific_frames(opt) -> None:
    print("Download specific frames.")
    
    # Create output_folder
    path_output = Path(opt.path_folder_out)
    path_output.mkdir(exist_ok=True, parents=True)

    # Create Frame folder inside output_folder.
    path_frame_folder_output = Path(path_output, "FRAMES")
    path_frame_folder_output.mkdir(exist_ok=True, parents=True)


    # Stat.
    sessions_fail = []
    list_frames_by_doi = get_doi_from_custom_frames_csv(opt)

    # for doi, frames in list_frames_by_doi.items():
    for doi, frames in list_frames_by_doi.items():
        try:
            if doi == None: continue

            version_json = get_version_from_doi(doi)
            if version_json == {} or "files" not in version_json:
                continue
            list_files = version_json["files"]

            # Continue if no files to download due to access_right not open.
            if len(list_files) == 0 and version_json["metadata"]["access_right"] != "open":
                print("[WARNING] No files to download, version is not open.")
                continue
            
            # In case we get a conceptrecid from the user, get doi
            doi = version_json["id"]

            # Get session_name.
            session_name = ""
            try:
                for identifier_obj in version_json["metadata"]["alternate_identifiers"]:
                    if "urn:" in identifier_obj["identifier"]:
                        session_name = identifier_obj["identifier"].replace("urn:", "")
                        break
            except Exception:
                pass

            if session_name == "":
                print("[WARNING] Cannot find session_name.")
            
            # Get the path between the session_name and the frame name.
            session_manager = SessionManager(session_name, path_output)
            frames_folder = session_manager.get_frame_parent_folder(frames)
            frames_zipped_folder = f'{frames_folder.replace("/", "_")}.zip'
            frames_name = [Path(frame).name for frame in frames]

            # Get which folder to download.
            file_to_download = []
            for file in list_files:
                if file["key"] == frames_zipped_folder:
                    file_to_download.append(file)

            # Download it.
            download_manager_without_token(file_to_download, path_output, session_name, doi)

            # Move frame.
            for file in Path(path_output, session_name, frames_folder).iterdir():
                if file.name not in frames_name: continue # Move only frame in csv file.
                shutil.move(file, Path(path_frame_folder_output, file.name))

            # Remove folder.
            shutil.rmtree(Path(path_output, session_name))

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append(doi)
    
    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_frames_by_doi), len(sessions_fail)))
    if (len(sessions_fail)):
        [print(f"\t* {doi} failed") for  doi in sessions_fail]
    return