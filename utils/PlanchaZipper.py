import os
from pathlib import Path
from zipfile import ZipFile

from .constants import MAXIMAL_ZIP_SIZE, BYTE_TO_GIGA_BYTE

class PlanchaZipper:
    """ Create zip file and scale with max size """
    def __init__(self, base_zip_path):
        self.zip_path = base_zip_path
        self.zip_name = Path(base_zip_path).stem
        self.zip = ZipFile(self.zip_path, "w")

        self.tot_zip_size, self.nb_zip_file = 0, 1


    def add_file(self, file, output_struc_file):
        file_size = round(os.path.getsize(str(file)) / BYTE_TO_GIGA_BYTE, 6)
        if file_size + self.tot_zip_size > MAXIMAL_ZIP_SIZE:
            self.nb_zip_file += 1
            self.zip.close()
            new_zip_path = str(self.zip_path).replace(self.zip_name, f"{self.zip_name}_p{str(self.nb_zip_file).rjust(2, '0')}")
            self.zip = ZipFile(new_zip_path, "w")
            self.tot_zip_size = file_size
        else:
            self.tot_zip_size += file_size
        self.zip.write(file, output_struc_file)


    def close(self):
        self.zip.close()