#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import psutil
import json
import copy
import logging
import traceback
import platform

from util import common
from util import cmd_util


instanceId=os.environ.get("EASYOPS_COLLECTOR_instanceId")

RATE = "rate"
GAUGE = "gauge"
DATA_TYPE_LONG = "long"
DATA_TYPE_STRING = "string"
UNIT_KILOBYTES = "kilobytes"
UNIT_PERCENT_100 = "%"


tag_define = [
    {
       "name": "mountpoint",
        "default": "",
        "readOnly": True,
        "description": "磁盘分区名称"
    }
]

Metrics = {
    'host_disk_max_used_percent': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"磁盘最大使用率"
    },
    'host_disk_max_used_percent_mount': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_STRING,
        "unit": "",
        "help": u"磁盘挂载最大使用率"
    },
    'host_disk_used_percent': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"磁盘使用率"
    },
    'host_disk_used_percent_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_PERCENT_100,
        "help": u"磁盘分区最大使用率",
        "tagDefine": tag_define
    },
    'host_disk_total_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘分区容量",
        "tagDefine": tag_define
    },
    'host_disk_used_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘分区已使用容量",
        "tagDefine": tag_define
    },
    'host_disk_free_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘分区空闲容量",
        "tagDefine": []
    },
    'host_disk_used': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘已使用容量"
    },
    'host_disk_free': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘空闲容量"
    },
    'host_disk_total': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘容量"
    },
    'host_disk_inode_total': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘inode总数",
        "tagDefine": tag_define
    },
    'host_disk_inode_free': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘空闲inode数",
        "tagDefine": tag_define
    },
    'host_disk_inode_used': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘已使用inode数",
        "tagDefine": tag_define
    },
    'host_disk_inode_per': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"磁盘inode使用率",
        "tagDefine": tag_define
    },
}

agent_type = "easyops"

param_define = []


def get_disk_linux(timeout):
    retdict = {}
    host_data = {
        'host_disk_max_used_percent': 0,
        'host_disk_max_used_percent_mount': '',
        'host_disk_used_percent': 0,
        'host_disk_used': 0,
        'host_disk_free': 0,
        'host_disk_total': 0,
    }

    partitions = psutil.disk_partitions()
    for partition in partitions:
        if 'cdrom' in partition.opts.lower():
            continue
        if 'removable' in partition.opts.lower():
            continue
        # 光盘
        if partition.fstype.lower() in ['hsf', 'iso9660', 'iso13490', 'udf']:
            continue
        # 虚拟分区
        if partition.fstype.lower() in ['configfs', 'devfs', 'debugfs', 'kernfs', 'procfs', 'specfs', 'sysfs',
                                        'tmpfs', 'winfs']:
            continue
        # custom
        if partition.fstype.lower() in ['proc', 'binfmt_misc', 'devpts']:
            continue

        mountpoint = partition.mountpoint
        usage = psutil.disk_usage(mountpoint)
        if usage.percent > host_data['host_disk_max_used_percent']:
            host_data['host_disk_max_used_percent'] = usage.percent
            host_data['host_disk_max_used_percent_mount'] = mountpoint
        host_data['host_disk_used'] += usage.used
        host_data['host_disk_free'] += usage.free
        host_data['host_disk_total'] += usage.total

        adisk = dict()
        adisk['host_disk_used_per'] = usage.used >> 10
        adisk['host_disk_free_per'] = usage.free >> 10
        adisk['host_disk_total_per'] = usage.total >> 10
        adisk['host_disk_used_percent_per'] = usage.percent
        dim = {'mountpoint': mountpoint}
        retdict[mountpoint] = (dim, adisk)

    host_data['host_disk_used_percent'] = 0
    if host_data['host_disk_total']:
        percent = host_data['host_disk_free'] * 100 / host_data['host_disk_total']
        host_data['host_disk_used_percent'] = 100 - percent
    host_data['host_disk_used'] >>= 10
    host_data['host_disk_free'] >>= 10
    host_data['host_disk_total'] >>= 10

    rcode, output = cmd_util.run_cmd('timeout {timeout} df -i'.format(timeout=timeout), shell=True)
    if not rcode:
        inode_data = {
            'host_disk_inode_total': 0,
            'host_disk_inode_free': 0,
            'host_disk_inode_used': 0,
            'host_disk_inode_per': 0,
        }

        inode_state = output.split('\n')
        for index in range(1, len(inode_state)):
            row = inode_state[index]
            if not row:
                continue
            states = row.split()

            if len(states) < 6:
                continue

            if states[5] not in retdict:
                continue
            inode_data['host_disk_inode_total'] = common.convert_to_int(states[1])
            inode_data['host_disk_inode_used'] = common.convert_to_int(states[2])
            inode_data['host_disk_inode_free'] = common.convert_to_int(states[3])
            inode_data['host_disk_inode_per'] = common.convert_to_int(states[4][:-1])
            retdict[states[5]][1].update(inode_data)

    retdict['host_data'] = ({}, host_data)
    return _submit_metrics(Metrics, retdict.values(), {})


def get_disk_windows():
    import wmi
    wmi_inst = wmi.WMI()

    retlist = []
    host_data = {
        'host_disk_max_used_percent': 0,
        'host_disk_max_used_percent_mount': '',
        'host_disk_used_percent': 0,
        'host_disk_used': 0,
        'host_disk_free': 0,
        'host_disk_total': 0,
    }

    # DriveType: 3, means local disk
    for item in wmi_inst.Win32_LogicalDisk(DriveType=3):
        device_id = item.DeviceID
        free = int(item.FreeSpace)
        total = int(item.Size)
        used = total - free
        used_percent = 0
        if total:
            used_percent = int(round(used * 100.0 / total))

        host_data['host_disk_total'] += total
        host_data['host_disk_free'] += free
        if used_percent > host_data['host_disk_max_used_percent']:
            host_data['host_disk_max_used_percent'] = used_percent
            host_data['host_disk_max_used_percent_mount'] = device_id

        adisk = dict()
        adisk['host_disk_used_per'] = used >> 10
        adisk['host_disk_free_per'] = free >> 10
        adisk['host_disk_total_per'] = total >> 10
        adisk['host_disk_used_percent_per'] = used_percent
        dim = {'mountpoint': device_id}
        retlist.append((dim, adisk))

    host_data['host_disk_total'] >>= 10
    host_data['host_disk_free'] >>= 10
    host_data['host_disk_used'] = host_data['host_disk_total'] - host_data['host_disk_free']
    host_data['host_disk_used_percent'] = 0
    if host_data['host_disk_total']:
        percent = int(round(host_data['host_disk_used'] * 100.0 / host_data['host_disk_total']))
        host_data['host_disk_used_percent'] = percent
    retlist.append(({}, host_data))

    return _submit_metrics(Metrics, retlist, {})


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

def run(timeout):
    system_type = platform.system().lower()
    if system_type == "windows":
        return get_disk_windows()
    elif system_type == "linux" or system_type == "darwin":
        return get_disk_linux(timeout)
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
        run(60)
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error("run collect disk error, err=%s", e.message)
