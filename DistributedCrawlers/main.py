import json
import math
import time

import pika

from GeneralMethods import method_request_api, method_mq_publish, method_mq_clear, check_queue_empty
from minio_storage import MinioStorage

# MQ 相关链接参数
params = pika.ConnectionParameters(host='192.168.0.105', port=30779,
                                   credentials=pika.PlainCredentials('admin', 'admin123'))
storage = MinioStorage(
    endpoint="192.168.0.105:31521",
    access_key="admin",
    secret_key="admin123",
    bucket_name="yiche",
    secure=False
)


def method_brand(date_flag):
    """
    获取品牌列表
    """
    result_json = method_request_api("https://mhapi.yiche.com/hcar/h_car/pc/api/v1/brand/get_master_list",
                                     "{\"configMaster\":1}")
    data_dict = json.loads(result_json).get("data")
    for brand_dict in data_dict:
        brand_id = brand_dict.get("id")
        brand_name = brand_dict.get("name")
        # 发布全部品牌的 厂商车型获取任务
        if method_mq_publish(params, "", "Brand",
                             {"brand_id": brand_id, "brand_name": brand_name, "date_flag": date_flag}) is True:
            print("发布成功")
        else:
            print("发布失败")
    return True


def method_factory_modules(date_flag):
    """
    获取厂商车型列表
    https://mapi.yiche.com/web_api/car_model_api/api/v1/car/car_list_condition?cid=508&param=%7B%22serialId%22%3A%228014%22%7D
    """
    files = storage.list_files(prefix=f"{date_flag}/Brand/", recursive=False)
    for file in files:
        file_name = file["name"]
        file_content = storage.get_file_bytes(file_name)
        data_list = json.loads(file_content.decode()).get("data")
        for data_dict in data_list:
            factory_id = data_dict.get("id")
            factory_name = data_dict.get("name")
            model_list = data_dict.get("serialList")
            for model_dict in model_list:
                model_id = model_dict.get("id")
                model_name = model_dict.get("name")
                print(f"发布厂商车型获取任务:{factory_name} {model_name}")
                if method_mq_publish(params, "", "Model",
                                     {"model_id": model_id, "model_name": model_name, "date_flag": date_flag}) is True:
                    print("发布成功")
                else:
                    print("发布失败")


def method_version(date_flag):
    """
    发送获取版本配置任务
    """
    # 定义任务类别映射
    car_status_map = {
        "notSaleCarList": "未售版本",
        "waitSaleCarList": "待售版本",
        "onSaleCarList": "在售版本",
        "stopSaleCarList": "停售版本"
    }

    files = storage.list_files(prefix=f"{date_flag}/Model/", recursive=False)
    versions_batches = []

    for file in files:
        file_content = storage.get_file_bytes(file["name"])

        if not file_content:
            print(f"警告：文件 {file['name']} 内容为空")
            continue  # 跳过空文件

        try:
            decoded_content = file_content.decode('utf-8')
            json_data = json.loads(decoded_content)

            if not isinstance(json_data, dict) or 'data' not in json_data:
                print(f"警告：文件 {file['name']} 解析结果不符合预期: {json_data}")
                continue

            data_version = json_data.get("data", {})

            if not isinstance(data_version, dict):
                print(f"警告：文件 {file['name']} 的 data 字段不是字典: {type(data_version)}")
                continue

            # 遍历四种状态
            for key, status_name in car_status_map.items():
                car_list_by_status = data_version.get(key, [])

                if not isinstance(car_list_by_status, list):
                    print(f"警告：文件 {file['name']} 的 {key} 不是列表: {type(car_list_by_status)}")
                    continue

                if not car_list_by_status:
                    continue

                # 处理每个版本
                for version_item in car_list_by_status:
                    year = version_item.get("year")

                    if not isinstance(version_item, dict) or not isinstance(year, int):
                        print(f"警告：文件 {file['name']} 的版本项格式错误: {version_item}")
                        continue

                    power_list = version_item.get("powerList", [])

                    if not isinstance(power_list, list):
                        print(f"警告：文件 {file['name']} 的 powerList 不是列表: {type(power_list)}")
                        continue

                    for power_item in power_list:
                        power = power_item.get("powerName")

                        if not isinstance(power_item, dict) or not isinstance(power, str):
                            print(f"警告：文件 {file['name']} 的 powerItem 格式错误: {power_item}")
                            continue

                        print(f"发布{status_name}任务: {year} {power}")

                        car_list = power_item.get("carList", [])

                        if not isinstance(car_list, list):
                            print(f"警告：文件 {file['name']} 的 carList 不是列表: {type(car_list)}")
                            continue

                        for car_item in car_list:
                            if not isinstance(car_item, dict):
                                print(f"警告：文件 {file['name']} 的 carItem 格式错误: {car_item}")
                                continue

                            versions_batches.append({
                                "car_id": car_item.get("id"),
                                "car_name": car_item.get("name")
                            })

        except Exception as e:
            print(f"解析文件 {file['name']} 时出错: {e}")
            continue

    # 本次一共多少版本
    total = len(versions_batches)
    print(f"本次一共版本数量: {total}")

    batch_size = 5
    total_batches = math.ceil(total / batch_size)

    for i in range(total_batches):
        batch = versions_batches[i * batch_size:(i + 1) * batch_size]

        # version_ids 格式为 id1,id2,id3,id4,id5
        version_ids = ",".join([str(item.get("car_id")) for item in batch])

        # 推送到 MQ
        if method_mq_publish(params, "", "Version", {"version_ids": version_ids, "date_flag": date_flag}) is True:
            print(f"已推送第 {i + 1} 组: {batch}")
        else:
            print("发布失败")


if __name__ == '__main__':
    # 日期标识
    date_flag = "20210801"
    # 1. 推送每个品牌的任务
    method_brand(date_flag)

    # 2. 等待 Brand 队列清空
    while True:
        if check_queue_empty(params, "Brand"):
            print("Brand 队列已处理完毕，开始推送 Model 任务")
            break
        else:
            print("Brand 队列尚未清空，继续等待 10 秒...")
            time.sleep(30)

    # 推送每个车型的任务
    # method_factory_modules(date_flag)
    while True:
        if check_queue_empty(params, "Model"):
            print("Model 队列已处理完毕，开始推送 Version 队列")
            break
        else:
            print("Model 队列尚未清空，继续等待 30 秒...")
            time.sleep(30)
    method_version(date_flag)
    while True:
        if check_queue_empty(params, "Version"):
            print("Model 队列已处理完毕，开始推送 Version 队列")
            break
        else:
            print("Model 队列尚未清空，继续等待 30 秒...")
            time.sleep(30)
