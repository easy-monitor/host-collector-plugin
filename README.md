# EasyOps 主机监控插件包

EasyOps 主机监控插件包是适用于 EasyOps 新版监控平台，专门提供主机监控服务的官方插件包。它提供了对主机CPU、内存、磁盘、I/O、网络等常见监控指标进行采集的采集插件以及可视化的仪表盘展示。

## 目录

- [背景](#背景)
- [使用方法](#使用方法)
- [项目内容](#项目内容)
- [工作原理](#工作原理)
- [维护者](#维护者)
- [许可证](#许可证)

## 背景

由于目前在 EasyOps 新版监控平台上搭建主机监控场景需要经过以下步骤：

1. 按照标准输出格式编写采集脚本，并在平台上新建相应的采集插件。
2. 手工录入采集插件具体的原始指标信息。
3. 理解原始指标含义后配置仪表盘展示。

所以为了实现主机监控场景的快速搭建，该项目对主机一些常见的监控指标及其采集脚本进行了封装，同时提供一个基本的仪表盘展示。

用户能够借助 EasyOps 平台提供的自动化工具来一键导入该插件包，真正做到主机监控场景的开箱即用。

## 使用方法

1. 下载该项目的压缩包（https://github.com/easy-monitor/host-collector-plugin/archive/master.zip ）。

2. 建议解压到 EasyOps 平台服务器上的 `/usr/local/easyops/monitor_plugin_packages` 该目录下。

3. 使用 EasyOps 平台内置的插件包导入工具导入该压缩包，具体命令如下（请替换其中的 `8888` 为当前 EasyOps 平台具体的 `org`）。

```sh
$ cd /usr/local/easyops/collector_plugin_service/tools
$ sh plugin_op.sh install 8888 /usr/local/easyops/monitor_plugin_packages/host-collector-plugin
```

4. 导入成功后访问 EasyOps 平台的「采集插件」小产品页面 (http://your-easyops-server/next/collector-plugin)，就能看到导入的 "host_collector_plugin" 采集插件。

5. 接下来可使用该采集插件为具体的主机实例创建采集任务。

## 项目内容

### 目录结构

```
host-collector-plugin
├── dashboard.json
├── origin_metric.json
└── script
    ├── plugin.yaml
    └── src
        ├── collect_host_metric.py
        ├── script
        │    ├── cpu.py
        │    ├── disk_io.py
        │    ├── disk.py
        │    ├── mem.py
        │    └── network.py
        └── ...
```

该项目的目录结构遵循标准的 EasyOps 监控插件包规范，具体内容如下：

- dashboard.json: 仪表盘的定义文件
- origin_metric.json: 采集插件关联的原始指标定义文件
- script: 采集插件关联的程序包目录，执行采集任务时会部署到指定的目标机器上
- script/plugin.yaml: 采集插件程序包的定义文件
- script/src: 采集插件程序包的脚本目录

### plugin.yaml

```yaml
# 支持 easyops/prometheus/zabbix 三种采集类型
# 1. easyops: 表示使用 EasyOps Agent 进行指标采集
# 2. prometheus: 表示对接 Prometheus Exporter 进行指标采集
# 3. zabbix: 表示对接 Zabbix Agent 进行指标采集
agentType: easyops

# 采集插件关联的程序包名称及其版本名称
name: inner_host_collector
version: 1.0.0

# 仅支持 simple-script 采集方式（采集类型为 easyops 时必须指定）
# 1. simple-script 表示使用执行脚本的采集方式
type: simple-script

# 采集命令（采集方式为 simple-script 时必须指定）
command:
  collect:
    type: python                                       # 脚本类型支持 shell/python/powershell
    user: root                                         # 执行用户
    interpreter: /usr/local/easyops/python/bin/python  # 脚本解释器
    scriptPath:                                        # 采集脚本相对 script 目录的路径分割后的数组, 例如：collector_script.py 的相对路径会被分割为 [src, collector_script.py]
      - src
      - collector_script.py
 
# 采集插件参数列表
params:
  - timeout
```

## 工作原理

##### 插件包导入工具执行过程

1. 读取 origin_metric.json 文件，根据定义创建或更新原始指标。
2. 压缩 scripts 目录，并根据 plugin.yaml 文件中定义的 name 和 version 创建采集插件程序包版本。
3. 根据 plugin.yaml 文件中定义的 agentType 和 params 创建采集插件，采集插件的名称对应采集插件程序包名称。
4. 将采集插件关联上原始指标和程序包版本。
5. 读取 dashboard.json 文件，创建对应的仪表盘。

## 维护者

@easyopscyrilchen

## 许可证

[MIT](#许可证) © EasyOps
