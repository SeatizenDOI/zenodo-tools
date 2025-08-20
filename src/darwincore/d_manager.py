import yaml
import json
import zipfile
import requests
import pycountry
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from datetime import datetime
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
        self.list_filepath_to_zip: list[Path] = []

        # Manager.
        self.ml_annotation_manager = MultilabelAnnotationDAO()
        self.ml_anno_ses_manager = MultilabelAnnotationSessionDAO()
        self.ml_label_manager = MultilabelLabelDAO()


    def create_darwincore_package(self, annotationSessions: list[MultilabelAnnotationSessionDTO]) -> None:

        # No annotations sessions.
        if len(annotationSessions) == 0:
            print("No annotations to export to darwincore format.")
            return
        
        mapping_label_by_taxonid = self.create_taxon_csv()
      

        event_data, record_data, occurrence_data = [], [], []
        dois_session = set()
        for sa in annotationSessions:

            # TODO Change the way to manage write but for now its okey
            if "amoros" in sa.author_name:
                sampling_proto = "https://doi.org/10.4314/wiojms.v23i2.4" 
                institution_id = "https://ror.org/03g407536" 
                rightHolders = "IHCM"
            else:
                sampling_proto = "https://doi.org/10.1038/s41597-024-04267-z"
                institution_id = "https://ror.org/044jxhp58"
                rightHolders = "Ifremer"
            
            
            record_data.append({
                "recordID": sa.id, 
                "type": "StillImage",
                "datasetID": sa.id,
                "datasetName": sa.dataset_name,
                "basisOfRecord": "HumanObservation",
                "modified": sa.annotation_date,
                "language": "en",
                "licence": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
                "rightsHolder": rightHolders,
                "accessRights": "not-for-profit use only",
                "institutionID": institution_id,
            })

            print(f"-- Launching {sa.dataset_name}")
            event_cached = set()
            for annotation in tqdm(self.ml_annotation_manager.get_annotations_from_anno_ses(sa)):
                if annotation.value not in [1, 0]: continue # Not presence or absence
                label = annotation.ml_label.name
                if label not in mapping_label_by_taxonid: continue

                eventDate, eventTime = "", ""
                if annotation.frame.gps_datetime is not None:
                    eventDate, eventTime = annotation.frame.gps_datetime.split(" ")
                    eventTime = eventTime + "Z"

                dois_session.add(annotation.frame.version.doi)
                eventID = f"{annotation.frame.filename.split('.')[0]}_{annotation.frame.gps_datetime.replace(' ', '_')}"

                if eventID not in event_cached:
                    lon, lat = annotation.frame.version.deposit.centroid
                    country = pycountry.countries.get(alpha_3=annotation.frame.version.deposit.alpha3_country_code)
                    
                    precision_gps_in_meters = 10
                    if annotation.frame.gps_fix == 1: # If we are in Q1
                        precision_gps_in_meters = 0.1 # Precise to 10 centimeters
                    event_data.append({
                        "parentID": annotation.frame.version.deposit.session_name,
                        "eventID": eventID,
                        "eventType": "Observation",
                        "eventDate": eventDate,
                        "eventTime": eventTime,
                        "habitat": "coral_reef",
                        "samplingProtocol": sampling_proto, 
                        "footprintWKT": annotation.frame.version.deposit.wkt_footprint,
                        "decimalLatitude": lat,
                        "decimalLongitude": lon,
                        "country": country.name,
                        "countryCode": annotation.frame.version.deposit.alpha3_country_code,
                        "geodeticDatum": "EPSG:4326",
                        "coordinateUncertaintyInMeters": precision_gps_in_meters,
                    })
                    event_cached.add(eventID)
                
                media = f"https://doi.org/10.5281/zenodo.{annotation.frame.version.doi}/{'_'.join(annotation.frame.relative_path.split('/')[1:-1])}.zip"
                media += f" | {annotation.frame.relative_path}"
                occurrence_data.append({
                    "eventID": eventID,
                    "occurenceID": annotation.id,
                    "taxonID": mapping_label_by_taxonid[label],
                    "recordNumber": sa.id,
                    "occurrenceStatus": "present" if annotation.value == 1 else "absent",
                    "recordedBy": ' | '.join([a.capitalize() for a in sa.author_name.split('-')]),
                    "associatedMedia": media
                })

        # If no data, no export.
        if len(record_data) == 0:
            print("No annotations to export to darwincore format.")
            return

        # Save header data to txt instead of CSV (GBIF constraint).
        event_path = Path(self.tmp_folder, "event.txt")
        occurrence_path = Path(self.tmp_folder, "occurrence.txt")
        record_path = Path(self.tmp_folder, "record-level.txt")


        pd.DataFrame(event_data, columns=list(event_data[0])).to_csv(event_path, index=False)
        pd.DataFrame(occurrence_data, columns=list(occurrence_data[0])).to_csv(occurrence_path, index=False)
        pd.DataFrame(record_data, columns=list(record_data[0])).to_csv(record_path, index=False)

        self.list_filepath_to_zip += [event_path, occurrence_path, record_path]

        # Create metadata files
        self.create_eml_xml(list(dois_session))
        self.create_metadata_xml()
        
        self.final_export()


    def create_eml_xml(self, frames_doi) -> None:
        """
            https://eml.ecoinformatics.org/
            Build an Ecological Metadata Language file.

            https://knb.ecoinformatics.org/emlparser/
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
        tree.write(self.eml_path, encoding='UTF-8', xml_declaration=True, method="xml")
    

    def create_metadata_xml(self) -> None:
        if not Path.exists(self.base_meta_path) or not self.base_meta_path.is_file(): return
        
        tree = ET.parse(self.base_meta_path)
        root = tree.getroot()

        # Register the namespace to handle the default namespace.
        namespace = {'dwc': 'http://rs.tdwg.org/dwc/text/'}
        ET.register_namespace('', namespace['dwc'])

        # Find the <files> element inside the <core> element.
        core_files_element = root.find('.//dwc:core/dwc:files', namespace)

        for f in self.list_filepath_to_zip:
            # Create a new <location> element
            new_location = ET.Element('location')
            new_location.text = f.name

            core_files_element.append(new_location)

        tree.write(self.meta_path, encoding='UTF-8', xml_declaration=True)


    def final_export(self) -> None:
        print(f"func: Create darwincore package to {self.archive_name}")

        Path(self.archive_name.parent).mkdir(exist_ok=True, parents=True)

        with zipfile.ZipFile(self.archive_name, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for f in self.list_filepath_to_zip:
                archive.write(f, f.name)
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
    

    def create_taxon_csv(self) -> dict:

        t_start = datetime.now()

        taxon_mapping_path = Path("src/darwincore/taxon_mapping.yaml")
        if not taxon_mapping_path.exists(): raise FileNotFoundError(f"Taxon mapping file not found at {taxon_mapping_path}")

        with open(taxon_mapping_path) as f:
            classes_taxon_mapping = yaml.load(f, Loader=yaml.FullLoader)

        # Get all gbif information for each label
        cache_gbif_by_label = Path("src/darwincore/cache_gbif.json")
        if not cache_gbif_by_label.exists():
            gbif_by_label = self.retrieve_gbif_information()
            with open(cache_gbif_by_label, "w") as file:
                json.dump(gbif_by_label, file)
        else:
            with open(cache_gbif_by_label) as file:
                gbif_by_label = json.load(file)

        gbif_by_label = {k: v for k, v in gbif_by_label.items() if len(v) != 0} # Remove uncomplete taxon.
        
        taxon_data, scientific_label_to_taxonid= [], {}
        for id, label in enumerate(gbif_by_label):
            scientific_label_to_taxonid[label] = id

            row = {"taxonID": id, "vernacularName": label}
            for our_label_field_key, label_field_key in classes_taxon_mapping['DARWINCORE_GBIF_FIELDS_MAPPING'].items():
                row[our_label_field_key] = gbif_by_label[label][label_field_key] if label_field_key in gbif_by_label[label] else ""

            taxon_data.append(row)
        
        taxon_path = Path(self.tmp_folder, f"taxon.txt") # GBIF want txt extension instead of csv
        self.list_filepath_to_zip.append(taxon_path)

        df_taxon = pd.DataFrame(taxon_data, columns=list(taxon_data[0]))
        df_taxon.to_csv(taxon_path, index=False)

        print(f"Retrieve information in {datetime.now() - t_start}")

        return scientific_label_to_taxonid