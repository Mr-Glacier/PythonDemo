import pika
import json
import time
import logging
import traceback
from DistributedCrawlers.GeneralMethods import method_request_api
from DistributedCrawlers.minio_storage import MinioStorage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

RABBITMQ_HOST = "192.168.0.105"
RABBITMQ_PORT = 30779
RABBITMQ_USER = "admin"
RABBITMQ_PASS = "admin123"

# 任务类型- 品牌 \ 车型 \ 版本
TASK_QUEUES = ["Brand", "Model", "Version"]

# MinIO 配置
MINIO_CONF = {
    "endpoint": "192.168.0.105:31521",
    "access_key": "admin",
    "secret_key": "admin123",
    "bucket_name": "yiche",
    "secure": False
}


def connect():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        heartbeat=60,
        blocked_connection_timeout=300,
        connection_attempts=5,
        retry_delay=5,
        credentials=credentials
    )
    return pika.BlockingConnection(params)


def connect_minio():
    return MinioStorage(**MINIO_CONF)


def process_brand_info(msg, date_flag, minio_storage):
    """获取品牌下车型信息"""
    api_data = json.dumps({"masterId": str(msg.get("brand_id"))})
    result = method_request_api(
        "https://mapi.yiche.com/web_api/car_model_api/api/v1/brand/get_brand_list",
        api_data
    )
    if result != "Error":
        minio_storage.upload_bytes(result.encode("utf-8"), f"{date_flag}/Brand/{msg.get('brand_id')}.json")
        return True
    return False


def process_model_info(msg, date_flag, minio_storage):
    """获取车型下版本信息"""
    api_data = json.dumps({"serialId": str(msg.get("model_id"))})
    result = method_request_api(
        "https://mapi.yiche.com/web_api/car_model_api/api/v1/car/car_list_condition",
        api_data
    )
    if result != "Error":
        minio_storage.upload_bytes(result.encode("utf-8"), f"{date_flag}/model/{msg.get('model_id')}.json")
        return True
    return False


def process_version_info(msg, date_flag, minio_storage):
    """处理版本配置信息"""
    api_data = json.dumps({"modelId": str(msg.get("model_id"))})
    result = method_request_api(
        "https://mapi.yiche.com/web_api/car_model_api/api/v1/model/get_model_info",
        api_data
    )
    if result != "Error":
        minio_storage.upload_bytes(result.encode("utf-8"), f"{date_flag}/Model/{msg.get('model_id')}.json")
        return True
    return False


# 队列与处理函数的映射
TASK_HANDLERS = {
    "Brand": process_brand_info,
    "Series": process_model_info,
    "Version": process_version_info
}


def process_message(queue_name, ch, method, properties, body):
    start_time = time.time()
    try:
        msg = json.loads(body.decode("utf-8"))
        date_flag = msg.get("date_flag")
        logging.info(f"[消费者] 收到 {queue_name} 队列消息: {msg}")

        handler = TASK_HANDLERS.get(queue_name)
        if not handler:
            logging.error(f"[消费者] 未找到 {queue_name} 队列的处理函数")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        minio_storage = connect_minio()
        success = handler(msg, date_flag, minio_storage)

        if success:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.info(f"[消费者] {queue_name} 消息处理成功 (耗时 {time.time() - start_time:.3f}s)")
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            logging.warning(f"[消费者] {queue_name} 接口返回错误，重试中...")

    except json.JSONDecodeError:
        logging.error(f"[消费者] JSON 格式错误: {body}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        logging.error(f"[消费者] 处理消息失败: {e}")
        traceback.print_exc()
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start_consumer():
    connection = connect()
    channel = connection.channel()

    for q in TASK_QUEUES:
        channel.queue_declare(queue=q, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=q,
            on_message_callback=lambda ch, method, properties, body, qname=q: process_message(qname, ch, method,
                                                                                              properties, body)
        )

    logging.info(f"[消费者] 开始监听队列: {', '.join(TASK_QUEUES)}")
    channel.start_consuming()


if __name__ == "__main__":
    retry_delay = 5
    while True:
        try:
            start_consumer()
        except pika.exceptions.AMQPConnectionError:
            logging.warning(f"[消费者] 连接丢失，{retry_delay}s 后重连...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        except KeyboardInterrupt:
            logging.info("[消费者] 手动停止")
            break
