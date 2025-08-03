FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

COPY . /app

# 如果没有 requirements.txt，直接安装 Flask
RUN pip install flask

# 声明应用运行在容器中的端口
EXPOSE 8000

CMD ["python", "main.py"]