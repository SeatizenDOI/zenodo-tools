import unittest

from src.utils.constants import TMP_PATH
from src.seatizen_session.ss_manager import SessionManager


class TestSessionManager(unittest.TestCase):


    def test_get_frame_parent_folder_1(self):
        session = SessionManager("20010101_FRA-BREST_ASV-01_01", TMP_PATH)
        list_frames_parent = [
            "20010101_FRA-BREST_ASV-01_01/PROCESSED_DATA/FRAMES/01.jpg",
            "20010101_FRA-BREST_ASV-01_01/PROCESSED_DATA/FRAMES/02.jpg",
            "20010101_FRA-BREST_ASV-01_01/PROCESSED_DATA/FRAMES/03.jpg",
            "20010101_FRA-BREST_ASV-01_01/PROCESSED_DATA/FRAMES/04.jpg",
        ]
        common_parent_folder = "PROCESSED_DATA/FRAMES"
        self.assertEqual(session.get_frame_parent_folder(list_frames_parent), common_parent_folder)
    
    def test_get_frame_parent_folder_2(self):
        session = SessionManager("20010101_FRA-BREST_ASV-01_01", TMP_PATH)
        list_frames_parent = [
            "20010101_FRA-BREST_ASV-01_01/DCIM/01.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/02.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/03.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/04.jpg",
        ]
        common_parent_folder = "DCIM"
        self.assertEqual(session.get_frame_parent_folder(list_frames_parent), common_parent_folder)
    
    def test_get_frame_parent_folder_3(self):
        session = SessionManager("20010101_FRA-BREST_ASV-01_01", TMP_PATH)
        list_frames_parent = [
            "20010101_FRA-BREST_ASV-01_01/DCIM/GOPRO1/01.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/GOPRO2/02.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/GOPRO3/03.jpg",
            "20010101_FRA-BREST_ASV-01_01/DCIM/GOPRO4/04.jpg",
        ]
        common_parent_folder = "DCIM"
        self.assertEqual(session.get_frame_parent_folder(list_frames_parent), common_parent_folder)
    
    def test_constructor_1(self):
        session = SessionManager("20010101_FRA-BREST_ASV-01_01", TMP_PATH)

        self.assertEqual(session.place, "Brest")
        self.assertEqual(session.country, "France")
        self.assertEqual(session.date, "2001-01-01")
        self.assertEqual(session.platform, "ASV")
    
    def test_constructor_2(self):
        session = SessionManager("15471212_SYC-CAP-HORNE-BLEU_UAV_01", TMP_PATH)

        self.assertEqual(session.place, "Cap-Horne-Bleu")
        self.assertEqual(session.country, "Seychelles")
        self.assertEqual(session.date, "1547-12-12")
        self.assertEqual(session.platform, "UAV")


if __name__ == "__main__":
    unittest.main()