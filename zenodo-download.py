import json
import argparse
from pathlib import Path

from src.utils.lib_download import download_specific_frames, download_with_token, download_without_token

def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-download", description="Workflow to download raw data and processed data with metadata")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-edoi", "--enable_doi", default=None, help="Take a doi")
    arg_input.add_argument("-ename", "--enable_name", default=None, help="Work from a session name")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    arg_input.add_argument("-ecf", "--enable_custom_frames", action="store_true", help="Work from csv to get specific frames")
    
    # Path of input.
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/download_example.csv", help="Path to the csv file, header can be session_name or doi or both")
    parser.add_argument("-pcf", "--path_custom_frames_csv", default="./csv_inputs/demo_seatizen_monitoring.csv", help="Work with a csv file with FileName and version_doi inside to get specific frames.")

    # Path of output.
    parser.add_argument("-po", "--path_folder_out", default="/tmp/00_test_download", help="Output folder to rebuild sessions")

    # Data type to download.
    parser.add_argument("-dr", "--download_rawdata", action="store_true", help="Download raw data from a session")
    parser.add_argument("-dp", "--download_processed_data", action="store_true", help="Download processed data from a session")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start")

    return parser.parse_args()


def main(opt):
    
    if opt.enable_custom_frames:
        download_specific_frames(opt)
        return

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