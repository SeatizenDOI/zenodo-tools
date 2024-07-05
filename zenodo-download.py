import json
import argparse
import traceback
from pathlib import Path

from src.zenodo_api.za_token import ZenodoAPI
from src.zenodo_api.za_tokenless import get_version_from_doi, download_manager_without_token

from src.utils.lib_tools import get_session_name_doi_from_opt

def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-download", description="Workflow to download raw data and processed data with metadata")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-edoi", "--enable_doi", default=None, help="Take a doi")
    arg_input.add_argument("-ename", "--enable_name", default=None, help="Work from a session name")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    
    # Path of input.
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/download_example.csv", help="Path to the csv file, header can be session_name or doi or both")

    # Path of output.
    parser.add_argument("-pout", "--path_folder_out", default="/tmp/00_test_download", help="Output folder to rebuild sessions")

    # Data type to download.
    parser.add_argument("-dr", "--download_rawdata", action="store_true", help="Download raw data from a session")
    parser.add_argument("-dp", "--download_processed_data", action="store_true", help="Download processed data from a session")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")

    return parser.parse_args()


def download_with_token(opt, config_json: dict) -> None:
    print("Using downloader with token")

    # Create output_folder
    path_output = Path(opt.path_folder_out)
    path_output.mkdir(exist_ok=True, parents=True)
    
    # Stat.
    sessions_fail = []
    list_name_doi = get_session_name_doi_from_opt(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_name_doi) else 0

    for i, (session_name, doi) in enumerate(list_name_doi[index_start:]):
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

            raw_data_ids, processed_data_ids = zenodoAPI.get_all_version_ids_for_deposit(conceptrecid)
            
            for id in raw_data_ids if opt.download_rawdata else []:
                print(f"Working for RAW DATA Version {id}")
                zenodoAPI.deposit_id = id
                zenodoAPI.zenodo_download_files(path_output)

            # For processed data we don't need to download all version but only the last or the specified one.
            if opt.download_processed_data:
                id_processed_data = doi if doi and doi in processed_data_ids else max(processed_data_ids)
                
                print(f"Working for PROCESSED DATA Version {id_processed_data}")
                zenodoAPI.deposit_id = id_processed_data
                zenodoAPI.zenodo_download_files(path_output)

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append((i, session_name, doi))

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_name_doi), len(sessions_fail)))
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

    for i, (session_name, doi) in enumerate(list_name_doi[index_start:]):
        try:
            if doi == None:
                print("Cannot find session without doi when you don't provide token.")
                continue
            
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

            download_manager_without_token(list_files, path_output, session_name, doi)

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append((i, session_name, doi))

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_name_doi), len(sessions_fail)))
    if (len(sessions_fail)):
        [print(f"\t* {i}, {session_name}, {doi} failed") for i, session_name, doi in sessions_fail]


def main(opt):
    
    # Return if no choice
    if not opt.download_rawdata and not opt.download_processed_data:
        print("[WARNING] Please choose if you want to reconstruct raw data or processed data or both.")
        return

    config_path = Path('./config.json')
    if not Path.exists(config_path) or not config_path.is_file():
        download_without_token(opt)

    else:
        # Open json file with zenodo token.
        with open(config_path) as json_file:
            config_json = json.load(json_file)
        
        download_with_token(opt, config_json)

if __name__ == "__main__":
    opt = parse_args()
    main(opt)