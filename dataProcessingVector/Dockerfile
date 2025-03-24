# 使用官方的 Python 基础镜像
FROM python:3.10-bullseye

# 设置工作目录
WORKDIR /app

# 设置环境变量以避免安装 Python 包时的互动提示
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE \
    TZ=Asia/Shanghai

# 安装系统依赖（按需安装）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

# 复制 requirements.txt 并安装 Python 依赖
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用程序代码到容器
COPY . .

# 创建主要存储目录
RUN mkdir -p /csv/workspace/ /csv/temp/

# 暴露应用程序运行的端口
EXPOSE 15000

# 定义启动命令
CMD ["python", "dataProcessingVector.py"]