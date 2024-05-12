import json
import argparse
import traceback

from utils.lib_tools import get_session_name_doi_from_opt

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
    parser.add_argument("-dr", "--download-rawdata", action="store_true", help="Download raw data from a session")
    parser.add_argument("-dp", "--download-processed_data", action="store_true", help="Download processed data from a session")

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
        """
            On cherche à reconstruire une session brute ou non.

            Si on passe juste un name ou un conceptrecid
                => Dernière session processed_data si elle existe
            Si on passe un id en particulier
                => Processed data renseigner et si c'est un id de raw data, dernier processed data s'il existe
        
        """
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