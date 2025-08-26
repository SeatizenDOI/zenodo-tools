from pathlib import Path
from fastapi import FastAPI


from src.models.deposit_model import DepositDAO
from src.seatizen_atlas.sa_manager import AtlasManager

atlas_manager = AtlasManager({}, "../seatizen_atlas_folder", True, False)
deposit_manager = DepositDAO()


app = FastAPI()

@app.get("/")
def root():
    return {"message": ', '.join([a.session_name for a in deposit_manager.deposits])}