import yaml
import zipfile
import pandas as pd
from pathlib import Path
from suds.client import Client
import xml.etree.ElementTree as ET

from ..utils.constants import TMP_PATH

from ..sql_connector.sc_multilabel_dto import MultilabelAnnotationSession, MultilabelAnnotationSessionManager

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


    def create_darwincore_package(self, annotationSessions: list[MultilabelAnnotationSession]) -> None:

        # Open all config file for darwin core
        taxon_mapping = Path(Path.cwd(), "src/darwincore", "taxon_mapping.yaml")

        with open(taxon_mapping) as f:
            classes_taxon_mapping = yaml.load(f, Loader=yaml.FullLoader)

        scinames = []
        for label in classes_taxon_mapping['CLASSES']:
            scinames.append(classes_taxon_mapping['CLASSES'][label]['taxon_research'])

        taxon_information_df = self.match_taxa_in_worms_database(scinames)

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

            sa_manager = MultilabelAnnotationSessionManager(annotation_session=sa)

            occurence_data = []
            for label, GPSLongitude, GPSLatitude, GPSDatetime, filename in sa_manager.get_all_annotations_informations():
                if label not in classes_taxon_mapping['CLASSES']: continue

                eventDate, eventTime, year, month, day = "", "", "", "", ""
                if GPSDatetime is not None:
                    eventDate, eventTime = GPSDatetime.split(" ")
                    year, month, day = eventDate.split("-")

                # Extract species information.
                scientific_data = {} # TODO mieux nommer
                for our_label_field_key in classes_taxon_mapping['DARWINCORE_WORMS_FIELDS_MAPPING']:
                    label_field_key = classes_taxon_mapping['DARWINCORE_WORMS_FIELDS_MAPPING'][our_label_field_key]
                    label_sciname = classes_taxon_mapping['CLASSES'][label]['taxon_research']
                    label_field_value = list(taxon_information_df[taxon_information_df['scientificname'] == label_sciname][label_field_key])
                    scientific_data[our_label_field_key] = label_field_value[0] if label_field_value else ""
                
                occurence_data.append({
                    "type": "DCIM",
                    "datasetID": sa.id,
                    "eventDate": eventDate,
                    "eventTime": eventTime,
                    "year": year,
                    "month": month,
                    "day": day,
                    "occurrenceID": filename,
                    "vernacularName": classes_taxon_mapping["CLASSES"][label]["vernacularName"],
                    "decimalLatitude": GPSLatitude,
                    "decimalLongitude": GPSLongitude,
                    "coordinatePrecision": "à une vache près",
                    "associatedMedia": "",
                    "occurrenceStatus": "present"
                } | scientific_data)

            # Save occurence.
            df_occurence = pd.DataFrame(occurence_data, columns=list(occurence_data[0]))
            df_occurence.to_csv(occurence_path, index=False)
        
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
    
    def match_taxa_in_worms_database(self, taxa_scientific_names: list) -> pd.DataFrame:
        '''Match taxa information in the WORMS database (https://www.marinespecies.org/)

        Input:
        - taxa_scientific_names : a string or a list of strings containing the taxa scientific names to reach in the database.

        Output :
        - a panda_dataframe with taxonomic information on the input names. Each row represents a taxa.
        '''

        cl = Client('https://www.marinespecies.org/aphia.php?p=soap&wsdl=1')

        scinames = cl.factory.create('scientificnames')
        scinames["_arrayType"] = "string[]"
        scinames["scientificname"] = taxa_scientific_names

        array_of_results_array = cl.service.matchAphiaRecordsByNames(scinames, like="true", fuzzy="false", marine_only="false")

        taxa_information = []

        for results_array in array_of_results_array:
            for aphia_object in results_array:
                items_value = Client.items(aphia_object)
                taxa_information.append([value for (key, value) in items_value])

        items_key = Client.items(aphia_object)
        col_names = [key for (key, value) in items_key]

        taxa_information_df = pd.DataFrame(
            data = taxa_information,
            columns = col_names
        ).drop_duplicates()

        return taxa_information_df