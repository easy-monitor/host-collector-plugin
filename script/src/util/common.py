#!/usr/local/easyops/python/bin/python
# _*_coding: utf-8_*_


import logging
import yaml
import os
import hashlib
import logging.handlers

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


EAYSOPS_PATH = os.environ.get("EASYOPS_BASE_PATH", "")
if EAYSOPS_PATH == "":
    EAYSOPS_PATH =  "/usr/local/easyops"

log_file_path = os.path.join(BASE_PATH, "log")
if not os.path.exists(log_file_path):
    os.mkdir(log_file_path)



def convert_to_int(value, default=0):
    if value.isdigit():
        return int(value)
    else:
        return default

def log_setup():
    log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_file_path, 'collector.log'),
        maxBytes=20000000,
        backupCount=5
    )

    formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
    log_handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
