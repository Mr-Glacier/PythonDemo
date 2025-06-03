import os
import platform
import subprocess
import ipaddress
import concurrent.futures
import time


def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP套接字连接到公共DNS服务器
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        try:
            # 如果上述方法失败，尝试获取主机名对应的IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "127.0.0.1"


def get_network_range(ip):
    """根据本机IP获取局域网IP范围"""
    try:
        interface = ipaddress.IPv4Interface(f"{ip}/24")
        network = interface.network
        return list(network.hosts())
    except Exception as e:
        print(f"无法确定网络范围: {e}")
        return []


def ping_ip(ip):
    """ping指定的IP地址，返回是否在线"""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    command = ["ping", param, "1", "-w", "1", str(ip)]

    try:
        # 使用subprocess运行ping命令，丢弃输出
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(command, stdout=devnull, stderr=devnull)
        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False


def scan_network():
    """扫描局域网内所有活跃的IP地址"""
    print("正在获取本机IP地址...")
    local_ip = get_local_ip()
    print(f"本机IP地址: {local_ip}")

    print("正在计算局域网IP范围...")
    ip_list = get_network_range(local_ip)
    if not ip_list:
        print("无法确定局域网IP范围，请手动输入起始和结束IP。")
        start_ip = input("起始IP(如192.168.1.1): ")
        end_ip = input("结束IP(如192.168.1.254): ")

        try:
            start = ipaddress.IPv4Address(start_ip)
            end = ipaddress.IPv4Address(end_ip)
            ip_list = [ipaddress.IPv4Address(ip) for ip in range(int(start), int(end) + 1)]
        except Exception as e:
            print(f"无效的IP范围: {e}")
            return []

    print(f"正在扫描局域网IP(共{len(ip_list)}个)...")

    active_ips = []
    start_time = time.time()

    # 使用线程池并发ping
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        future_to_ip = {executor.submit(ping_ip, ip): ip for ip in ip_list}

        for future in concurrent.futures.as_completed(future_to_ip):
            ip = future_to_ip[future]
            try:
                is_active = future.result()
                if is_active:
                    active_ips.append(str(ip))
                    print(f"发现活跃IP: {ip}")
            except Exception as e:
                print(f"检查IP {ip} 时出错: {e}")

    end_time = time.time()
    print(f"\n扫描完成! 耗时: {end_time - start_time:.2f}秒")
    print(f"发现 {len(active_ips)} 个活跃IP地址:")

    # 按IP地址排序输出
    active_ips_sorted = sorted(active_ips, key=lambda x: tuple(map(int, x.split('.'))))
    for ip in active_ips_sorted:
        print(ip)

    return active_ips_sorted


if __name__ == "__main__":
    import socket  # 延迟导入以避免Windows上的问题

    print("局域网IP扫描工具")
    print("=" * 30)

    active_ips = scan_network()

    # 可选: 将结果保存到文件
    # save = input("\n是否将结果保存到文件?(y/n): ").lower()
    # if save == 'y':
    #     filename = input("输入文件名(默认: active_ips.txt): ") or "active_ips.txt"
    #     with open(filename, 'w') as f:
    #         f.write("\n".join(active_ips))
    #     print(f"结果已保存到 {filename}")

    input("\n按Enter键退出...")