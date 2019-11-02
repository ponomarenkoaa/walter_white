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


def prepare_peis_c01_file(fpath: str) -> pd.DataFrame:
    file_path, file_name = os.path.split(fpath)
    peis1 = extract_mpt(file_path + "/", file_name)
    print(peis1.head())
    print(list(peis1.columns.values))
    print(peis1[['Z_mag', 'Z_phase']])
    peis1["Z_mag_shifted"] = peis1["Z_mag"].shift()
    peis1["Z_phase_shifted"] = peis1["Z_phase"].shift()

    def impedanzkorr(z_mag_shifted, z_phase_shifted, z_phase):
        if (z_phase < z_phase_shifted) & (z_phase * z_phase_shifted < 0):
            return z_mag_shifted
        else:
            return None

    peis1["Impedanz1"] = peis1[["Z_mag_shifted", "Z_phase_shifted", "Z_phase"]].apply(
        lambda imp_args: impedanzkorr(*imp_args), axis=1)
    return peis1


def prepare_mp_c01_file(fpath: str) -> pd.DataFrame:
    file_path, file_name = os.path.split(fpath)
    mp = extract_mpt(file_path + "/", file_name)
    print(mp.head())
    print(list(mp.columns.values))
    mp["counter_inc_shifted"] = mp["counter inc."].shift()

    def mpfun(counter_inc_shifted, counter_inc, ns_changes):
        if (counter_inc * counter_inc_shifted == 0) & ((abs(counter_inc_shifted - counter_inc)) == 1):
            return ns_changes
        else:
            return 0

    mp["cycle"] = mp[["counter_inc_shifted", "counter inc.", "Ns_changes"]].apply(
        lambda cycle_args: mpfun(*cycle_args), axis=1).cumsum()

    return mp


class MprFilesHandler(LoggingFileSystemEventHandler):
    def __init__(self):
        self.peis_c01_df = None

    def on_created(self, event):
        if event.is_directory:
            logging.info("Directory %s created" % event.src_path)
            time.sleep(5)
            directory_files = [os.path.join(event.src_path, f) for f in os.listdir(event.src_path)]

            peis_c01_files = [f for f in directory_files if f.endswith("03_PEIS_C01.mpt")]
            mp_c01_files = [f for f in directory_files if f.endswith("04_MP_C01.mpt")]

            if len(peis_c01_files) != 1:
                raise BaseException("Problem with peis c01 files, peis file list %s" % peis_c01_files)

            if len(mp_c01_files) != 1:
                raise BaseException("Problem with mp c01 files")

            peis_c01_df = prepare_peis_c01_file(peis_c01_files[0])
            mp_c01_df = prepare_mp_c01_file(mp_c01_files[0])

            peis1_value = peis_c01_df[pd.notnull(peis_c01_df["Impedanz1"])].iloc[0, :]["Impedanz1"]
            print(peis1_value)

            mp_c01_df["U korr/V"] = mp_c01_df["EweV"] - (mp_c01_df["I_avg"] / 1000 * peis1_value)

            oberflaeche = 0.073
            mp_c01_df["mA/cm2"] = mp_c01_df["I_avg"]/oberflaeche
            print(mp_c01_df)
            self.peis_c01_df = peis_c01_df

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=str)
    args = parser.parse_args()

    event_handler = MprFilesHandler()
    observer = Observer()
    observer.schedule(event_handler, args.path, recursive=True)
    logging.info("Observing directory %s" % args.path)
    observer.start()
    logging.info("something happening here")
    try:
        while True:
            time.sleep(1)
            logging.info("and every second, here")
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
