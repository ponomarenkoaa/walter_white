import logging
import os
import shutil
import tempfile
import time
import unittest

import pandas as pd
from watchdog.observers import Observer

from mendeleev.main import MprFilesHandler

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
        self.observer.stop()
        shutil.rmtree(self.test_dir)

    def test_sample(self):
        copytree("tests/resources", self.test_dir)
        time.sleep(10)


if __name__ == '__main__':
    print("Starting tests")
    unittest.main()
