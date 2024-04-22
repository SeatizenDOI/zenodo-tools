import json
import argparse
from pathlib import Path

from utils.PlanchaSession import PlanchaSession
from utils.PlanchaMetadata import PlanchaMetadata
from utils.ZenodoUploader import ZenodoUploader

TMP_PATH = "/tmp"
ROOT_FOLDER = Path("/home/bioeos/Documents/Bioeos/plancha-session")

def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-tools", description="Workflow to upload raw data and processed data with metadata")
    parser.add_argument("-ur", "--upload-rawdata", action="store_true", help="Upload raw data from a session")
    parser.add_argument("-up", "--upload-processeddata", action="store_true", help="Upload processed data from a session")
    parser.add_argument("-um", "--update-metadata", action="store_true", help="Update metadata from a session")

    return parser.parse_args()

def main(opt):

    if not Path.exists(ROOT_FOLDER):
        print(f"Root folder doesn't exist")
        return

    # Open json file with metadata of the session.
    with open('./metadata.json') as json_file:
        metadata_json = json.load(json_file)
    
    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)

    for session_path in sorted(list(ROOT_FOLDER.iterdir())):

        if session_path.name != "20231204_REU-TROUDEAU_ASV-1_01": continue

        if not Path.exists(session_path):
            print(f"Session not found for {session_path.name}")
            return
        
        print(f"Working with session {session_path.name}")
        
        plancha_session = PlanchaSession(session_path, TMP_PATH)
        plancha_metadata = PlanchaMetadata(plancha_session, metadata_json)
        uploader = ZenodoUploader(plancha_session.session_name, config_json)

        uploader.get_session_info_by_id(uploader.deposit_id)
        if opt.upload_rawdata:
            # Prepape raw data
            plancha_session.prepare_raw_data()
            raw_metadata = plancha_metadata.build_for_raw()
            uploader.create_deposit_on_zenodo(plancha_session.temp_folder, raw_metadata)
        
        if opt.upload_processeddata:
            # Processed data
            plancha_session.prepare_processed_data(["BATHY", "IA", "FRAMES"])
            processed_metadata = plancha_metadata.build_for_processed_data()
            uploader.add_new_version_to_deposit(plancha_session.temp_folder, processed_metadata)
            plancha_session.cleanup()
        
        if opt.update_metadata:
            processed_metadata = plancha_metadata.build_for_processed_data()
            uploader.edit_metadata(processed_metadata)

if __name__ == "__main__":
    opt = parse_args()
    main(opt)