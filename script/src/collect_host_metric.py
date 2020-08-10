import multiprocessing as mp
import time
import os
import json
import logging
import traceback

from script.disk import run as collect_disk
from script.mem import run as collect_mem
from script.disk_io import run as collect_disk_io
from script.cpu import run as collect_cpu
from script.network import run as collect_network
from util import common

timeout=os.environ.get("EASYOPS_COLLECTOR_timeout")


if __name__ == '__main__':
    common.log_setup()
    pool = mp.Pool(processes=5)
    if not timeout:
        timeout = 50
        logging.info("use default timeout 50")
    timeout = int(timeout)
    logging.info("timeout is %d", timeout)

    collect_entries = {
        "collect_disk": collect_disk,
        "collect_mem": collect_mem,
        "collect_io": collect_disk_io,
        "collect_cpu": collect_cpu,
        "collect_network": collect_network
    }

    results = {}
    for colect_type, entry in collect_entries.iteritems():
        p = pool.apply_async(entry, ())
        results[colect_type] = p
        logging.info("start process for type %s", colect_type)

    pool.close()
    # pool.join()

    join_list = []
    for collect_type, p in results.iteritems():
        try:
            join_list.extend(json.loads(p.get(timeout)))
            logging.debug("load %s output complete", colect_type)
        except mp.TimeoutError as e:
            logging.error("process %s run timeout, will not collect", collect_type)
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.error("load process %s output %s error", collect_type, p.get(timeout))

    logging.debug("result %s", json.dumps(join_list))
    print json.dumps(join_list)
