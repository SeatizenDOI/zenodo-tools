import json
import argparse
import traceback
from pathlib import Path

from utils.ZenodoAPI import ZenodoAPI
from utils.lib_tools import get_session_name_doi_from_opt
from utils.constants import TMP_PATH_DOWNLOADER

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

    # Data type to download.
    parser.add_argument("-dr", "--download_rawdata", action="store_true", help="Download raw data from a session")
    parser.add_argument("-dp", "--download_processed_data", action="store_true", help="Download processed data from a session")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")

    return parser.parse_args()

def main(opt):
    
    # Return if no choice
    if not opt.download_rawdata and not opt.download_processed_data:
        print("[WARNING] Please choose if you want to reconstruct raw data or processed data or both.")
        return

    # Create output_folder
    path_output = Path(opt.path_folder_out)
    path_output.mkdir(exist_ok=True, parents=True)

    # Open json file with zenodo token.
    with open('./config.json') as json_file:
        config_json = json.load(json_file)
    
    # Stat.
    sessions_fail = []
    list_name_doi = get_session_name_doi_from_opt(opt)
    index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_name_doi) else 0

    for i, (session_name, doi) in enumerate(list_name_doi[index_start:]):
        """
            On cherche à reconstruire une session brute ou non.

            Si on passe juste un name ou un conceptrecid
                => Dernière session processed_data si elle existe
            Si on passe un id en particulier
                => Processed data renseigner et si c'est un id de raw data, dernier processed data s'il existe
            
            Si on a juste un nom, on a juste à récupérer son id 
        """
        try:
            print(f"\n\nWorking with {session_name} and {doi}")
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
                print(f"Raw data id {id}")
                

            for id in processed_data_ids if opt.download_processed_data else []:
                print(f"Processed data id {id}")

        except Exception:
            print(traceback.format_exc(), end="\n\n")

            sessions_fail.append(i)

    # Stat
    print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_name_doi), len(sessions_fail)))
    if (len(sessions_fail)):
        [print(f"\t* Line {index+2} failed") for index in sessions_fail]

if __name__ == "__main__":
    opt = parse_args()
    main(opt)