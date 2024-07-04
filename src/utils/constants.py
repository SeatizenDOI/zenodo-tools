TMP_PATH = "/tmp/00_plancha"
RESTRICTED_FILES = ["DCIM"]
IMG_EXTENSION = ('.png', '.jpg', '.jpeg') # Image extension in lower case
BYTE_TO_GIGA_BYTE = 1000000000

# Zenodo constants for seatizen manager
SEATIZEN_ATLAS_DOI = "11125848"
SEATIZEN_ATLAS_GPKG = "seatizen_atlas_db.gpkg"
SQL_FILE = "./src/sql_connector/base_database.sql"

# Zenodo constant for upload
MAXIMAL_DEPOSIT_FILE_SIZE = 50 # GB
MAXIMAL_ZIP_SIZE = 15 # GB
MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE = 50
NB_VERSION_TO_FETCH = 100 # Keep low because zenodo tiemout after 30 sec.

# Zenodo for download without token
ZENODO_LINK_WITHOUT_TOKEN = "https://zenodo.org/api/records"

# IA model. The values are the name of the predictions files in PROCESSED_DATA/IA without the session_name
JACQUES_MODEL_NAME = "jacques-v0.1.0_model-20240513_v20.0"
# Assuming model will come from huggingface, the next gen platform.
MULTILABEL_AUTHOR = "lombardata"
MULTILABEL_MODEL_NAME = "DinoVdeau-large-2024_04_03-with_data_aug_batch-size32_epochs150_freeze" 