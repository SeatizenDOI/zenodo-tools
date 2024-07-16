import json
import argparse
import traceback
from pathlib import Path

from src.utils.lib_tools import get_list_sessions

from src.seatizen_atlas.sa_manager import AtlasManager
from src.seatizen_atlas.sa_metadata import seatizen_atlas_metadata


def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-manager", description="Workflow to manage global deposit")

    # Input.
    arg_input = parser.add_mutually_exclusive_group(required=True)
    arg_input.add_argument("-efol", "--enable_folder", action="store_true", help="Work from a folder of session")
    arg_input.add_argument("-eses", "--enable_session", action="store_true", help="Work with one session")
    arg_input.add_argument("-ecsv", "--enable_csv", action="store_true", help="Work from csv")
    arg_input.add_argument("-eno", "--enable_nothing", action="store_true", help="Use with generate")

    # Path of input.
    parser.add_argument("-pfol", "--path_folder", default="/home/bioeos/Documents/Bioeos/plancha-session", help="Path to folder of session")
    parser.add_argument("-pses", "--path_session", default="/home/bioeos/Documents/Bioeos/plancha-session/20240517_REU-TROU-DEAU_ASV-1_01/", help="Path to the session")
    parser.add_argument("-pcsv", "--path_csv_file", default="./csv_inputs/test.csv", help="Path to the csv file")

    # Mode.
    parser.add_argument("-ulo", "--use_from_local", action="store_true", help="Work from a local folder. Update if exists else Create. Default behaviour is to download data from zenodo.")
    parser.add_argument("-um", "--update_metadata", action="store_true", help="Update last version metadata")
    
    parser.add_argument("-la", "--load_annotations", default=None, help="If not none, try to load all annotations in path. Can be a file or a folder of files")
    parser.add_argument("-at", "--annotation_type", default="multilabel", help="Annotation type to parse. Default multilabel")

    # Seatizen Atlas path.
    parser.add_argument("-psa", "--path_seatizen_atlas_folder", default="./seatizen_atlas_folder", help="Folder to store data")
    parser.add_argument("-pmj", "--path_metadata_json", default="./metadata/metadata_seatizen_atlas.json", help="Path to metadata file")

    # Optional arguments.
    parser.add_argument("-is", "--index_start", default="0", help="Choose from which index to start.")
    parser.add_argument("-fr", "--force_regenerate", action="store_true", help="Regenerate gpkg file from scracth even if exist.")

    return parser.parse_args()

def main(opt):

    config_path, config_json = Path('./config.json'), {}
    if not Path.exists(config_path) or not config_path.is_file():
        print("No config file found, you cannot upload the result on zenodo.")
    else:
        # Open json file with zenodo token.
        with open(config_path) as json_file:
            config_json = json.load(json_file)

    if opt.update_metadata:
        if config_json == {}:
            print("Cannot update metadata without zenodo token")
        else:
            seatizen_atlas_metadata(config_json, opt.path_metadata_json)
        return

    seatizenManager = AtlasManager(config_json, opt.path_seatizen_atlas_folder, opt.use_from_local, opt.force_regenerate)

    if not opt.enable_nothing:
        sessions_fail = []
        list_session = get_list_sessions(opt)
        index_start = int(opt.index_start) if opt.index_start.isnumeric() and int(opt.index_start) < len(list_session) else 0
        
        for session_path in list_session[index_start:]:

            try:
                if not Path.exists(session_path):
                    print(f"Session not found for {session_path.name}")
                    continue
                
                print(f"\n\nWorking with session {session_path.name}")
                seatizenManager.import_session(session_path)


            except Exception:
                print(traceback.format_exc(), end="\n\n")

                sessions_fail.append(session_path.name)

        # Stat
        print("\nEnd of process. On {} sessions, {} fails. ".format(len(list_session), len(sessions_fail)))
        if (len(sessions_fail)):
            [print("\t* " + session_name) for session_name in sessions_fail]
    
    # Import annotation
    if opt.load_annotations != None:
        seatizenManager.load_annotation_files(opt.load_annotations, opt.annotation_type)

    # Export all value we wants.
    seatizenManager.export_csv()
    
    # Upload all data.
    # seatizenManager.publish(opt.path_metadata_json)

    # Close database connection.
    seatizenManager.sql_connector.close()

if __name__ == "__main__":
    opt = parse_args()
    main(opt)
