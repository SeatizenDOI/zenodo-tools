import json
import argparse
import traceback
from pathlib import Path
import requests

from utils.constants import TMP_PATH
from utils.PlanchaSession import PlanchaSession
from utils.ZenodoUploader import ZenodoUploader
from utils.PlanchaMetadata import PlanchaMetadata
from utils.lib_tools import get_session_name_doi_from_opt

"""
conceptrecid:11162064
id:11162065
urn:20231208_REU-ST-LEU_ASV-1_01 

"""

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
    parser.add_argument("-pout", "--path_folder_out", default="/tmp", help="Output folder to rebuild sessions")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")

    return parser.parse_args()

def main(opt):
    
    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)
    
    # Stat
    sessions_fail = []
    list_name_doi = get_session_name_doi_from_opt(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_name_doi) else 0

    for i, (session_name, doi) in enumerate(list_name_doi[index_start:]):

        # It's more easier to work with doi
        if doi == None and session_name == None:
            print(f"-- [WARNING] No doi or name found at line {i+2}") # Start counting at 1 and omit csv header
            continue
        
        # We need to retrieve the parent id of the
        if session_name and doi == None:
            pass
        print(session_name, doi)

        try:
            pass
        
        except Exception:
            print(traceback.format_exc(), end="\n\n")

            # sessions_fail.append(session_path.name)

    # Stat
    # print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_session), len(sessions_fail)))
    if (len(sessions_fail)):
        [print("\t* " + session_name) for session_name in sessions_fail]

if __name__ == "__main__":
    opt = parse_args()
    main(opt)