#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-


import os
import json
import logging
import traceback
import yaml

from script.cpu import output_metric as get_cpu_metric_definition
from script.disk import output_metric as get_disk_metric_definition
from script.disk_io import output_metric as get_disk_io_metric_definition
from script.mem import output_metric as get_mem_metric_definition
from script.network import output_metric as get_network_metric_definition
from util import common


def get_plugin_define():
    plugin_define_file_path = os.path.abspath(os.path.join(__file__, "../../plugin.yaml"))
    try:
        with open(plugin_define_file_path) as f:
            return yaml.load(f)
    except Exception:
        return {}

if __name__ == '__main__':
    common.log_setup()

    get_metric_definition_entries = {
        "cpu": get_cpu_metric_definition,
        "disk": get_disk_metric_definition,
        "disk_io": get_disk_io_metric_definition,
        "mem": get_mem_metric_definition,
        "network": get_network_metric_definition
    }
    plugin_define = get_plugin_define()
    if not plugin_define.get("name"):
        print "get plugin name fail"
    plugin_name = plugin_define['name']

    metric_definition_list = []
    try:
        for metric_definition_type, entry in get_metric_definition_entries.iteritems():
            logging.info("Get \"%s\" metric definition", metric_definition_type)
            metrics = json.loads(entry())
            for metric in metrics:
                del metric["name"]
            metric_definition_list.extend(metrics)
            logging.info("Get \"%s\" metric definition successfully", metric_definition_type)
    except Exception as e:
        logging.error(traceback.format_exc())

    with open("./origin_metric.json", "w") as origin_metric_file:
        origin_metric_file.write(json.dumps(metric_definition_list, indent=4))
