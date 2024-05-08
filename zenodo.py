import json
import argparse
import traceback
from pathlib import Path

from utils.constants import TMP_PATH
from utils.PlanchaSession import PlanchaSession
from utils.ZenodoUploader import ZenodoUploader
from utils.PlanchaMetadata import PlanchaMetadata
from utils.lib_tools import get_list_sessions, get_folders_from_output

def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-tools", description="Workflow to upload raw data and processed data with metadata")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-efol", "--enable_folder", action="store_true", help="Work from a folder of session")
    arg_input.add_argument("-eses", "--enable_session", action="store_true", help="Work with one session")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    arg_input.add_argument("-eno", "--enable_nothing", action="store_true", help="Use with clean parameter")

    # Path of input.
    parser.add_argument("-pfol", "--path_folder", default="/home/bioeos/Documents/Bioeos/plancha-session", help="Folder of session")
    parser.add_argument("-pses", "--path_session", default="/home/bioeos/Documents/Bioeos/plancha-session/20240314_REU-SAINTLEU_ASV-1_02", help="One session")
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/test.csv", help="Session from csv file")

    # Data type to upload.
    parser.add_argument("-ur", "--upload-rawdata", action="store_true", help="Upload raw data from a session")
    parser.add_argument("-up", "--upload-processeddata", default="", help="Specify folder to upload f: FRAMES, m: METADATA, b: BATHY, g: GPS, i: IA | Ex: '-up fi' for upload frames and ia ")
    parser.add_argument("-um", "--update-metadata", action="store_true", help="Update metadata from a session")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")
    parser.add_argument("-cd", "--clean_draft", action="store_true", help="Clean all draft with no version published")

    return parser.parse_args()

def main(opt):

    # Open json file with metadata of the session.
    with open('./metadata.json') as json_file:
        metadata_json = json.load(json_file)
    
    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)

    # Action on zenodo without specific session
    if opt.enable_nothing:
        if opt.clean_draft:
            uploader = ZenodoUploader("", config_json)
            uploader.clean_draft_no_version()
        return 
    
    # Stat
    sessions_fail = []
    list_session = get_list_sessions(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_session) else 0

    for session_path in list_session[index_start:]:
        session_path = Path(session_path)

        try:
            if not Path.exists(session_path):
                print(f"Session not found for {session_path.name}")
                continue
            
            print(f"\n\nWorking with session {session_path.name}")
            
            plancha_session = PlanchaSession(session_path, TMP_PATH)
            plancha_metadata = PlanchaMetadata(plancha_session, metadata_json)
            uploader = ZenodoUploader(plancha_session.session_name, config_json)

            if opt.upload_rawdata:
                # Prepape raw data
                folders_to_upload = plancha_session.prepare_raw_data()
                raw_metadata = plancha_metadata.build_for_raw()

                for i, folder_to_upload in enumerate(folders_to_upload):
                    if i == 0:
                        uploader.create_deposit_on_zenodo(folder_to_upload, raw_metadata) # RAW_DATA
                    else:
                        raw_metadata["metadata"]["version"] = f"RAW_DATA_{i+1}"
                        uploader.add_new_version_to_deposit(folder_to_upload, raw_metadata) # RAW_DATA_2, RAW_DATA_3, ...
                plancha_session.cleanup()
            
            if opt.upload_processeddata:
                # Processed data
                folders, needFrames = get_folders_from_output(opt)
                plancha_session.prepare_processed_data(folders, needFrames)
                processed_metadata = plancha_metadata.build_for_processed_data()
                uploader.add_new_version_to_deposit(plancha_session.temp_folder, processed_metadata)
                plancha_session.cleanup()
            
            if opt.update_metadata:
                if uploader.deposit_id == None:
                    print("With no id, we cannot update our data, continue")
                    continue
                processed_metadata = plancha_metadata.build_for_processed_data()
                uploader.edit_metadata(processed_metadata)
        
        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append(session_path.name)

            # Avoid tmp folder over charge
            plancha_session.cleanup()

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_session), len(sessions_fail)))
    if (len(sessions_fail)):
        [print("\t* " + session_name) for session_name in sessions_fail]

if __name__ == "__main__":
    opt = parse_args()
    main(opt)