#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-


import copy
import json
import logging
import os
import platform
import time
import traceback
from collections import deque

import psutil


if platform.system().lower() == 'windows':
    import wmi


# constants
METRIC_TYPE_GAUGE = "gauge"

DATA_TYPE_LONG = "long"

UNIT_KILOBYTES = "kilobytes"
UNIT_PERCENT_100 = "%"


tag_define = [
]

Metrics = {
    'host_cpu_used_us': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"用户级 CPU 使用率"
    },
    'host_cpu_used_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"CPU 使用率"
    },
    'host_cpu_used_wa': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"I/O Wait 的 CPU 使用率"
    },
    'host_cpu_used_sy': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"系统级 CPU 使用率"
    },
    'host_load_1': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"1分钟平均负载"
    },
    'host_load_5': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"5分钟平均负载"
    },
    'host_load_15': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"15分钟内平均负载"
    },
    'host_load_1_per_core': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"单核1分钟平均负载"
    },
    'host_load_5_per_core': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"单核5分钟平均负载"
    },
    'host_load_15_per_core': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"单核15分钟内平均负载"
    },
}

agent_type = "easyops"

tag_define = []

param_define = []


class HostCPUCollector(object):

    def __init__(self):
        self.last_cpu_times = None
        self.collector_interval = 2

    def get_cpu_info(self):
        cpu_info = {}
        average_load = os.getloadavg()
        
        cpu_physical_cores = psutil.cpu_count(logical=True)
        cpu_info.update({
            'host_load_1': average_load[0],
            'host_load_5': average_load[1],
            'host_load_15': average_load[2],
            'host_load_1_per_core': '%.2f' % (average_load[0] / cpu_physical_cores),
            'host_load_5_per_core': '%.2f' % (average_load[1] / cpu_physical_cores),
            'host_load_15_per_core': '%.2f' % (average_load[2] / cpu_physical_cores)
        })
        # 初始化psutil内部计数缓存
        psutil.cpu_percent()
        psutil.cpu_times_percent()
        time.sleep(3)

        cpu_info.update({"host_cpu_used_total": int(psutil.cpu_percent())})
        cpu_times_percent = psutil.cpu_times_percent()
        cpu_info['host_cpu_used_sy'] = self._get_cpu_time('system', cpu_times_percent)
        cpu_info['host_cpu_used_us'] = self._get_cpu_time('user', cpu_times_percent)
        cpu_info['host_cpu_used_wa'] = self._get_cpu_time('iowait', cpu_times_percent)
        return cpu_info

    def _get_cpu_time(self, attr, stat):
        return getattr(stat, attr, None)


class WindowsHostCPUCollector(HostCPUCollector):

    _queue_len_cache = deque([0 for _ in range(15)], maxlen=15)

    def __init__(self):
        super(WindowsHostCPUCollector, self).__init__()
        self.wmi_inst = wmi.WMI()

    def get_cpu_info(self):
        used_total = 0
        collect_time = 3
        for i in range(collect_time):
            for item in self.wmi_inst.Win32_PerfFormattedData_PerfOS_Processor():
                if item.name == '_Total':
                    used_total += int(getattr(item, "PercentProcessorTime", 0))
            time.sleep(self.collector_interval)
        host_data = {'host_cpu_used_total': used_total / collect_time}

        try:
            host_data.update(self._get_cpu_load())
        except Exception as e:
            print e

        return host_data

    def _get_cpu_load(self):
        host_data = {}
        queue_len_cache = WindowsHostCPUCollector._queue_len_cache
        processor_queue_len = 0
        for item in self.wmi_inst.Win32_PerfFormattedData_PerfOS_System():
            processor_queue_len += item.ProcessorQueueLength
        queue_len_cache.append(int(processor_queue_len))
        host_data['host_load_1'] = queue_len_cache[-1]

        latest_5_time_value = 0
        for i in range(10, 15):
            latest_5_time_value += queue_len_cache[i]
        host_data['host_load_5'] = latest_5_time_value / 5

        latest_15_time_value = 0
        for i in range(15):
            latest_15_time_value += queue_len_cache[i]
        host_data['host_load_15'] = latest_15_time_value / 15
        return host_data


def run(timeout):
    system_type = platform.system().lower()
    if system_type == "windows":
        windows_host_cpu_collector = WindowsHostCPUCollector()
        cpu_info = windows_host_cpu_collector.get_cpu_info()
        return _submit_metrics(Metrics, [({}, cpu_info)], {})
    elif system_type == "linux" or system_type == "darwin":
        host_cpu_collector = HostCPUCollector()
        cpu_info = host_cpu_collector.get_cpu_info()
        return _submit_metrics(Metrics, [({}, cpu_info)], {})
    elif system_type == "aix":
        logging.error("not support yet")
    else:
        logging.error("not support current system %s", system_type)


def _submit_metrics(metrics, results, tags):
    output = []
    host_result = {
        'dims': {},
        'vals': {}
    }

    for data in results:
        host_data = copy.deepcopy(host_result)
        tag, collect_result = data
        host_data['dims'].update(tags)
        host_data['dims'].update(tag)

        for metric_key, value in collect_result.iteritems():
            if not metric_key in metrics:
                continue
            host_data['vals'][metric_key] = value

        output.append(host_data)
    return json.dumps(output, indent=4)


def output_metric():
    metric_list = []
    for name, metric in Metrics.iteritems():
        metric['name'] = name
        metric['agentType'] = agent_type
        metric['paramDefine'] = param_define
        if 'tagDefine' not in metric:
            metric['tagDefine'] = tag_define
        metric['key'] = name
        metric_list.append(metric)
    return json.dumps(metric_list, indent=4)


if __name__ == "__main__":
    try:
        # print output_metric()
        print run(60)
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error("run collect cpu error, err=%s", e.message)
