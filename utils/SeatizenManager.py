import json
import pandas as pd
from pathlib import Path

from .lib_tools import md5
from .ZenodoAPI import ZenodoAPI
from .SQLiteConnector import SQLiteConnector
from .constants import SEATIZEN_ATLAS_DOI, SEATIZEN_ATLAS_GPKG

class SeatizenManager:
    def __init__(self, config, seatizen_folder_path, from_local, force_regenerate):
        
        # Config
        self.config = config
        # TODO Add metadata

        # Bool.
        self.from_local = from_local
        self.force_regenerate = force_regenerate

        # Path.
        self.seatizen_folder_path = Path(seatizen_folder_path)
        self.seatizen_atlas_gpkg = Path(self.seatizen_folder_path, SEATIZEN_ATLAS_GPKG)
        self.sql_connector = SQLiteConnector(self.seatizen_atlas_gpkg)

        # TODO Add exporter.

        # TODO Add importer.

        self.setup()

    def setup(self):
        
        # Create folder if not exists.
        self.seatizen_folder_path.mkdir(exist_ok=True, parents=True)

        # Clean folder if we download from zenodo or if we force to regenerate.
        if self.force_regenerate or not self.from_local:
            self.clean_seatizen_folder()
        
        # Download data if we don't force to regenerate.
        if not self.force_regenerate and not self.from_local:
            
            # Get last version information.
            version_json = ZenodoAPI.get_version_from_doi(SEATIZEN_ATLAS_DOI)

            # Download data.
            ZenodoAPI.download_manager_without_token(version_json["files"], self.seatizen_folder_path, ".", SEATIZEN_ATLAS_DOI)
        
        # Try to figure out if we have a gpkg file.
        if not Path.exists(self.seatizen_atlas_gpkg) or not self.seatizen_atlas_gpkg.is_file():
            print("Generating base gpkg file.")
            self.sql_connector.generate()

    def import_session(self, session: Path):
        pass
    
    def export_csv(self):


        pass

    def clean_seatizen_folder(self):
        
        for file in self.seatizen_folder_path.iterdir():
            file.unlink()


    def publish(self):
        if self.from_local: 
            print("Work from local, don't publish data on zenodo.")
            return
    
    @staticmethod
    def update_metadata(config_json, metadata_json_path):
        """ Seatizen Atlas metadata """
        metadata_json_path = Path(metadata_json_path)
        if not Path.exists(metadata_json_path) or not metadata_json_path.is_file():
            print("Metadata file not found.")
            return
        print("Updating metadata last version of seatizen atlas.")
        with open(metadata_json_path) as json_file:
            metadata_json = json.load(json_file)

        zenodoAPI = ZenodoAPI("", config_json)
        zenodoAPI.deposit_id = SEATIZEN_ATLAS_DOI
        
        data = {
            'metadata': {
                'title': "Seatizen Atlas",
                'upload_type': 'dataset',
                'keywords': metadata_json["keywords"],
                'creators': metadata_json["creators"],
                'related_identifiers': [{'identifier': 'urn:seatizen-atlas', 'relation': 'isAlternateIdentifier'}],
                'language': "eng",
                'description': SeatizenManager.get_description(),
                'access_right': 'open',
                'version': metadata_json["version"],
                'license': metadata_json["license"]
            }
        }
        zenodoAPI.edit_metadata(data)
    
    @staticmethod
    def get_description():
        return f"""
            The deposit is currently a work in progress, but it will soon serve as a comprehensive repository. Once completed, it will include: <br>
            <ul>
            <li> <strong>Geopackage File:</strong> This file will store extensive geospatial data, allowing for efficient management and analysis of spatial information.</li>
            <li> <strong>CSV Files:</strong> These files will bring together all key information in an accessible and easy-to-read format, ensuring that key data is easily available and well-organized.</li>
            </ul><br>

            <strong>CSV files include:</strong><br><br>
            <ul>
            <li><strong>session_doi.csv:</strong> A CSV file listing all sessions published on Zenodo. This file contains the following columns:</li>
            <ul>
            <li> session_name: Identifies the session.</li>
            <li> session_doi: Indicates the URL of the session.</li>
            <li> place: Indicates the location of the session.</li>
            <li> date: Indicates the date of the session.</li>
            <li> raw_data: Indicates whether the session contains raw data.</li>
            <li> processed_data: Indicates whether the session contains processed data.<br>
            </ul><br>
            <li><strong>metadata_images.csv:</strong> A CSV file describing all metadata for each image published in open access. This file contains the following columns:<br>
            <ul>
            <li> OriginalFileName: Indicates the original name of the photo.</li>
            <li> FileName: Indicates the name of the photo adapted to the naming convention adopted by the Seatizen team (i.e., YYYYMMDD_COUNTRYCODE-optionalplace_device_session-number_originalimagename.*). </li>
            <li> relative_file_path: Indicates the path of the image in the deposit.</li>
            <li> frames_doi: Indicates the DOI of the version where the image is located.</li>
            <li> GPSLatitude: Indicates the latitude of the image (if available).</li>
            <li> GPSLongitude: Indicates the longitude of the image (if available).</li>
            <li> GPSAltitude: Indicates the depth of the frame (if available).</li>
            <li> GPSRoll: Indicates the roll of the image (if available).</li>
            <li> GPSPitch: Indicates the pitch of the image (if available).</li>
            <li> GPSTrack: Indicates the track of the image (if available).</li>
            <li> prediction_doi: Refers to a specific model prediction on the current image (if available). </li>
            <li> Columns for each class predicted by the model.</li>
            </ul><br>

            <li><strong>metadata_annotation.csv:</strong> A CSV file listing the subset of all the images that are annotated, along with their annotations. This file contains the following columns:<br>
            <ul>
            <li> FileName: Indicates the name of the photo.</li>
            <li> frame_doi: Indicates the DOI of the version where the image is located.</li>
            <li> relative_file_path: Indicates the path of the image in the deposit.</li>
            <li> annotation_date: Indicates the date when the image was annotated.</li>
            <li> Columns for each class with values: </li>
                <ul>
                    <li> 1: If the class is present.</li>
                    <li> 0: If the class is absent.</li>
                    <li> -1: If the class was not annotated.</li>
                </ul>
            </ul>
            </ul>
    """