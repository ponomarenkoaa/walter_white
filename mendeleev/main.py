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


def prepare_peis_data(peis: pd.DataFrame) -> pd.DataFrame:
    peis["Z_mag_shifted"] = peis["Z_mag"].shift()
    peis["Z_phase_shifted"] = peis["Z_phase"].shift()
    peis["Impedanz1"] = peis[["Z_mag_shifted", "Z_phase_shifted", "Z_phase"]].apply(
        lambda imp_args: impedanzkorr(*imp_args), axis=1)

    return peis


def calculate_cycle_data(peis: pd.DataFrame) -> pd.DataFrame:
    peis_cycle = pd.DataFrame(peis[pd.notnull(peis["Impedanz1"])].iloc[:, :]["Impedanz1"])
    peis_cycle["cycle"] = range(1, len(peis_cycle) + 1)
    return peis_cycle


class MprFilesHandler(LoggingFileSystemEventHandler):
    def __init__(self):
        self.psql_string = 'postgresql://{user}:{password}@postgres:5432/{db}'.format(user=POSTGRES_USER,
                                                                                      password=POSTGRES_PASSWORD,
                                                                                      db=POSTGRES_DB)
        super(MprFilesHandler, self).__init__()

    @staticmethod
    def read_mpt(fpath: str) -> pd.DataFrame:
        file_path, file_name = os.path.split(fpath)
        return extract_mpt(file_path + "/", file_name)

    @staticmethod
    def find_file(files_list, postfix):
        found_files = [f for f in files_list if f.endswith(postfix)]
        if len(found_files) == 0:
            raise Exception("No file with postfix %s found" % postfix)
        elif len(found_files) > 1:
            raise Exception("Too many files with postfix %s found" % postfix)
        else:
            logging.info("Found file for postfix %s" % postfix)
            return found_files[0]

    def on_created(self, event):
        if event.is_directory:
            # logging directory creation and awaiting for all files to be copied
            logging.info("Directory %s created" % event.src_path)
            time.sleep(5)

            # listing files to find all data sources
            directory_files = [os.path.join(event.src_path, f) for f in os.listdir(event.src_path)]
            all_mpt_files = [f for f in directory_files if f.endswith(".mpt")]

            logging.info("Presented .mpt files are:")

            for mpt_file in all_mpt_files:
                logging.info("\t %s" % mpt_file)

            peis09_path = MprFilesHandler.find_file(all_mpt_files, "09_PEIS_C01.mpt")
            cp08_path = MprFilesHandler.find_file(all_mpt_files, "08_CP_C01.mpt")
            peis05_path = MprFilesHandler.find_file(all_mpt_files, "05_PEIS_C01.mpt")
            cv06_path = MprFilesHandler.find_file(all_mpt_files, "06_CV_C01.mpt")

            peis09_df = MprFilesHandler.read_mpt(peis09_path)
            cp08_df = MprFilesHandler.read_mpt(cp08_path)
            peis05_df = MprFilesHandler.read_mpt(peis05_path)
            cv06_df = MprFilesHandler.read_mpt(cv06_path)

            peis09_df = prepare_peis_data(peis09_df)
            peis05_df = prepare_peis_data(peis05_df)

            peis09_cycle_data = calculate_cycle_data(peis09_df)
            peis05_cycle_data = calculate_cycle_data(peis05_df)

            peis05_impedanz_value = peis05_cycle_data.iloc[0, 0]
            cv06_df["corr_voltage_vs_RHE"] = cv06_df["Ewe/V"] - ((cv06_df["I_avg"] / 1000) * peis05_impedanz_value)
            surface_circle = 0.126
            cv06_df["current_density"] = cv06_df["I_avg"] / surface_circle

            min_current_density = cv06_df["current_density"].min()
            cv06_df["current_density_verschoben"] = cv06_df["current_density"] - min_current_density
            cv06_df["corr_voltage_vs_RHE_shifted"] = cv06_df["corr_voltage_vs_RHE"].shift()
            cv06_df["current_density_verschoben_shifted"] = cv06_df["current_density_verschoben"].shift()
            cv06_df["current_density_cumulative"] = (cv06_df["corr_voltage_vs_RHE"] - cv06_df[
                "corr_voltage_vs_RHE_shifted"]) * (cv06_df["current_density_verschoben"] + cv06_df[
                "current_density_verschoben_shifted"]) / 2

            cv06_df_area = cv06_df.groupby("cycle_number")["current_density_cumulative"].sum().to_frame()
            cycle_speed = 100
            cv06_df_area["C"] = cv06_df_area["current_density_cumulative"] / cycle_speed * surface_circle
            cv06_df_area = cv06_df_area.reset_index()

            cp08_df["times_diff"] = cp08_df["times"].diff(1).fillna(0).astype(int)
            cp08_df["diff_indicator"] = cp08_df["times_diff"].map(lambda diff: 0 if diff <= 1 else 1)
            cp08_df["times_grouping"] = cp08_df["diff_indicator"].cumsum() + 1

            merged_df = cp08_df.merge(peis09_cycle_data, left_on="times_grouping", right_on="cycle")
            merged_df["spanung"] = merged_df["Ewe/V"] - (merged_df["I/mA"] / 1000 * merged_df["Impedanz1"])
            merged_df["clean_times"] = (merged_df["times"] - merged_df["times"].min()).astype(int)

            merged_df.columns = [c.lower() for c in merged_df.columns]

            result_df_cp = merged_df[["impedanz1", "cycle", "clean_times", "spanung"]]
            result_df_cp["load_dttm"] = pd.datetime.now()
            result_df_cp["probe_index"] = event.src_path.split("/")[-1]
            engine = create_engine(self.psql_string)
            logging.info("Writing into database")
            result_df_cv = cv06_df[["Ewe/V", "I_avg","cycle_number", "corr_voltage_vs_RHE","current_density"]]
            result_df_cp.to_sql('cp_experiment', engine, if_exists="replace", chunksize=50000, index=False)
            result_df_cv.to_sql('cv_experiment', engine, if_exists="replace", chunksize=50000, index=False)
            cv06_df_area.to_sql('cv_area_experiment', engine, if_exists="replace", chunksize=50000, index=False)
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
