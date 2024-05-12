import json
import argparse
import traceback
from pathlib import Path

from utils.constants import TMP_PATH
from utils.ZenodoAPI import ZenodoAPI
from utils.lib_tools import get_list_sessions
from utils.PlanchaSession import PlanchaSession
from utils.SeatizenManager import SeatizenManager


def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-manager", description="Workflow to manage global deposit")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-efol", "--enable_folder", action="store_true", help="Work from a folder of session")
    arg_input.add_argument("-eses", "--enable_session", action="store_true", help="Work with one session")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    arg_input.add_argument("-eno", "--enable_nothing", action="store_true", help="Didn't take a session, use with clean parameter")

    # Path of input.
    parser.add_argument("-pfol", "--path_folder", default="/home/bioeos/Documents/Bioeos/plancha-session", help="Path to folder of session")
    parser.add_argument("-pses", "--path_session", default="/home/bioeos/Documents/Bioeos/plancha-session/20240314_REU-SAINTLEU_ASV-1_02", help="Path to the session")
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/test.csv", help="Path to the csv file")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")

    return parser.parse_args()

def main(opt):
    
    # Open json file with metadata of the session.
    with open('./metadata.json') as json_file:
        metadata_json = json.load(json_file)

    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)

    # Load metadata manager
    seatizenManager = SeatizenManager(config_json, metadata_json)

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
            
            # Update session_doi.csv
            print("-- Add doi in session_doi.csv.")
            zenodoAPI = ZenodoAPI(plancha_session.session_name, config_json)
            if zenodoAPI.deposit_id:
                seatizenManager.add_to_session_doi(plancha_session.session_name, zenodoAPI.get_conceptrecid_specific_deposit())
            else:
                print("[WARNING] Session without conceptid, may be in draft or not on zenodo.")

            # Get all frames metadata for the session (read predictions_gps.csv)
            print("-- Grab frame metadata.")
            predictions_gps = plancha_session.get_predictions_gps()
            if predictions_gps:
                seatizenManager.add_to_metadata_image(predictions_gps)
            else:
                print("[WARNING] No decent image metadata to upload.")

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append(session_path.name)

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_session), len(sessions_fail)))
    if (len(sessions_fail)):
        [print("\t* " + session_name) for session_name in sessions_fail]
    
    # Save and published change.
    seatizenManager.save_and_published()

if __name__ == "__main__":
    opt = parse_args()
    main(opt)