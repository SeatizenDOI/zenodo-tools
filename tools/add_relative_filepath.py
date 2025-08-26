from pathlib import Path
import json
from tqdm import tqdm

from src.seatizen_atlas.sa_manager import AtlasManager
from src.models.frame_model import FrameDAO, FrameDTO


def main():

    config_path, config_json = Path('./config.json'), {}
    if not Path.exists(config_path) or not config_path.is_file():
        print("No config file found, you cannot upload the result on zenodo.")
    else:
        # Open json file with zenodo token.
        with open(config_path) as json_file:
            config_json = json.load(json_file)

    seatizenManager = AtlasManager(config_json, "seatizen_atlas_folder", True, False)


    frame_manager = FrameDAO()
    frames = frame_manager.frames
    
    for frame in tqdm(frames):
        if frame.relative_path is not None: continue

        field_value = f"{frame.version.deposit.session_name}/DCIM/{frame.original_filename}"
        frame_manager.update_field(frame.id, "relative_file_path", field_value)




if __name__ == "__main__":
    main()