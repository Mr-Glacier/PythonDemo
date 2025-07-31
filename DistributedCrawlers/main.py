import json

import pika

from DistributedCrawlers.GeneralMethods import method_request_api, method_mq_publish, method_mq_clear
from DistributedCrawlers.minio_storage import MinioStorage

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


if __name__ == '__main__':
    # 日期标识
    date_flag = "20210801"
    # 推送每个品牌的任务
    method_brand(date_flag)
    # 推送每个车型的任务
    # method_factory_modules(date_flag)

    # method_mq_clear(params, "Brand")
    # method_brand()
    # print(method_brand())
    # print(method_factory_modules())
