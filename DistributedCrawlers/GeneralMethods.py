import json
import random
import traceback
from typing import Union

import requests
import hashlib
import time
import urllib.parse
import pika


def method_request_api(main_url: str, param: str) -> str:
    """
    易车 api 请求发送 方法
    Args:
        main_url (str): 基础 URL
        param (str): 要传递的参数字符串

    Returns:
        str: 返回响应内容，出错时返回 "Error"
    """
    result_json = "Error"
    # 1. 生成时间戳
    timestamp = str(int(time.time() * 1000))
    # 2. 固定盐值（o）
    o = "19DDD1FBDFF065D3A4DA777D2D7A81EC"
    # 3. 构造签名原文 s
    cid = "508"
    s = f"cid={cid}&param={param}{o}{timestamp}"
    # 4. 计算 MD5 签名
    md5_str = hashlib.md5(s.encode('utf-8')).hexdigest().lower()
    # 5. 设置 Cookie（可根据需要动态生成）
    cookie = ""

    try:
        # 6. URL 编码 param
        param_url = urllib.parse.quote(param, encoding='utf-8')
        # 7. 构造完整 URL
        full_url = f"{main_url}?cid={cid}&param={param_url}"
        print(full_url)
        # 8. 设置请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "X-City-Id": "201",
            "X-Ip-Address": "101.27.236.186",
            "X-Platform": "pc",
            "X-Sign": md5_str,
            "X-User-Guid": "849ec451-0627-4ee7-8139-7d0a7233d10a",
            "Cookie": cookie,
            "Content-Type": "application/json;charset=UTF-8",
            "Cid": cid,
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "X-Timestamp": timestamp,
        }

        # 9. 发送 GET 请求
        response = requests.get(
            full_url,
            headers=headers
            # verify=False  # 忽略 SSL 验证（与 ignoreHttpErrors 对应）
        )
        # 10. 获取响应体
        result_json = response.text

        # 11. 增加随机延时
        time.sleep(random.uniform(0.25, 1.5))
    except Exception as e:
        print(f"Error occurred: {e}")
        # 可以选择打印 traceback
        # import traceback; traceback.print_exc()

    return result_json


def method_mq_publish(
        connection_params: pika.ConnectionParameters,
        exchange_name: str,
        routing_key: str,
        body: Union[str, dict, list]
) -> bool:
    """
    RabbitMQ 发布方法（支持直接传 dict 或 str）

    Args:
        :param body: 要发布的消息内容（str / dict / list）
        :param routing_key: 路由键（通常为队列名）
        :param exchange_name: 交换机名称（为空字符串表示使用默认交换机）
        :param connection_params: 连接参数

    Returns:
        bool: 发布成功返回 True，失败返回 False
    """
    connection = None
    try:
        # 处理消息内容
        if isinstance(body, (dict, list)):
            # dict/list 转 JSON 字符串
            body_str = json.dumps(body, ensure_ascii=False)
        elif isinstance(body, str):
            body_str = body
        else:
            raise TypeError(f"body 类型不支持: {type(body)}，请传 str / dict / list")

        # 转成 bytes
        body_bytes = body_str.encode("utf-8")

        # 建立连接
        connection = pika.BlockingConnection(connection_params)
        channel = connection.channel()

        # 确保队列存在
        channel.queue_declare(queue=routing_key, durable=True)

        # 发布消息
        channel.basic_publish(
            exchange=exchange_name or "",
            routing_key=routing_key,
            body=body_bytes,
            properties=pika.BasicProperties(delivery_mode=2)  # 消息持久化
        )

        print(f"[Scheduler] 发布成功 -> {routing_key}: {body_str}")
        return True

    except Exception as e:
        print(f"[Scheduler] 发布失败: {e}")
        traceback.print_exc()
        return False

    finally:
        if connection and not connection.is_closed:
            connection.close()


def method_mq_clear(connection_params: pika.ConnectionParameters, queue_name):
    """
    清空指定队列的所有消息
    """
    connection = pika.BlockingConnection(connection_params)
    channel = connection.channel()

    # 清空队列
    channel.queue_purge(queue=queue_name)
    print(f"[调度中心] 队列 '{queue_name}' 已清空")

    connection.close()
