import unittest
from fresser.main import MprFilesHandler
from watchdog.observers import Observer
import shutil, tempfile
import logging
import os 
import pandas as pd 
import time 

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

class BaseTest(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.event_handler = MprFilesHandler()
        self.observer = Observer()
        self.observer.schedule(self.event_handler, self.test_dir, recursive=True)
        logging.info("Observing directory %s" % self.test_dir)
        self.observer.start()
        logging.info("Test directory created, test started: %s" % self.test_dir)

    def tearDown(self):
        # Remove the directory after the test
        shutil.rmtree(self.test_dir)
        self.observer.stop()

    def test_sample(self):
        copytree("tests/resources",self.test_dir)
        time.sleep(10)
        self.assertIsInstance(self.event_handler.peis_c01_df,pd.DataFrame)

if __name__ == '__main__':
    print("Starting tests")
    unittest.main()
