#! /usr/local/easyops/python/bin/python
# -*- coding: utf-8 -*-


import copy
import json
import logging
import platform
import socket
import subprocess
import tempfile
import time
import traceback
from contextlib import nested

import chardet
import psutil

codec_list = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig']


def try_decode2unicode(msg, code=None):
    if not msg:
        return msg

    if isinstance(msg, unicode):
        return msg

    if code:
        return msg.decode(code)

    for codec in codec_list:
        try:
            return msg.decode(codec)
        except Exception, e:
            pass
    # 如果没能解码，使用chardet
    ret = chardet.detect(msg)
    charset = ret['encoding']
    if charset is not None and charset != 'ascii':
        msg = msg.decode(charset, errors='ignore')
    return msg


def do_cmd(command, shell=False, close_fds=False, stdin=None, only_stdout=False, **kwargs):
    """
    Run the given subprocess command and return it's output. Raise an Exception
    if an error occurs.
    """

    # # Use tempfile, allowing a larger amount of memory. The subprocess.Popen
    # # docs warn that the data read is buffered in memory. They suggest not to
    # # use subprocess.PIPE if the data size is large or unlimited.
    # env = dict(kwargs.pop('env', {})) if kwargs.get('env') else os.environ.copy()
    # if platform.system() != "Windows":
    #     if env.get('PATH', None):
    #         env['PATH'] = '%s:%s' % (ESSENTIAL_TOOLS_PATH, env['PATH'])
    #     else:
    #         env['PATH'] = ':'.join([ESSENTIAL_TOOLS_PATH, os.getenv('PATH')])

    with nested(tempfile.TemporaryFile(), tempfile.TemporaryFile()) as (stdout_f, stderr_f):
        proc = subprocess.Popen(
            command,
            close_fds=close_fds,  # only set to True when on Unix, for WIN compatibility
            shell=shell,
            stdin=stdin,
            stdout=stdout_f,
            stderr=stderr_f,
            **kwargs
        )
        proc.wait()
        stderr_f.seek(0)
        err = stderr_f.read()

        stdout_f.seek(0)
        output = stdout_f.read()

    if only_stdout:
        result = output
    else:
        result = err or output

    return proc.returncode, result


def convert_to_int(value, default=0):
    if value.isdigit():
        return int(value)
    else:
        return default


# constants
METRIC_TYPE_GAUGE = "gauge"
METRIC_TYPE_CALC = "calculated"

DATA_TYPE_LONG = "long"
DATA_TYPE_STRING = "string"

UNIT_KILOBYTES = "kilobytes/s"
UNIT_KILOBITS_PER_SECOND = "kilobits/sec(Kbps)"

tagDefine = [
]

interfaceTagDefine = [
    {
        "name": "interface",
        "default": "",
        "readOnly": True,
        "description": u"网卡名称"
    },
    {
        "name": "interface_ip",
        "default": "",
        "readOnly": True,
        "description": u"网卡 IP"
    },
]

Metrics = {
    'host_net_error_in': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"网络接收错误包量",
        "tagDefine": tagDefine
    },
    'host_net_error_out': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"网络发送错误包量",
        "tagDefine": tagDefine
    },
    'host_net_conn_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"网络连接数",
        "tagDefine": tagDefine
    },
    'host_net_bits_out': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"出流量",
        "tagDefine": tagDefine
    },
    'host_net_drop_in': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"丢弃入流量",
        "tagDefine": tagDefine
    },
    'host_net_packages_out': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"数据包出流量",
        "tagDefine": tagDefine
    },
    'host_net_packages_in': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"数据包入流量",
        "tagDefine": tagDefine
    },
    'host_net_bits_in': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"入流量",
        "tagDefine": tagDefine
    },
    'host_net_drop_out': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"丢弃出流量",
        "tagDefine": tagDefine
    },
    'host_net_bits_in_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"网卡入流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_packages_in_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBYTES,
        "help": u"网卡数据包入流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_error_in_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"网卡入流量错误",
        "tagDefine": interfaceTagDefine
    },
    'host_net_bits_out_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"网卡出流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_packages_out_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"网卡数据包出流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_error_out_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"网络发送错误包量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_drop_out_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"网卡丢弃出流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_drop_in_per': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": UNIT_KILOBITS_PER_SECOND,
        "help": u"网卡丢弃入流量",
        "tagDefine": interfaceTagDefine
    },
    'host_net_tcp_syn_sent': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"SYN_SENT 连接数量",
    },
    'host_net_tcp_syn_recv': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"SYN_RECV 连接数量",
    },
    'host_net_tcp_established': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"ESTABLISHED 连接数量",
    },
    'host_net_tcp_fin_wait_1': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"FIN-WAIT-1 连接数量",
    },
    'host_net_tcp_close_wait': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"CLOSE-WAIT 连接数量",
    },
    'host_net_tcp_fin_wait_2': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"SYN_FIN-WAIT-2SENT 连接数量",
    },
    'host_net_tcp_last_ack': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"LAST-ACK 连接数量",
    },
    'host_net_tcp_time_wait': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"TIME-WAIT 连接数量",
    },
    'host_net_tcp_closing': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"CLOSING 连接数量",
    },
    'host_net_tcp_closed': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"CLOSED 连接数量",
    },
    'host_net_tcp_listen': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"LISTENING 连接数量",
    },
    'host_net_tcp_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"tcp socket总数",
    },
    'host_net_udp_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"udp socket总数",
    },
    'host_net_unix_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "",
        "help": u"unix socket总数",
    },
    'host_net_drop_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"网络总丢包量",
        "agentType": METRIC_TYPE_CALC,
        "expression": "host_net_drop_in + host_net_drop_out",
    },
    'host_net_error_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"网络总错误包量",
        "agentType": METRIC_TYPE_CALC,
        "expression": "host_net_error_in + host_net_error_out",
    },
    'host_net_packages_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "pps",
        "help": u"网络总包量",
        "agentType": METRIC_TYPE_CALC,
        "expression": "host_net_packages_in + host_net_packages_out",
    },
    'host_net_bits_total': {
        "metric_type": METRIC_TYPE_GAUGE,
        "data_type": DATA_TYPE_LONG,
        "unit": "kbps",
        "help": u"总流量",
        "agentType": METRIC_TYPE_CALC,
        "expression": "host_net_bits_in + host_net_bits_out",
    }
}

agent_type = "easyops"

tag_define = []

param_define = []


class HostNetworkCollector(object):

    def __init__(self):
        self.collector_interval = 2

        self.last_network_time = 0
        self.last_network_stat = {}

    @staticmethod
    def get_eth2ip():
        ret = {}
        result = psutil.net_if_addrs()
        for eth, items in result.iteritems():
            for item in items:
                if item.family == socket.AF_INET:
                    ret[eth] = item.address
                    break
        return ret

    def get_network_info(self):
        network_time = time.time()
        network_stat = psutil.net_io_counters(pernic=True)
        if self.last_network_time == 0:
            self.last_network_time = network_time
            self.last_network_stat = network_stat
            time.sleep(self.collector_interval)
            return self.get_network_info()

        eths_info = []
        host_data = {
            'host_net_bits_in': 0,
            'host_net_bits_out': 0,
            'host_net_packages_in': 0,
            'host_net_packages_out': 0,
            'host_net_error_in': 0,
            'host_net_error_out': 0,
            'host_net_drop_in': 0,
            'host_net_drop_out': 0,
            'host_net_conn_total': 0,
        }
        interval = int(network_time - self.last_network_time)
        eth2ip = self.get_eth2ip()
        eths = network_stat.keys()
        for eth in eths:
            if eth not in eth2ip:
                continue

            # 不采集lo流量
            if eth == 'lo':
                continue
            if eth not in self.last_network_stat:
                continue

            pre = self.last_network_stat[eth]
            cur = network_stat[eth]
            host_data['host_net_bits_in'] += (cur.bytes_recv - pre.bytes_recv)
            host_data['host_net_bits_out'] += (cur.bytes_sent - pre.bytes_sent)
            host_data['host_net_packages_in'] += (cur.packets_recv - pre.packets_recv)
            host_data['host_net_packages_out'] += (cur.packets_sent - pre.packets_sent)
            host_data['host_net_error_in'] += (cur.errin - pre.errin)
            host_data['host_net_error_out'] += (cur.errout - pre.errout)
            host_data['host_net_drop_in'] += (cur.dropin - pre.dropin)
            host_data['host_net_drop_out'] += (cur.dropout - pre.dropout)

            item = dict()
            item['host_net_bits_in_per'] = (cur.bytes_recv - pre.bytes_recv) / 1024 * 8 / interval
            item['host_net_bits_out_per'] = (cur.bytes_sent - pre.bytes_sent) / 1024 * 8 / interval
            item['host_net_packages_in_per'] = (cur.packets_recv - pre.packets_recv) / interval
            item['host_net_packages_out_per'] = (cur.packets_sent - pre.packets_sent) / interval
            item['host_net_error_in_per'] = (cur.errin - pre.errin) / interval
            item['host_net_error_out_per'] = (cur.errout - pre.errout) / interval
            item['host_net_drop_in_per'] = (cur.dropin - pre.dropin) / interval
            item['host_net_drop_out_per'] = (cur.dropout - pre.dropout) / interval

            dims = dict()
            dims['interface'] = try_decode2unicode(eth)
            dims['interface_ip'] = eth2ip[eth]

            eths_info.append((dims, item))

        # unit: kbps
        host_data['host_net_bits_in'] = host_data['host_net_bits_in'] / 1024 * 8 / interval
        host_data['host_net_bits_out'] = host_data['host_net_bits_out'] / 1024 * 8 / interval

        # unit: packets/sec
        host_data['host_net_packages_in'] /= interval
        host_data['host_net_packages_out'] /= interval
        host_data['host_net_error_in'] /= interval
        host_data['host_net_error_out'] /= interval
        host_data['host_net_drop_in'] /= interval
        host_data['host_net_drop_out'] /= interval

        # socket connections (tcp, udp, unix)
        socket_connetions = self._get_connection()
        host_data.update(socket_connetions)

        self.last_network_time = network_time
        self.last_network_stat = network_stat

        return {
            "host_network_data": ({}, host_data),
            "eths_network_data": eths_info
        }

    @staticmethod
    def _get_connection():
        socket_connections = dict()

        # 解析ss输出
        def get_ss_output(ss_cmd):
            rcode, output = do_cmd(ss_cmd, shell=True)
            if rcode != 0:
                return None
            else:
                return output.strip()

        net_tcp_metric = {
            'SYN-SENT': 'host_net_tcp_syn_sent',
            'SYN-RECV': 'host_net_tcp_syn_recv',
            'ESTAB': 'host_net_tcp_established',
            'FIN-WAIT-1': 'host_net_tcp_fin_wait_1',
            'CLOSE-WAIT': 'host_net_tcp_close_wait',
            'FIN-WAIT-2': 'host_net_tcp_fin_wait_2',
            'LAST-ACK': 'host_net_tcp_last_ack',
            'TIME-WAIT': 'host_net_tcp_time_wait',
            'CLOSING': 'host_net_tcp_closing',
            'CLOSED': 'host_net_tcp_closed',
            'LISTEN': 'host_net_tcp_listen'
        }

        state_cmd = "which ss >/dev/null && ss -n -a | awk 'NR>1{a[$1]+=1}END{for (i in a){print i\":\"a[i]}}'"
        state_conn = get_ss_output(state_cmd)

        if not state_conn:
            socket_connections['host_net_conn_total'] = 0
            return socket_connections
        else:
            for line in state_conn.split('\n'):
                line = line.strip()
                if not line:
                    continue

                state, count = line.split(":")
                state = state.strip()
                if state not in net_tcp_metric:
                    continue
                socket_connections[net_tcp_metric[state]] = convert_to_int(count.strip())

        socket_connections['host_net_conn_total'] = socket_connections.get(net_tcp_metric['ESTAB'], '0')

        sort_cmd = 'ss -s'
        sort_count = get_ss_output(sort_cmd)
        state_key_map = {"TCP": 'host_net_tcp_total', "UDP": 'host_net_udp_total'}

        for line in sort_count.split('\n'):
            line = line.strip()
            if not line:
                continue

            columns = line.split()
            if len(columns) < 3:
                continue

            header = columns[0].strip()
            if header in state_key_map:
                socket_connections[state_key_map[header]] = convert_to_int(columns[1].strip())

        unix_cmd = 'ss -n -x -a | tail -n +2 | wc -l'
        socket_connections['host_net_unix_total'] = convert_to_int(get_ss_output(unix_cmd))
        return socket_connections


def run(timeout):
    system_type = platform.system().lower()
    if system_type == "windows":
        host_network_collector = HostNetworkCollector()
        network_info = host_network_collector.get_network_info()
        results = [
            network_info['host_network_data'],
        ]
        for eth_network_data in network_info["eths_network_data"]:
            results.append(eth_network_data)
        return _submit_metrics(Metrics, results, {})
    elif system_type == "linux" or system_type == "darwin":
        host_network_collector = HostNetworkCollector()
        network_info = host_network_collector.get_network_info()
        results = [
            network_info['host_network_data'],
        ]
        for eth_network_data in network_info["eths_network_data"]:
            results.append(eth_network_data)
        return _submit_metrics(Metrics, results, {})
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
        if not 'agentType' in metric:
            metric['agentType'] = agent_type
        metric['paramDefine'] = param_define
        if 'tagDefine' not in metric:
            metric['tagDefine'] = []
        metric['key'] = name
        metric_list.append(metric)
    return json.dumps(metric_list, indent=4)


if __name__ == "__main__":
    try:
        # print output_metric()
        print run(60)
    except Exception as e:
        logging.error(traceback.format_exc())
        logging.error("run collect network error, err=%s", e.message)
