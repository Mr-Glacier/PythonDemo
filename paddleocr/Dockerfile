# 使用指定的基础镜像
FROM paddlepaddle/paddle:3.0.0-gpu-cuda12.6-cudnn9.5-trt10.5

# 设置工作目录
WORKDIR /app

RUN mkdir -p /root/ocr/

# 复制当前目录下的所有文件到容器的 /app 目录
COPY . .

# 设置清华源为 pip 镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装所需的 Python 包
RUN pip install  paddleocr \
    && pip install fastapi \
    && pip install requests \
    && pip install  uvicorn \
    && pip install  python-multipart

# 暴露端口
EXPOSE 3000

# 运行 Python 脚本
CMD ["python", "ocr_interface.py"]
