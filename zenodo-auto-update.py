import json
import time
import shutil
import argparse
import traceback
from pathlib import Path
from datetime import datetime

from src.seatizen_atlas.sa_manager import AtlasManager

from src.utils.lib_tools import increment_semantic_versioning_at_patch_level, SemanticVersioningLevel

from src.utils.constants import ZENODO_LINK_WITHOUT_TOKEN_COMMUNITIES, TMP_PATH

from src.zenodo_api.za_tokenless import get_session_in_communities, download_manager_without_token, get_all_versions_from_session_name

from src.models.deposit_model import DepositDAO, VersionDAO
from src.models.etl_runs_model import ETLRunsDAO



def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-auto-update", description="Try to fetch all the sessions online to populate seatizen atlas.")

    # Communities to fetch
    parser.add_argument("-fc", "--fetch_communities", default=["seatizen-data"], help="List of communities on zenodo to fetch and try to populate SeatizenAtlas.")

    # Seatizen Atlas path.
    parser.add_argument("-psa", "--path_seatizen_atlas_folder", default="./seatizen_atlas_folder", help="Folder to store data")
    parser.add_argument("-pmj", "--path_metadata_json", default="./metadata/metadata_seatizen_atlas.json", help="Path to metadata file")

    return parser.parse_args()

def main(opt):

    config_path, config_json = Path('./config.json'), {}
    if not Path.exists(config_path) or not config_path.is_file():
        print("No config file found, you cannot upload the result on zenodo.")
    else:
        # Open json file with zenodo token.
        with open(config_path) as json_file:
            config_json = json.load(json_file)

    # Change from local if you perform it twice
    seatizenManager = AtlasManager(config_json, opt.path_seatizen_atlas_folder, from_local=True, force_regenerate=False) 
    deposit_manager = DepositDAO()
    version_manager = VersionDAO()
    etl_run_manager = ETLRunsDAO()

    all_deposit_key = [deposit.doi for deposit in list(deposit_manager.deposits)]
    last_etl_run = etl_run_manager.get_last_etl_run()

    sessions_fail, cpt_sessions = [], 0
    for communities in opt.fetch_communities:
        url = f"{ZENODO_LINK_WITHOUT_TOKEN_COMMUNITIES}/{communities}/records"
        print(f"\n\nWorking with communities {communities} using this base url {url} and keeping only session after {last_etl_run.last_zenodo_harvest_at}")

        list_session_in_communities = get_session_in_communities(url, last_etl_run.last_zenodo_harvest_at)
        for i, (conceptrecid, session_name) in enumerate(list_session_in_communities):
            time.sleep(0.5) # Sleep 0.5 sec to avoid hitting max rate limit on Zenodo. 
            cpt_sessions += 1
            try:
                print(f"\n\n({i}/{len(list_session_in_communities)}) Working with session {session_name}")


                # Take all doi concern with the conceptrecid.
                versions_for_conceptrecid = get_all_versions_from_session_name(session_name) # This one take time but is due to network.

                # If we have already the conceptrecid, we check only if we have a new version.
                if conceptrecid in all_deposit_key:
                    for version in versions_for_conceptrecid:
                        # Don't deal with version there are not processed or raw (like deprecated)
                        if version["metadata"]["version"].replace(" ", "_") not in ["RAW_DATA", "PROCESSED_DATA"]: 
                            print(f'This version is: {version["metadata"]["version"]}')
                            continue
                        try:
                            _ = version_manager.get_version_by_doi(str(version["id"]))
                        except NameError:
                            print(f"Version {version['id']} not in db and it's version name is {version['metadata']['version']}")

                            # Todo We need to try to add it in the databse.

                else:
                    print("Session not in db, we try to import it.")
                    session_path = None
                    
                    # As we working with new version, we always want the last data, so we start with the old one to erase the old data with new data. 
                    for version in sorted(versions_for_conceptrecid, key=lambda d: d["id"]):
                        list_files_to_download = []
                        for file in version["files"]:
                            if file["key"].replace(".zip", "") in ["METADATA", "PROCESSED_DATA_IA"]:
                                list_files_to_download.append(file)
                        if len(list_files_to_download) == 0: continue

                        # We download only the needed data.
                        session_path = Path(TMP_PATH, "auto_update", session_name)
                        download_manager_without_token(list_files_to_download, session_path.parent, session_name, version["id"])

                    if not session_path: 
                        print("[WARNING] We don't found METADATA.zip or PROCESSED_DATA.zip to download, no data to import in DB, we continue.")
                        continue # We didn't found files to download. 

                    # Actually for UAV and AUV, we don't have jacques predictions. We need to force frame insertion inside db.
                    force_frame_insertion = "UAV" in session_name or "AUV" in session_name

                    # Import the session in the database.
                    seatizenManager.import_session(session_path, force_frame_insertion)

                    # Remove the data folder.
                    shutil.rmtree(session_path)


            except KeyboardInterrupt:
                return
            except:
                print(traceback.format_exc(), end="\n\n")

                sessions_fail.append(session_name)


    # Stats.
    print(f"\nEnd of process. On {cpt_sessions} sessions, {len(sessions_fail)} fails. ")
    if (len(sessions_fail)):
        [print("\t* " + session_name) for session_name in sessions_fail]
    
    # Update last time harvest.
    date_now = datetime.now().strftime("%Y-%m-%d")
    new_version = increment_semantic_versioning_at_patch_level(last_etl_run.last_version_on_zenodo, SemanticVersioningLevel.PATCH)
    etl_run_manager.update(zenodo_harvest_at=date_now, version=new_version)

    # Export all value we wants.
    seatizenManager.export_csv()
    
    # Upload all data.
    seatizenManager.publish(opt.path_metadata_json, new_version)

    # Close database connection.
    seatizenManager.sql_connector.close()

if __name__ == "__main__":
    opt = parse_args()
    main(opt)
