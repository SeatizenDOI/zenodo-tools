import shutil
import zipfile
from pathlib import Path

from ..sql_connector.connector import SQLiteConnector

from ..zenodo_api.tokenless import get_all_versions_from_session_name
from ..zenodo_api.base_function import file_downloader

from ..seatizen_session.manager import SessionManager
from ..utils.lib_tools import md5
from ..utils.constants import TMP_PATH

class AtlasImport:

    def __init__(self, seatizen_atlas_gpkg: Path):

        # Path.
        self.seatizen_atlas_gpkg = seatizen_atlas_gpkg
        
        # SQL Connector.
        self.sql_connector = SQLiteConnector()


    def import_seatizen_session(self, session_path: Path):

        if not Path.exists(session_path) or not session_path.is_dir():
            print("[ERROR] Session not found in importer. ")
        
        # Get all versions for a session_name.
        versions = get_all_versions_from_session_name(session_path.name)
        if len(versions) == 0:
            raise NameError("No associated version on zenodo.")

        # Get checksum for frames and predictions.
        folders_to_compare = ["PROCESSED_DATA/IA", "METADATA"]        
        session = SessionManager(session_path, TMP_PATH)
        session.prepare_processed_data(folders_to_compare, needFrames=True)
        filename_with_md5 = session.get_md5_checksum_zip_folder()
        session.cleanup()

        # Found doi for frames and predictions.
        filename_with_doi = {}
        for version in versions:
            for file in version["files"]:
                if file["key"] in filename_with_md5 and filename_with_md5[file["key"]] == file["checksum"].replace("md5:", ""):
                    filename_with_doi[file["key"]] = version["id"]
        
        

        # for metadata and ia, we may be need to download zip files to check file md5sum because 
        # the way file are compressed, the zip file md5sum change between hardisk
        if len(filename_with_doi) != len(filename_with_md5):
            print("Md5 sum of zip file are different, need to compare file to file.")

            # Before to download data from zenodo, we need to get all md5 data.
            filename_subfile_with_md5 = {}
            for fdc in folders_to_compare: # We assume frames don't failed due t
                p_fdc = Path(session_path, fdc)
                if not Path.exists(p_fdc) or not p_fdc.is_dir(): continue
                
                p_fdc_code = f"{fdc.replace('/', '_')}.zip"
                filename_subfile_with_md5[p_fdc_code] = {}
                for subfile in p_fdc.iterdir():
                    filename_subfile_with_md5[p_fdc_code][subfile.name] = md5(subfile)


            tmp_zip_folder = Path(TMP_PATH, session_path.name, "TMP")
            for version in versions:
                for file in version["files"]:
                    if file["key"] in filename_with_md5 and file["key"] not in filename_with_doi:
                        if file["key"] not in filename_subfile_with_md5:
                            raise NameError(f"MD5 sum not compute for zip file {file['key']}")
                        
                        # We download file.
                        path_tmp_file = Path(tmp_zip_folder, file["key"])
                        url = file["links"]["self"]
                        print(f"\nWorking with: {path_tmp_file}")
                        file_downloader(url, path_tmp_file)

                        # Retry while checksum is different.
                        while md5(path_tmp_file) != file["checksum"].replace("md5:", ""):
                            print(f"[WARNING] Checksum error when downloading {path_tmp_file}. We retry.")
                            path_tmp_file.unlink()
                            file_downloader(url, path_tmp_file)

                        # Unzip it.
                        path_to_unzip_folder = Path(str(path_tmp_file).replace(".zip", ""))
                        print(f"Unzip {path_tmp_file} to {path_to_unzip_folder}.")
                        with zipfile.ZipFile(path_tmp_file, 'r') as zip_ref:
                            zip_ref.extractall(path_to_unzip_folder)
                        
                        # Go throw all files and try to get all same md5 for file.
                        always_same_md5 = True
                        for subfile in path_to_unzip_folder.iterdir():
                            if not subfile.is_file(): continue
                            if filename_subfile_with_md5[file["key"]][subfile.name] != md5(subfile):
                                always_same_md5 = False
                                break 
                        
                        # If we have exactly the same md5 sum for each file, we have our doi.
                        if always_same_md5:
                            filename_with_doi[file["key"]] = version["id"]

                        # Remove zip file and folder.
                        path_tmp_file.unlink()
                        shutil.rmtree(path_to_unzip_folder)
        
        # Check another time if we have all our filename with doi and if not raise an error.
        if len(filename_with_doi) != len(filename_with_md5):
            raise NameError("Not enough doi to peuplate database")
        
        # Create or update deposit
