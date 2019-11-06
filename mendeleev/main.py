import argparse
import logging
import os
import time

import pandas as pd
from PyEIS import extract_mpt
from sqlalchemy import create_engine
from watchdog.events import LoggingFileSystemEventHandler
from watchdog.observers import Observer

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]


def impedanzkorr(z_mag_shifted, z_phase_shifted, z_phase):
    if (z_phase < z_phase_shifted) & (z_phase * z_phase_shifted < 0):
        return z_mag_shifted
    else:
        return None


def extract_mpt_wrapper(fpath: str) -> pd.DataFrame:
    file_path, file_name = os.path.split(fpath)
    return extract_mpt(file_path + "/", file_name)


def prepare_peis_file(fpath: str) -> pd.DataFrame:
    peis = extract_mpt_wrapper(fpath)
    peis["Z_mag_shifted"] = peis["Z_mag"].shift()
    peis["Z_phase_shifted"] = peis["Z_phase"].shift()

    peis["Impedanz1"] = peis[["Z_mag_shifted", "Z_phase_shifted", "Z_phase"]].apply(
        lambda imp_args: impedanzkorr(*imp_args), axis=1)

    return peis


class MprFilesHandler(LoggingFileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            logging.info("Directory %s created" % event.src_path)
            time.sleep(5)
            directory_files = [os.path.join(event.src_path, f) for f in os.listdir(event.src_path)]

            peis4_c01_files = [f for f in directory_files if f.endswith("09_PEIS_C01.mpt")]
            cp_c01_files = [f for f in directory_files if f.endswith("08_CP_C01.mpt")]

            logging.info("PEIS file path: %s" % peis4_c01_files[0])
            logging.info("CP data file path: %s" % cp_c01_files[0])

            peis4_c01_df = prepare_peis_file(peis4_c01_files[0])
            cp_c01_df = extract_mpt_wrapper(cp_c01_files[0])

            peis4_value = pd.DataFrame(peis4_c01_df[pd.notnull(peis4_c01_df["Impedanz1"])].iloc[:, :]["Impedanz1"])
            peis4_value["cycle"] = range(1, len(peis4_value) + 1)

            cp_c01_df["times_diff"] = cp_c01_df["times"].diff(1).fillna(0).astype(int)
            cp_c01_df["diff_indicator"] = cp_c01_df["times_diff"].map(lambda diff: 0 if diff <= 1 else 1)
            cp_c01_df["times_grouping"] = cp_c01_df["diff_indicator"].cumsum() + 1

            merged_df = cp_c01_df.merge(peis4_value, left_on="times_grouping", right_on="cycle")
            merged_df["spanung"] = merged_df["Ewe/V"] - (merged_df["I/mA"] / 1000 * merged_df["Impedanz1"])
            merged_df["clean_times"] = (merged_df["times"] - merged_df["times"].min()).astype(int)

            merged_df.columns = [c.lower() for c in merged_df.columns]

            result_df = merged_df[["impedanz1", "cycle", "clean_times", "spanung"]]
            result_df["load_dttm"] = pd.datetime.now()
            result_df["probe_index"] = event.src_path.split("/")[-1]
            psql_string = 'postgresql://{user}:{password}@postgres:5432/{db}'.format(user=POSTGRES_USER,
                                                                                     password=POSTGRES_PASSWORD,
                                                                                     db=POSTGRES_DB)
            engine = create_engine(psql_string)
            logging.info("Writing into database")
            result_df.to_sql('f_experiment', engine, if_exists="replace", chunksize=50000, index=False)
            logging.info("new experiment data written to database")


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
            time.sleep(5)
            logging.info("Observer process is running")
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
