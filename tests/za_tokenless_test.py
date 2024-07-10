import unittest

from src.utils.constants import SEATIZEN_ATLAS_DOI
from src.zenodo_api.za_tokenless import get_version_from_doi, get_version_from_session_name


class TestZenodoAPITokenLess(unittest.TestCase):


    def test_get_version_from_doi_1(self):
        version_json = get_version_from_doi(SEATIZEN_ATLAS_DOI)
        self.assertEqual(version_json["metadata"]["alternate_identifiers"][0]["identifier"], "urn:seatizen-atlas")
    
    def test_get_version_from_session_name(self):
        # Drone session made by Mr. Poulain
        version_json = get_version_from_session_name("20221023_SYC-aldabra-arm06_UAV-02_17")
        self.assertEqual(version_json["metadata"]["related_identifiers"][0]["identifier"], "urn:20221023_SYC-aldabra-arm06_UAV-02_17")

        # Plancha session
        version_json = get_version_from_session_name("20221021_SYC-ALDABRA-ARM01_ASV-02_00")
        self.assertEqual(version_json["metadata"]["alternate_identifiers"][0]["identifier"], "urn:20221021_SYC-ALDABRA-ARM01_ASV-02_00")
        

if __name__ == "__main__":
    unittest.main()