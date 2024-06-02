TMP_PATH = "/media/bioeos/F/tmp/"
RESTRICTED_FILES = ["DCIM"]
IMG_EXTENSION = ('.png', '.jpg', '.jpeg') # Image extension in lower case
BYTE_TO_GIGA_BYTE = 1000000000

# Zenodo constants for seatizen manager
TMP_PATH_MANAGER = "/tmp/SeatizenManager/"
SEATIZEN_ATLAS_DOI = "11125848"

SESSION_DOI_CSV = "session_doi.csv"
METADATA_IMAGE_CSV = "metadata_image.csv"
SEATIZEN_MANAGER_FILES = [SESSION_DOI_CSV, METADATA_IMAGE_CSV]

# Zenodo constant for upload
MAXIMAL_DEPOSIT_FILE_SIZE = 50 # GB
MAXIMAL_ZIP_SIZE = 15 # GB
MAX_RETRY_TO_UPLOAD_DOWNLOAD_FILE = 50
NB_VERSION_TO_FETCH = 500