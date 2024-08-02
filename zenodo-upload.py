import json
import argparse
import traceback
from pathlib import Path

from src.zenodo_api.za_token import ZenodoAPI
from src.seatizen_session.ss_manager import SessionManager
from src.seatizen_session.ss_metadata import SessionMetadata
from src.utils.constants import TMP_PATH, RESTRICTED_FILES
from src.utils.lib_tools import get_list_sessions, get_processed_folders_to_upload, get_custom_folders_to_upload

def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-upload", description="Workflow to upload raw data and processed data with metadata")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-efol", "--enable_folder", action="store_true", help="Work from a folder of session")
    arg_input.add_argument("-eses", "--enable_session", action="store_true", help="Work with one session")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    arg_input.add_argument("-eno", "--enable_nothing", action="store_true", help="Didn't take a session, use with clean parameter")

    # Path of input.
    parser.add_argument("-pfol", "--path_folder", default="/home/bioeos/Documents/Bioeos/plancha-session", help="Path to folder of session")
    parser.add_argument("-pses", "--path_session", default="/media/bioeos/F/202210_plancha_session/20221020_SYC-ALDABRA-ARM01_ASV-01_00/", help="Path to the session")
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/retry.csv", help="Path to the csv file")

    # Data type to upload or update.
    parser.add_argument("-ur", "--upload-rawdata", action="store_true", help="Upload raw data from a session")
    parser.add_argument("-up", "--upload-processeddata", default="", help="Specify folder to upload f: FRAMES, m: METADATA, b: BATHY, g: GPS, i: IA | Ex: '-up fi' for upload frames and ia ")
    parser.add_argument("-um", "--update-metadata", action="store_true", help="Update metadata from a session") # ! Caution could be dangerous when we get multiple processed version
    
    parser.add_argument("-uc", "--upload-custom", action="store_true", help="Upload custom data. Specify folder to upload f: FRAMES, m: METADATA, b: BATHY, g: GPS, i: IA, d: DCIM, s: SENSORS")
    parser.add_argument("-umc", "--update-metadata-custom", action="store_true", help="Update custom metadata from a session")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")
    parser.add_argument("-cd", "--clean_draft", action="store_true", help="Clean all draft with no version published")
    parser.add_argument("-pmj", "--path_metadata_json", default="./metadata/metadata.json", help="Path to metadata json file")
    

    return parser.parse_args()

def main(opt):

    # Open json file with metadata of the session.
    metadata_json_path = Path(opt.path_metadata_json)
    if not Path.exists(metadata_json_path) or not metadata_json_path.is_file():
        print("Cannot find metadata file.")
        return

    with open(metadata_json_path) as json_file:
        metadata_json = json.load(json_file)
    
    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)

    # Action on zenodo without specific session
    if opt.enable_nothing:
        if opt.clean_draft:
            zenodoAPI = ZenodoAPI("", config_json)
            zenodoAPI.clean_draft_no_version()
        return 
    
    # Zenodo API
    zenodoAPI = ZenodoAPI("", config_json)

    # Stat
    sessions_fail = []
    list_session = get_list_sessions(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_session) else 0

    for session_path in list_session[index_start:]:
  
        try:
            if not Path.exists(session_path):
                print(f"Session not found for {session_path.name}")
                continue
            
            print(f"\n\nWorking with session {session_path.name}")
            
            plancha_session = SessionManager(session_path, TMP_PATH)
            plancha_metadata = SessionMetadata(plancha_session, metadata_json)
            zenodoAPI.update_current_session(plancha_session.session_name)

            if opt.upload_rawdata:
                if zenodoAPI.deposit_id != None:
                    print(f"We already have a deposit with the same urn: https://zenodo.org/records/{zenodoAPI.deposit_id}")
                    continue
                    
                folders_to_upload = plancha_session.prepare_raw_data()
                raw_metadata = plancha_metadata.build_for_raw()

                for i, folder_to_upload in enumerate(folders_to_upload):
                    if i == 0:
                        zenodoAPI.create_deposit_on_zenodo(folder_to_upload, raw_metadata) # RAW_DATA
                    else:
                        zenodoAPI.add_new_version_to_deposit(folder_to_upload, raw_metadata, RESTRICTED_FILES) # RAW_DATA_2, RAW_DATA_3, ...
                plancha_session.cleanup()
            
            if opt.upload_processeddata:
                folders, needFrames = get_processed_folders_to_upload(opt)
                plancha_session.prepare_processed_data(folders, needFrames, with_file_at_root_folder=True)
                processed_metadata = plancha_metadata.build_for_processed_data()
                zenodoAPI.add_new_version_to_deposit(plancha_session.temp_folder, processed_metadata, RESTRICTED_FILES, dontUploadWhenLastVersionIsProcessedData=True)
                plancha_session.cleanup()
            
            if opt.update_metadata:
                if zenodoAPI.deposit_id == None:
                    print("With no id, we cannot update our data, continue")
                    continue

                raw_data_ids, processed_data_ids = zenodoAPI.get_all_version_ids_for_deposit(zenodoAPI.get_conceptrecid_specific_deposit())

                # Update metadata for raw data
                print("-- Editing raw data version")
                raw_metadata = plancha_metadata.build_for_raw()
                for id in raw_data_ids:
                    print(f"Working with id {id}")
                    zenodoAPI.deposit_id = id
                    zenodoAPI.edit_metadata(raw_metadata)
                
                # Update metadata for processed data
                print("-- Editing processed data version")
                processed_metadata = plancha_metadata.build_for_processed_data()
                for id in processed_data_ids:
                    print(f"Working with id {id}")
                    zenodoAPI.deposit_id = id
                    zenodoAPI.edit_metadata(processed_metadata)
        
            if opt.upload_custom:
                folders_to_zip = get_custom_folders_to_upload(opt)
                plancha_session.prepare_custom_data(folders_to_zip)
                custom_metadata = plancha_metadata.build_for_custom() 

                if zenodoAPI.deposit_id == None:
                    # No deposit found, create a new one
                    zenodoAPI.create_deposit_on_zenodo(plancha_session.temp_folder, custom_metadata)
                else:
                    # Session have already a deposit, so we add a new version.
                    zenodoAPI.add_new_version_to_deposit(plancha_session.temp_folder, custom_metadata)
                plancha_session.cleanup()
            
            if opt.update_metadata_custom:
                if zenodoAPI.deposit_id == None:
                    print("With no id, we cannot update our data, continue")
                    continue
                
                custom_metadata = plancha_metadata.build_for_custom() 
                raw_data_ids, processed_data_ids = zenodoAPI.get_all_version_ids_for_deposit(zenodoAPI.get_conceptrecid_specific_deposit())
                for id in raw_data_ids + processed_data_ids:
                    print(f"Working with id {id}")
                    zenodoAPI.deposit_id = id
                    zenodoAPI.edit_metadata(custom_metadata)            

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