FROM python:3.10-bullseye

# 设置工作目录
RUN mkdir -p /workspace
WORKDIR /zkzd

# 设置环境变量以避免安装Python包时的互动提示
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

# 安装系统依赖（如果有需要的话）
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 复制当前目录的内容到容器中的 /app 目录
COPY . /workspace

# 创建模型加载目录
RUN mkdir -p /workspace/models/

# 设置时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

# 安装Python依赖
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 暴露应用程序将运行的端口
EXPOSE 3100

# 定义启动命令
CMD ["python", "text2vec_server.py"]