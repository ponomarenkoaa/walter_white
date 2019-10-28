import argparse
import logging
import os
import time

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
                if event.src_path.endswith("PEIS_C01.mpt"):
                    file_path, file_name = os.path.split(event.src_path)
                    data = extract_mpt(file_path + "/", file_name)
                    print(data.head())  # TODO: finish this logic


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
