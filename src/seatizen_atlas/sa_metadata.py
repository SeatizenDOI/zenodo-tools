import json
from pathlib import Path

from ..zenodo_api.za_token import ZenodoAPI

def seatizen_atlas_metadata(config_json: dict, metadata_json_path: str) -> None:
    """ Seatizen Atlas metadata """
    print("Updating metadata last version of seatizen atlas.")
    
    metadata = build_metadata(metadata_json_path)

    zenodoAPI = ZenodoAPI("seatizen-atlas", config_json)

    zenodoAPI.edit_metadata(metadata)
    

def build_metadata(metadata_json_path: str, version: str | None = None) -> dict:

    metadata_json_path = Path(metadata_json_path)
    if not Path.exists(metadata_json_path) or not metadata_json_path.is_file():
        print("Metadata file not found.")
        return {}
    
    with open(metadata_json_path) as json_file:
        metadata_json = json.load(json_file)

    communities = [{'identifier': name} for name in metadata_json["communities"]]

    data = {
        'metadata': {
            'title': "Seatizen Atlas",
            'upload_type': 'dataset',
            'keywords': metadata_json["keywords"],
            'creators': metadata_json["creators"],
            'related_identifiers': [{'identifier': 'urn:seatizen-atlas', 'relation': 'isAlternateIdentifier'}],
            'language': "eng",
            'description': get_description(metadata_json["description"]),
            'access_right': 'open',
            'version': version if version != None else metadata_json["version"],
            'license': metadata_json["license"],
            'communities': None if len(communities) == 0 else communities
        }
    }
    return data


def get_description(path_description_raw: str) -> str:
    """ Read and return description in text file. """
    path_description = Path(path_description_raw)
    if not Path.exists(path_description) or not path_description.is_file():
        return ""
            
    data = ""
    with open(path_description, "r") as f:
        data = "".join(f.readlines()).replace("\n", "")
    return data