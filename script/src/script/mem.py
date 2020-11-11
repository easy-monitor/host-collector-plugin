#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-

import os
import psutil
import json
import copy
import platform
import traceback
import logging


instanceId=os.environ.get("EASYOPS_COLLECTOR_instanceId")

RATE = "rate"
GAUGE = "gauge"
DATA_TYPE_LONG = "long"
DATA_TYPE_STRING = "string"


tag_define = [
]

Metrics = {
    # windows
    'host_mem_modified': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "已修改内存"
    },
    'host_mem_standby': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "待机内存"
    },
    # linux
    'host_mem_free': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "空闲内存大小"
    },
    'host_mem_total': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "总内存大小"
    },
    'host_mem_cached': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "已缓存内存"
    },
    'host_mem_buffers': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "内存缓冲区大小"
    },
    'host_mem_percent': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "%",
        "help": "内存使用百分比"
    },
    'host_mem_available': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "可用内存大小"
    },
    'host_mem_used': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "已使用内存大小"
    },
    'host_mem_swap_total': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "内存交换区大小"
    },
    'host_mem_swap_used': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "已使用内存交换区大小"
    },
    'host_mem_swap_free': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kilobytes",
        "help": "空闲内存交换区大小"
    },
    'host_mem_swap_percent': {
        "metric_type": GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "%",
        "help": "已使用内存交换区百分比"
    },
}

agent_type = "easyops"


param_define = []

def get_memory_info_linux():
    virtual_memory = psutil.virtual_memory()
    swap_memory = psutil.swap_memory()
    # 在lxc机器，psutil<5.0版本，内存得到的是母机的
    # 5.4.3 以上psutil计算方式
    # used = total - free - cached - buffers
    # if used < 0:
    #     used = total - free

    # 4.3.0 psutil计算方式
    # used = total - free
    cached = getattr(virtual_memory, 'cached', 0)
    buffers = getattr(virtual_memory, 'buffers', 0)
    free = getattr(virtual_memory, 'free', 0)
    total = getattr(virtual_memory, 'total', 1)

    if psutil.version_info == (4, 3, 0):
        percent = float(total - free - buffers - cached) / float(total) * 100
    else:
        percent = float(getattr(virtual_memory, 'used', 0)) / float(total) * 100
    data = {
        'host_mem_free': free / 1024,
        'host_mem_total': total / 1024,
        'host_mem_cached': cached / 1024,
        'host_mem_buffers': buffers / 1024,
        'host_mem_percent': percent,
        'host_mem_available': getattr(virtual_memory, 'available', 0) / 1024,
        'host_mem_used': getattr(virtual_memory, 'used', 0) / 1024,
        'host_mem_swap_total': getattr(swap_memory, 'total', 0) / 1024,
        'host_mem_swap_used': getattr(swap_memory, 'used', 0) / 1024,
        'host_mem_swap_free': getattr(swap_memory, 'free', 0) / 1024,
        'host_mem_swap_percent': getattr(swap_memory, 'percent', 0),
    }
    return _submit_metrics(Metrics, [({}, data)], {})


def get_memory_info_windows():
        import wmi
        wmi_inst = wmi.WMI()

        from win32com.client import Dispatch
        comp = wmi_inst.Win32_OperatingSystem()[0]
        total = int(comp.TotalVisibleMemorySize)

        try:
            objWMIService = Dispatch("WbemScripting.SWbemLocator")
            conn_server = objWMIService.ConnectServer('localhost', "root\cimv2")  # noqa

            col_items = conn_server.ExecQuery(
                "SELECT AvailableKBytes, StandbyCacheNormalPriorityBytes, StandbyCacheReserveBytes, \
                FreeAndZeroPageListBytes, ModifiedPageListBytes FROM Win32_PerfFormattedData_PerfOS_Memory"
            )

            for item in col_items:
                available = int(item.AvailableKBytes)
                standby = (int(item.StandbyCacheNormalPriorityBytes) + int(item.StandbyCacheReserveBytes)) / 1024
                free = int(item.FreeAndZeroPageListBytes) / 1024
                modified = int(item.ModifiedPageListBytes) / 1024
        except Exception:
            usage_ins = wmi_inst.Win32_PerfRawData_PerfOS_Memory()[0]
            available = int(getattr(usage_ins, "AvailableKBytes", 0))
            # windows server 2003 cat not get standby, free, modified
            standby = (
                int(getattr(usage_ins, "StandbyCacheNormalPriorityBytes", 0)) +
                int(getattr(usage_ins, "StandbyCacheReserveBytes", 0))
            ) / 1024
            free = int(getattr(usage_ins, "FreeAndZeroPageListBytes", 0)) / 1024
            modified = int(getattr(usage_ins, "ModifiedPageListBytes", 0)) / 1024

        data = {
            'host_mem_available': available,
            'host_mem_free': free,
            'host_mem_percent': (total - available) * 100 / total,
            'host_mem_total': total,
            'host_mem_used': total - free - standby - modified,
            'host_mem_cached': modified + standby,
            'host_mem_modified': modified,
            'host_mem_standby': standby,
            'host_mem_buffers': 0
        }
        if data['host_mem_used'] == data['host_mem_total']:
            data['host_mem_used'] = data['host_mem_total'] - data['host_mem_available']
        return _submit_metrics(Metrics, [({}, data)], {})


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
        return get_memory_info_windows()
    elif system_type == "linux" or system_type == "darwin":
        return get_memory_info_linux()
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
            metric['tagDefine'] = tag_define
        metric['key'] = name
        metric_list.append(metric)
    return json.dumps(metric_list, indent=4)


if __name__ == "__main__":
    # output_metric()
    try:
        run(60)
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error("run collect disk error, err=%s", e.message)

