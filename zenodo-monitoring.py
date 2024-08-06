import argparse

from src.zenodo_monitoring.zm_app_page import ZenodoMonitoringApp


def parse_args():
    parser = argparse.ArgumentParser(prog="zenodo-monitoring", description="Interface to retrieve data from sqlite database.")

    # Seatizen atlas folder path
    parser.add_argument("-psa", "--path_seatizen_atlas_folder", default="./seatizen_atlas_folder", help="Folder to store data.")
    parser.add_argument("-ulo", "--use_from_local", action="store_true", help="Work from a local folder. Update if exists else Create. Default behaviour is to download data from zenodo.")

    return parser.parse_args()


if __name__ == '__main__':
    opt = parse_args()
    my_app = ZenodoMonitoringApp(opt)

    my_app.run(debug=True)