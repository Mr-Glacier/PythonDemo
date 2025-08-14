# 使用官方 Python 3.11 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app

# 安装系统依赖（必要的编译工具、Tesseract OCR 等）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        tesseract-ocr \
        libgl1-mesa-glx \
        && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 创建上传临时目录
RUN mkdir -p /app/uploads

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 启动 FastAPI 服务
CMD ["python", "test_DeepDoc.py"]
