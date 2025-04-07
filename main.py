import streamlit as st
import paramiko
import time
import pandas as pd
import multiprocessing
import queue
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
import os
from monitor import monitor_server  # 从 monitor.py 导入监控函数

class ServerManager:
    def __init__(self):
        self.servers = {}
        self.processes = {}
        self.data_queue = multiprocessing.Queue()
        self.server_data = {}
        self.monitoring = False
        self.interval = 5
        self.last_data_time = None  # 记录最后一次收到数据的时间

    def load_config(self, config_file):
        try:
            with open(config_file, 'r', encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if not config or 'servers' not in config:
                st.error("配置文件格式错误，必须包含 'servers' 部分")
                return False
            self.servers = {server.get('id', server['hostname']): server for server in config['servers']}
            self.interval = config.get('interval', 5)
            return True
        except Exception as e:
            st.error(f"加载配置文件失败: {e}")
            return False

    def save_config(self, config_file, servers, interval=5):
        try:
            config = {'interval': interval, 'servers': servers}
            with open(config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
            return True
        except Exception as e:
            st.error(f"保存配置文件失败: {e}")
            return False

    def start_monitoring(self, selected_servers=None):
        if self.monitoring:
            return
        self.monitoring = True
        self.server_data = {server_id: [] for server_id in (selected_servers or self.servers.keys())}
        self.last_data_time = time.time()  # 初始化最后数据时间
        servers_to_monitor = {k: v for k, v in self.servers.items() if k in (selected_servers or self.servers.keys())}
        for server_id, server_config in servers_to_monitor.items():
            process = multiprocessing.Process(
                target=monitor_server,
                args=(server_config, self.interval, self.data_queue)
            )
            process.daemon = True
            process.start()
            self.processes[server_id] = process

    def stop_monitoring(self):
        if not self.monitoring:
            return
        for server_id, process in self.processes.items():
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        self.processes.clear()
        self.monitoring = False
        self.last_data_time = None

    def process_queue_data(self):
        while True:
            try:
                data = self.data_queue.get(timeout=0.1)
                server_id = data.get("server_id")
                if not server_id or server_id not in self.server_data:
                    continue
                if data.get("status") == "data":
                    self.server_data[server_id].append(data)
                    self.last_data_time = time.time()  # 更新最后数据时间
                    if len(self.server_data[server_id]) > 100:
                        self.server_data[server_id] = self.server_data[server_id][-100:]
                elif data.get("status") == "error":
                    st.error(f"服务器 {server_id} 错误: {data.get('message', '未知错误')}")
            except queue.Empty:
                break

def create_sample_config():
    config_path = os.path.join('config', 'servers.yaml')
    if not os.path.exists('config'):
        os.makedirs('config')
    if not os.path.exists(config_path):
        sample_config = {
            'interval': 5,
            'servers': [
                {'id': 'server1', 'hostname': 'server1.example.com', 'username': 'root', 'password': 'password', 'port': 22},
                {'id': 'server2', 'hostname': 'server2.example.com', 'username': 'admin', 'key_filename': '/path/to/key.pem', 'port': 2222}
            ]
        }
        with open(config_path, 'w') as f:
            yaml.dump(sample_config, f, default_flow_style=False)
        return config_path
    return config_path

def render_combined_metrics(server_manager, chart_placeholder):
    """渲染图表到指定占位符"""
    with chart_placeholder.container():
        if not any(server_manager.server_data.values()):
            if server_manager.last_data_time and (time.time() - server_manager.last_data_time) > 5:
                st.info("正在等待服务器数据...")
            return

        fig = make_subplots(rows=3, cols=1, subplot_titles=("CPU 使用率 (%)", "内存使用率 (%)", "磁盘使用率 (%)"), shared_xaxes=True, vertical_spacing=0.1)
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

        for idx, (server_id, data) in enumerate(server_manager.server_data.items()):
            if not data:
                continue
            df = pd.DataFrame(data)
            color = colors[idx % len(colors)]
            for row, metric, name in [(1, 'cpu', 'CPU'), (2, 'memory', '内存'), (3, 'disk', '磁盘')]:
                if metric in df.columns and not df[metric].isna().all():
                    fig.add_trace(
                        go.Scatter(x=df['timestamp'], y=df[metric], mode='lines+markers', name=f"{server_id} {name}",
                                   line=dict(color=color, width=2), fill='tozeroy', legendgroup=server_id),
                        row=row, col=1
                    )

        fig.update_layout(height=900, title_text="所有服务器资源使用率", showlegend=True,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        fig.update_yaxes(range=[0, 100], row=1, col=1)
        fig.update_yaxes(range=[0, 100], row=2, col=1)
        fig.update_yaxes(range=[0, 100], row=3, col=1)
        fig.update_xaxes(title_text="时间", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)

def show_latest_metrics(server_manager, metrics_placeholder):
    """显示最新数据到指定占位符"""
    with metrics_placeholder.container():
        st.subheader("最新数据")
        for server_id, data in server_manager.server_data.items():
            if not data:
                continue
            df = pd.DataFrame(data)
            latest = df.iloc[-1]
            hostname = server_manager.servers[server_id]['hostname']
            st.markdown(f"### {server_id} ({hostname})")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="当前CPU使用率", value=f"{latest['cpu']:.2f}%",
                          delta=f"{latest['cpu'] - df.iloc[-2]['cpu']:.2f}%" if len(df) > 1 else None)
            with col2:
                st.metric(label="当前内存使用率", value=f"{latest['memory']:.2f}%",
                          delta=f"{latest['memory'] - df.iloc[-2]['memory']:.2f}%" if len(df) > 1 else None)
                if 'memory_used' in latest and 'memory_total' in latest:
                    st.text(f"已用内存: {latest['memory_used']:.0f}MB / {latest['memory_total']:.0f}MB")
            with col3:
                if 'disk' in latest and not pd.isna(latest['disk']):
                    st.metric(label="当前磁盘使用率", value=f"{latest['disk']:.2f}%",
                              delta=f"{latest['disk'] - df.iloc[-2]['disk']:.2f}%" if len(df) > 1 and 'disk' in df.iloc[-2] else None)

def main():
    st.set_page_config(page_title="多服务器监控系统", page_icon="🖥️", layout="wide")
    st.title("多服务器资源监控仪表盘")

    if 'server_manager' not in st.session_state:
        st.session_state.server_manager = ServerManager()
    server_manager = st.session_state.server_manager

    config_file = os.path.join('config', 'servers.yaml')
    if not os.path.exists(config_file):
        config_file = create_sample_config()
        st.info(f"已创建示例配置文件: {config_file}")
    if not server_manager.servers:
        server_manager.load_config(config_file)

    with st.sidebar:
        st.header("监控控制")
        interval = st.slider("刷新间隔 (秒)", min_value=1, max_value=60, value=server_manager.interval, key="interval")
        if interval != server_manager.interval:
            server_manager.interval = interval
            server_manager.save_config(config_file, list(server_manager.servers.values()), interval)
        selected_servers = st.multiselect("选择要监控的服务器", options=list(server_manager.servers.keys()),
                                         default=list(server_manager.servers.keys()), key="selected_servers")
        col1, col2 = st.columns(2)
        with col1:
            start_button = st.button("开始监控", key="start_btn")
        with col2:
            stop_button = st.button("停止监控", key="stop_btn")

    if start_button and not server_manager.monitoring and selected_servers:
        server_manager.start_monitoring(selected_servers)
        st.success(f"开始监控 {len(selected_servers)} 个服务器")
    if stop_button and server_manager.monitoring:
        server_manager.stop_monitoring()
        st.warning("监控已停止")

    # 创建占位符
    chart_placeholder = st.empty()
    metrics_placeholder = st.empty()

    while True:
        server_manager.process_queue_data()
        if server_manager.monitoring:
            render_combined_metrics(server_manager, chart_placeholder)
            show_latest_metrics(server_manager, metrics_placeholder)
        elif not selected_servers:
            st.warning("未选择任何服务器，请在侧边栏选择要监控的服务器")
        else:
            st.info("监控未启动，请点击'开始监控'按钮")
        time.sleep(1)  # 每秒更新一次

if __name__ == "__main__":
    main()