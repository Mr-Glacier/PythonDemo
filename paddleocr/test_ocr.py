import requests


# 定义请求函数
def request_structure(api_url, file_path):
    """
    请求 /structure 接口
    :param api_url: API 的 URL (例如 http://127.0.0.1:8000/structure)
    :param file_path: 本地图片文件路径
    :return: 响应内容
    """
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(api_url, files=files)
    return response.json()


def request_ocr(api_url, file_path):
    """
    请求 /ocr 接口
    :param api_url: API 的 URL (例如 http://127.0.0.1:8000/ocr)
    :param file_path: 本地图片文件路径
    :return: 响应内容
    """
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(api_url, files=files)
    return response.json()


# 使用示例
if __name__ == "__main__":
    # 替换为实际的 API 地址
    structure_api_url = "http://223.0.12.108:8300/structure"
    ocr_api_url = "http://223.0.12.108:8300/ocr"

    # 替换为实际的图片文件路径
    image_file_path = "/images/dataProcessing-home.png"

    # 请求 /structure 接口
    structure_response = request_structure(structure_api_url, image_file_path)
    print("Structure Response:", structure_response)

    # 请求 /ocr 接口
    ocr_response = request_ocr(ocr_api_url, image_file_path)
    print("OCR Response:", ocr_response)
