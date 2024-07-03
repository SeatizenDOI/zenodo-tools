import unittest

from ..utils.constants import TMP_PATH
from ..seatizen_session.ss_manager import SessionManager


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

if __name__ == "__main__":
    unittest.main()