#!/usr/bin/env python3
import sys

import yaml
import re
import threading
import json
import tarfile
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from mysqlInit.DeployDB import deploy_db
from Upgrade import start_Upgrade_process, daemonize, acquire_lock, load_compose, load_docker, SERVICE_NAME
from Util import docker_compose_up, check_service_running, run_with_retry, is_autodeploy_running, run_cmd
from datetime import datetime
import logging
import os


# 创建 logs 目录（可选）
LOGS_DIR = Path("./deployLogs")
LOGS_DIR.mkdir(exist_ok=True)

# 生成带时间戳的日志文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"pilotos_deploy_{timestamp}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建 formatter
# formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] "
    "[PID:%(process)d TID:%(thread)d %(threadName)s] "
    "%(name)s: %(message)s"
)

# 控制台处理器（StreamHandler）
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 文件处理器（FileHandler）
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

def init_db():
    logger.info("start init_db")
    run_with_retry(deploy_db, "init_db")

def start_services():
    logger.info("=== 启动 ===")
    if check_service_running():
        logger.info("司南镜像服务已经启动，无需再次启动")
    else:
        logger.info("正在启动司南服务")
        docker_compose_up()
        flag = check_service_running()
        if not flag:
            raise RuntimeError("服务未正常运行")
        logger.info("司南镜像服务启动成功")
    #如果升级服务没有启动，启动升级服务
    if not is_autodeploy_running():
        # 启动升级服务
        logger.info("开始启动升级服务，其余输出见日志文件")
        daemonize()
        start_Upgrade_process()
    else:
        logger.info(f"[PID={os.getpid()}]升级服务已经启动，无需再次启动")

# def run_core_config():
#     run_cmd(["ulimit", "-c", "unlimited"])
#     run_cmd(["sudo", "sysctl", "-w", "kernel.core_uses_pid=1"])
#     run_cmd(["sudo", "sysctl", "-w", "kernel.core_pattern=./core-%e-%p-%t"])

def enable_system_core_dump():
    # 1. limits (core size)
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/security/limits.d/99-core.conf <<'EOF'
* soft core unlimited
* hard core unlimited
EOF
"""
    ])

    # 2. systemd directory (FIX)
    run_cmd(["sudo", "mkdir", "-p", "/etc/systemd/system.conf.d"])

    # 3. systemd core limit
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/systemd/system.conf.d/99-core.conf <<'EOF'
[Manager]
DefaultLimitCORE=infinity
EOF
"""
    ])

    run_cmd(["sudo", "systemctl", "daemon-reexec"])

    # 4. sysctl directory
    run_cmd(["sudo", "mkdir", "-p", "/etc/sysctl.d"])

    # 5. sysctl core pattern
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/sysctl.d/99-core.conf <<'EOF'
kernel.core_uses_pid=1
kernel.core_pattern=/var/coredump/core-%e-%p-%t
EOF
"""
    ])

    run_cmd(["sudo", "sysctl", "--system"])

    # 6. core directory
    run_cmd(["sudo", "mkdir", "-p", "/var/coredump"])
    run_cmd(["sudo", "chmod", "1777", "/var/coredump"])

    # 7. optional: disable systemd-coredump
    run_cmd(["sudo", "systemctl", "disable", "systemd-coredump.socket"], check=False)
    run_cmd(["sudo", "systemctl", "stop", "systemd-coredump.socket"], check=False)



def init_docker():
    data = load_compose()
    image = data["services"][SERVICE_NAME]["image"] + '.iso'
    load_docker(image)

def print_usage():
    print("示例用法:")
    print("  python AutoDeploy.py init    # 初始化数据库")
    print("  python AutoDeploy.py start   # 启动镜像和升级服务")    


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "initDB":
        init_db()
    elif cmd == "loadImage":
        init_docker()
    elif cmd == "start":
        enable_system_core_dump()
        start_services()
    else:
        print(f"未知命令: {cmd}")
        print_usage()
        sys.exit(1)
