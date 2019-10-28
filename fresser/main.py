import logging
import time

logging.basicConfig(level=logging.DEBUG)


def action_recorder():
    logging.info("application is running")


if __name__ == '__main__':
    while True:
        action_recorder()
        time.sleep(5)
