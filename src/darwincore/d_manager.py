import yaml
import uuid
import zipfile
import requests
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from suds.client import Client
import xml.etree.ElementTree as ET

from ..utils.constants import TMP_PATH

from ..models.ml_annotation_model import MultilabelAnnotationSessionDAO, MultilabelAnnotationDAO, MultilabelAnnotationSessionDTO, MultilabelLabelDAO

class DarwinCoreManager:
    def __init__(self, archive_name: Path) -> None:
        
        # Package name for darwincore archive.
        self.archive_name = archive_name
        
        # Path to tmp_folder.
        self.tmp_folder = Path(TMP_PATH, "darwincore")
        self.tmp_folder.mkdir(exist_ok=True, parents=True)

        # Path to base file.
        self.base_meta_path = Path(Path.cwd(), "src/darwincore/base_meta.xml")
        self.base_eml_path = Path(Path.cwd(), "src/darwincore/base_eml.xml")

        # Path to tmp_file.
        self.meta_path = Path(self.tmp_folder, "meta.xml")
        self.eml_path = Path(self.tmp_folder, "eml.xml")
        self.header_path = Path(self.tmp_folder, "dataset.csv")
        self.list_occurence_path: list[Path] = []

        # Manager.
        self.ml_annotation_manager = MultilabelAnnotationDAO()
        self.ml_anno_ses_manager = MultilabelAnnotationSessionDAO()
        self.ml_label_manager = MultilabelLabelDAO()


    def create_darwincore_package(self, annotationSessions: list[MultilabelAnnotationSessionDTO]) -> None:

        # No annotations sessions.
        if len(annotationSessions) == 0:
            print("No annotations to export to darwincore format.")
            return
        
        # Open all config file for darwin core
        t_start = datetime.now()
        
        taxon_mapping = Path(Path.cwd(), "src/darwincore", "taxon_mapping.yaml")

        with open(taxon_mapping) as f:
            classes_taxon_mapping = yaml.load(f, Loader=yaml.FullLoader)

        # Get all gbif information for each label
        gbif_by_label = self.retrieve_gbif_information()

        print(f"Retrieve information in {datetime.now() - t_start}")

        header_data = []
        # Iterate on each session and create an occurence_file for each one.
        for sa in annotationSessions:

            # Add data to header.
            header_data.append({
                "datasetID": sa.id,
                "datasetName": sa.dataset_name,
                "basisOfRecord": "MachineObservation",
                "rightsHolder": "Ifremer",
                "accessRights": "not-for-profit use only",
                "dataGeneralizations": "No generalizations",
                "recordedBy": "Ifremer",
                "habitat": "coral_reef",
                "language": "English",
                "identifiedBy": sa.author_name
            })


            # Generate occurence file.
            occurence_path = Path(self.tmp_folder, f"occurence_{sa.id}_{sa.dataset_name}.csv")
            self.list_occurence_path.append(occurence_path)

            occurence_data = []
            print(f"-- Launching {occurence_path}")
            for annotation in tqdm(self.ml_annotation_manager.get_annotations_from_anno_ses(sa)):
                label = annotation.ml_label.name
                if len(gbif_by_label[label]) == 0: continue

                eventDate, eventTime, year, month, day = "", "", "", "", ""
                if annotation.frame.gps_datetime is not None:
                    eventDate, eventTime = annotation.frame.gps_datetime.split(" ")
                    year, month, day = eventDate.split("-")

                scientific_data = {}
                for our_label_field_key, label_field_key in classes_taxon_mapping['DARWINCORE_GBIF_FIELDS_MAPPING'].items():
                    scientific_data[our_label_field_key] = gbif_by_label[label][label_field_key] if label_field_key in gbif_by_label[label] else ""

                occurence_data.append({
                    "type": "DCIM",
                    "datasetID": sa.id,
                    "eventDate": eventDate,
                    "eventTime": eventTime,
                    "year": year,
                    "month": month,
                    "day": day,
                    "occurrenceID": f"{annotation.frame.filename}_{uuid.uuid4()}",
                    "vernacularName": label,
                    "decimalLatitude": annotation.frame.gps_latitude,
                    "decimalLongitude": annotation.frame.gps_longitude,
                    "coordinatePrecision": annotation.frame.gps_fix,
                    "occurrenceStatus": "present"
                } | scientific_data)

            # Save occurence.
            df_occurence = pd.DataFrame(occurence_data, columns=list(occurence_data[0]))
            df_occurence.to_csv(occurence_path, index=False)
        
        # If no data, no export.
        if len(header_data) == 0:
            print("No annotations to export to darwincore format.")
            return

        # Save header data to csv.
        df_header_data = pd.DataFrame(header_data, columns=list(header_data[0]))
        df_header_data.to_csv(self.header_path, index=False)

        # Create metadata files
        self.create_eml_xml([])
        self.create_metadata_xml()
        
        self.final_export()


    def create_eml_xml(self, frames_doi) -> None:
        """
            https://eml.ecoinformatics.org/
            Build an Ecological Metadata Language file.
        """

        if not Path.exists(self.base_eml_path) or not self.base_eml_path.is_file(): return

        # Retrieve base xml and get dataset part.
        tree = ET.parse(self.base_eml_path)
        dataset = tree.find("dataset")
        
        if dataset == None: return

        # Add references.
        references = ET.SubElement(dataset, "bibliographicCitation")
        for doi in frames_doi:
            citation = ET.SubElement(references, "citation")
            identifier = ET.SubElement(citation, "identifier")
            identifier.text = f"https://doi.org/10.5281/zenodo.{doi}"

        # Save the XML to a file.
        tree.write(self.eml_path, encoding='UTF-8', xml_declaration=True)
    

    def create_metadata_xml(self) -> None:
        if not Path.exists(self.base_meta_path) or not self.base_meta_path.is_file(): return
        
        tree = ET.parse(self.base_meta_path)
        root = tree.getroot()

        # Register the namespace to handle the default namespace.
        namespace = {'dwc': 'http://rs.tdwg.org/dwc/text/'}
        ET.register_namespace('', namespace['dwc'])

        # Find the <files> element inside the <core> element.
        core_files_element = root.find('.//dwc:core/dwc:files', namespace)

        for f in self.list_occurence_path:
            # Create a new <location> element
            new_location = ET.Element('location')
            new_location.text = f.name

            core_files_element.append(new_location)

        tree.write(self.meta_path, encoding='UTF-8', xml_declaration=True)


    def final_export(self) -> None:
        print(f"func: Create darwincore package to {self.archive_name}")

        Path(self.archive_name.parent).mkdir(exist_ok=True, parents=True)

        with zipfile.ZipFile(self.archive_name, 'w') as archive:
            for f in self.list_occurence_path:
                archive.write(f, f.name)
            archive.write(self.header_path, self.header_path.name)
            archive.write(self.meta_path, self.meta_path.name)
            archive.write(self.eml_path, self.eml_path.name)

    
    def retrieve_gbif_information(self) -> dict[str, dict]:
        """ Fetch gbif information. """
        print("func: Fetching gbif information. ")

        gbif_map_by_label = {}
        cache = {}
        print("Fetching: ", end="")
        for label in self.ml_label_manager.labels:
            print(f"{label.name}", end=", ", flush=True)

            gbif_map_by_label[label.name] = {}
            if not label.id_gbif: continue

            if label.id_gbif in cache:
                gbif_map_by_label[label.name] = cache[label.id_gbif]
                continue

            r = requests.get(f"https://api.gbif.org/v1/species/{label.id_gbif}")
    
            if r.status_code == 404:
                print(f"Cannot access to {label.name}. Error 404")
            else:
                gbif_map_by_label[label.name] = r.json()
                cache[label.id_gbif] = r.json()
        
        print()
        return gbif_map_by_label