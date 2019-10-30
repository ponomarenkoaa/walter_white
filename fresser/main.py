import argparse
import logging
import os
import time
import pandas as pd

from PyEIS import extract_mpt
from watchdog.events import LoggingFileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


class MprFilesHandler(LoggingFileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            logging.info("Directory %s created" % event.src_path)
        else:
            logging.info("File %s created" % event.src_path)
            if event.src_path.endswith(".mpt"):
                logging.info("New file with MPT format: %s" % event.src_path)
                if event.src_path.endswith("03_PEIS_C01.mpt"):
                    file_path, file_name = os.path.split(event.src_path)
                    peis1 = extract_mpt(file_path + "/", file_name)
                    print(peis1.head())
                    print(list(peis1.columns.values))
                    print(peis1[['Z_mag', 'Z_phase']])
                    peis1["Z_mag_shifted"] = peis1["Z_mag"].shift()
                    peis1["Z_phase_shifted"] = peis1["Z_phase"].shift()

                    def handler(Z_mag_shifted, Z_phase_shifted, Z_phase):
                        if ((Z_phase < Z_phase_shifted) & (Z_phase * Z_phase_shifted < 0)):
                            return Z_mag_shifted
                        else:
                            return None

                    peis1["Impedanz1"] = peis1[["Z_mag_shifted", "Z_phase_shifted", "Z_phase"]].apply(lambda args: handler(*args), axis=1)
                    print(peis1)

                if event.src_path.endswith("04_MP_C01.mpt"):
                    file_path, file_name = os.path.split(event.src_path)
                    mp = extract_mpt(file_path + "/", file_name)
                    print(mp.head())
                    print(list(mp.columns.values))




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str)
    args = parser.parse_args()

    event_handler = MprFilesHandler()
    observer = Observer()
    observer.schedule(event_handler, args.path, recursive=True)
    logging.info("Observing directory %s" % args.path)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
