#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import psutil
import json
import platform
import traceback
import re
import copy
import json
import time
import logging
from collections import defaultdict

from util import cmd_util

instanceId=os.environ.get("EASYOPS_COLLECTOR_instanceId")

RATE = "rate"
GAUGE = "gauge"
DATA_TYPE_LONG = "long"
DATA_TYPE_STRING = "string"
UNIT_KILOBYTES = "kilobytes/s"

header_re = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
item_re = re.compile(r'^([\-a-zA-Z0-9\/]+)')
value_re = re.compile(r'\d+\.\d+')
disk_blacklist = ['dm-']


tag_define = [
    {
        "name": "disk_name",
        "default": "",
        "readOnly": True,
        "description": u"磁盘名称"
    },
]

Metrics = {
    'host_io_r_s': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"每秒完成的读 I/O 设备次数"
    },
    'host_io_w_s': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"每秒完成的写 I/O 设备次数"
    },
    'host_io_rkbyte_s': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"每秒读K字节数"
    },
    'host_io_wkbyte_s': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"每秒写K字节数"
    },
    'host_io_avgrq_sz': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"平均每次设备I/O操作的数据大小"
    },
    'host_io_await': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "ms",
        "help": u"平均每次设备I/O操作的等待时间 (毫秒)"
    },
    'host_io_svctm': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "ms",
        "help": u"平均每次设备I/O操作的服务时间 (毫秒)"
    },
    'host_io_util': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "%",
        "help": u"一秒中有百分之多少的时间用于 I/O 操作"
    },

    'host_io_r_s_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"磁盘每秒完成的读 I/O 设备次数",
        "tagDefine": tag_define
    },
    'host_io_w_s_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"磁盘每秒完成的写 I/O 设备次数",
        "tagDefine": tag_define
    },
    'host_io_rkbyte_s_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘每秒读K字节数",
        "tagDefine": tag_define
    },
    'host_io_wkbyte_s_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘每秒写K字节数",
        "tagDefine": tag_define
    },
    'host_io_avgrq_sz_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"磁盘平均每次设备I/O操作的数据大小",
        "tagDefine": tag_define
    },
    'host_io_await_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "ms",
        "help": u"磁盘平均每次设备I/O操作的等待时间 (毫秒)",
        "tagDefine": tag_define
    },
    'host_io_svctm_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "ms",
        "help": u"磁盘平均每次设备I/O操作的服务时间 (毫秒)",
        "tagDefine": tag_define
    },
    'host_io_util_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"磁盘一秒中有百分之多少的时间用于 I/O 操作",
        "tagDefine": tag_define
    },
}

agent_type = "easyops"

tag_define = []

param_define = []


def _parse_linux2(output):
    recent_stats = output.split('Device:')[2].split('\n')
    header = recent_stats[0]
    header_names = re.findall(header_re, header)

    io_stats = {}

    for stats_index in range(1, len(recent_stats)):
        row = recent_stats[stats_index]

        if not row:
            # Ignore blank lines.
            continue

        device_match = item_re.match(row)

        if device_match is not None:
            # Sometimes device names span two lines.
            device = device_match.groups()[0]
        else:
            continue

        should_skip = False
        for each_black in disk_blacklist:
            if device.startswith(each_black):
                should_skip = True
                break
        if should_skip:
            continue

        values = re.findall(value_re, row)

        if not values:
            # Sometimes values are on the next line so we encounter
            # instances of [].
            continue

        io_stats[device] = {}

        for header_index in range(len(header_names)):
            header_name = header_names[header_index]
            io_stats[device][header_name] = values[header_index]

    return io_stats


def get_io_info():
    # mac下是不支持的
    cmd = 'iostat -x 1 2 -d -k'
    rcode, output = cmd_util.run_cmd(cmd, shell=True)
    if rcode:
        logging.error('can not found the iostat command')
        return

    all_disk_io = _parse_linux2(output)

    host_data = {
        'host_io_r_s': 0,
        'host_io_w_s': 0,
        'host_io_rkbyte_s': 0,
        'host_io_wkbyte_s': 0,
        'host_io_avgrq_sz': 0,
        'host_io_await': 0,
        'host_io_svctm': 0,
        'host_io_util': 0
    }

    per_disk = {}
    for each_disk, disk_metric in all_disk_io.items():
        host_data['host_io_r_s'] += float(disk_metric.get('r/s', 0))
        host_data['host_io_w_s'] += float(disk_metric.get('w/s', 0))
        host_data['host_io_rkbyte_s'] += float(disk_metric.get('rkB/s', 0))
        host_data['host_io_wkbyte_s'] += float(disk_metric.get('wkB/s', 0))
        host_data['host_io_avgrq_sz'] += float(disk_metric.get('avgrq-sz', 0))

        host_data['host_io_await'] = max(host_data['host_io_await'], float(disk_metric.get('await', 0)))
        host_data['host_io_svctm'] = max(host_data['host_io_svctm'], float(disk_metric.get('svctm', 0)))
        host_data['host_io_util'] = max(host_data['host_io_util'], float(disk_metric.get('%util', 0)))

        item = dict()
        item['host_io_r_s_per'] = float(disk_metric.get('r/s', 0))
        item['host_io_w_s_per'] = float(disk_metric.get('w/s', 0))
        item['host_io_rkbyte_s_per'] = float(disk_metric.get('rkB/s', 0))
        item['host_io_wkbyte_s_per'] = float(disk_metric.get('wkB/s', 0))
        item['host_io_avgrq_sz_per'] = float(disk_metric.get('avgrq-sz', 0))
        item['host_io_await_per'] = float(disk_metric.get('await', 0))
        item['host_io_svctm_per'] = float(disk_metric.get('svctm', 0))
        item['host_io_util_per'] = float(disk_metric.get('%util', 0))
        per_disk[each_disk] = ({"disk_name": each_disk}, item)

    if all_disk_io:
        host_data['host_io_avgrq_sz'] /= len(all_disk_io)
        host_data['host_io_util'] = min(host_data['host_io_util'], 100.0)
        result = [({}, host_data)]
        result.extend(per_disk.values())
        return _submit_metrics(Metrics, result, {})
    else:
        logigng.warn("collect empty io data")
        return


def convert_obj_to_map(ts, data):
    data_map = {
        'io_time': ts,
        'io_stat':  defaultdict(dict),
    }

    for disk, nval in data.iteritems():
        data_map['io_stat'][disk]['read_count'] = nval.read_count
        data_map['io_stat'][disk]['write_count'] = nval.write_count
        data_map['io_stat'][disk]['read_bytes'] = nval.read_bytes
        data_map['io_stat'][disk]['write_bytes'] = nval.write_bytes
        data_map['io_stat'][disk]['read_time'] = nval.read_time
        data_map['io_stat'][disk]['write_time'] = nval.write_time
    return data_map


def set_last_status_windows(data):
    with open("last_io_stat_psutil.json", "w") as f:
        f.write(json.dumps(data))


def get_last_status_windows():
    try:
        with open("last_io_stat_psutil.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error("get windows io last state error, err=%s", e.message)
        return {}


def _sum_cpu_time(cpu_time):
    if platform.system().lower() in ['windows', 'darwin']:
        return cpu_time.user + cpu_time.system + cpu_time.idle
    else:
        return cpu_time.user + cpu_time.system + cpu_time.idle + cpu_time.iowait


def get_io_info_windows():
    curr_stat = psutil.disk_io_counters(True)
    if not curr_stat:
        logging.error("get io info %s from psutil, skip", curr_stat)
        return

    cpu_count = psutil.cpu_count(logical=True)
    curr_cpu_time = _sum_cpu_time(psutil.cpu_times()) / cpu_count

    last_stat = get_last_status_windows()

    # 刚启动，第1次采集
    if not last_stat:
        if curr_cpu_time == 0:
            logging.error("get error cpu_time, return")
            return

        set_last_status_windows(convert_obj_to_map(curr_cpu_time, curr_stat))
        time.sleep(5)
        return get_io_info_windows()

    curr_stat = convert_obj_to_map(curr_cpu_time, curr_stat)
    io_data = {
        'host_io_r_s': 0,
        'host_io_w_s': 0,
        'host_io_rkbyte_s': 0,
        'host_io_wkbyte_s': 0,
        'host_io_await': 0,
        'host_io_avgrq_sz': 0,
        'host_io_svctm': 0,
        'host_io_util': 0
    }

    ts = curr_cpu_time - last_stat['io_time']
    per_disk_data = {}
    for disk, nval in curr_stat['io_stat'].iteritems():
        skip = False
        for each_black in disk_blacklist:
            if disk.startswith(each_black):
                skip = True
                break
        if skip:
            continue

        oval = last_stat['io_stat'].get(disk)
        # 有新增磁盘
        if not oval:
            continue
        total_time = nval['write_time'] - oval['write_time'] + nval['read_time'] - oval['read_time']
        total_count = nval['write_count'] - oval['write_count'] + nval['read_count'] - oval['read_count']
        if not total_count:  # 该磁盘没有IO操作，不参与平均
            continue
        io_data['host_io_w_s'] += (nval['write_count'] - oval['write_count']) / ts
        io_data['host_io_wkbyte_s'] += (nval['write_bytes'] - oval['write_bytes']) / 1024 / ts
        io_data['host_io_r_s'] += (nval['read_count'] - oval['read_count']) / ts
        io_data['host_io_rkbyte_s'] += (nval['read_bytes'] - oval['read_bytes']) / 1024 / ts
        io_data['host_io_await'] += total_time / total_count if total_count else 0.0

        if hasattr(oval, 'busy_time'):  # linux下psutil==4.0.0才有busy_time
            if io_data['host_io_svctm'] is None:
                io_data['host_io_svctm'] = 0
            io_data['host_io_svctm'] += (nval['busy_time'] - oval['busy_time']) / total_count if total_count else 0.0

            if io_data['host_io_util'] is None:
                io_data['host_io_util'] = 0
            io_util = (nval['busy_time'] - oval['busy_time']) * 100.0 / (ts * 1000)
            io_data['host_io_util'] = min(max(io_util, io_data['host_io_util']), 100)

        item = dict()
        item['host_io_r_s_per'] = (nval['read_count'] - oval['read_count']) / ts
        item['host_io_rkbyte_s_per'] = (nval['read_bytes'] - oval['read_bytes']) / 1024 / ts
        item['host_io_w_s_per'] = (nval['write_count'] - oval['write_count']) / ts
        item['host_io_wkbyte_s_per'] = (nval['write_bytes'] - oval['write_bytes']) / 1024 / ts
        item['host_io_await_per'] = total_time / total_count if total_count else 0.0
        item['host_io_avgrq_sz_per'] = 0
        item['host_io_svctm_per'] = 0
        item['host_io_util_per'] = 0
        if hasattr(oval, 'busy_time'):  # linux下psutil==4.0.0才有busy_time
            item['host_io_svctm_per'] = 0
            if total_count:
                item['host_io_svctm_per'] = (nval['busy_time'] - oval['busy_time']) / total_count
            io_util = (nval['busy_time'] - oval['busy_time']) * 100.0 / (ts * 1000)
            item['host_io_util_per'] = min(io_util, 100)

        per_disk_data[disk] = ({"disk_name": disk}, item)

    set_last_status_windows(curr_stat)
    result = [({}, io_data)]
    result.extend(per_disk_data.values())
    return _submit_metrics(Metrics, result, {})


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


def run():
    system_type = platform.system().lower()
    if system_type == "windows":
        import psutil
        return get_io_info_windows()
    elif system_type == "linux" or system_type == "darwin":
        return get_io_info()
    elif system_type == "aix":
        logging.error("not support yet")
    else:
        logging.error("not support current system %s", system_type)


def output_metric():
    metric_list = []
    for name, metric in Metrics.iteritems():
        metric['name'] = name
        metric['agentType'] = agent_type
        metric['paramDefine'] = param_define
        if 'tagDefine' not in metric:
            metric['tagDefine'] = []
        metric['key'] = name
        metric_list.append(metric)
    return json.dumps(metric_list, indent=4)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error("run collect disk error, err=%s", e.message)

