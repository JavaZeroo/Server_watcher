# 多服务器监控系统

本项目是一个基于 Streamlit 的多服务器资源监控仪表盘，支持实时监控多个服务器的 CPU、内存、磁盘等资源使用情况。

## 功能
- 实时监控多个服务器的资源使用情况
- 支持动态注册监控指标
- 图表展示资源使用率
- 支持通过配置文件管理服务器信息

## 安装

首先，安装所需的 Python 包：

```bash
pip install streamlit paramiko pandas plotly pyyaml
```

## 使用

1. 克隆项目到本地：

```bash
git clone https://github.com/JavaZeroo/Server_watcher
cd Server_watcher
```

2. 创建或编辑配置文件 `config/servers.yaml`，添加需要监控的服务器信息。

3. 运行主程序：

```bash
streamlit run main.py
```

4. 打开浏览器访问 `http://localhost:8501`，即可查看监控仪表盘。

## 配置文件格式

配置文件位于 `config/servers.yaml`，示例如下：

```yaml
interval: 5
servers:
- id: server1
  hostname: server1.example.com
  username: root
  password: password
  port: 22
  metrics:
    - type: CpuMetric
    - type: MemoryMetric
- id: server2
  hostname: server2.example.com
  username: admin
  key_filename: /path/to/key.pem
  port: 2222
  metrics:
    - type: DiskMetric
```

- `interval`：刷新间隔，单位为秒。
- `servers`：服务器列表，每个服务器包含以下字段：
  - `id`：服务器唯一标识符。
  - `hostname`：服务器主机名或 IP 地址。
  - `username`：登录用户名。
  - `password`：登录密码（可选）。
  - `key_filename`：SSH 密钥文件路径（可选）。
  - `port`：SSH 端口，默认 22。
  - `metrics`：监控指标列表，支持 `CpuMetric`、`MemoryMetric` 和 `DiskMetric`。

## 贡献

欢迎提交问题和功能请求，或通过 Pull Request 贡献代码。

## 许可证

本项目采用 [GNU General Public License v3.0](LICENSE)。