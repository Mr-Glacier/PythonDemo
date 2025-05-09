# OCR 识别服务

> Thanks for [paddleocr](https://paddlepaddle.github.io/PaddleOCR/latest/quick_start.html)

### 1. 构建镜像

```shell
docker build -f Dockerfile -t paddleocr:latest .
```

### 2. 运行容器
> cpu 使用
```shell
docker run -itd --restart always --name ocr --gpus '"device=3"' -p 8300:8300 -v /${PATH}/.paddleocr:/root/.paddleocr paddleocr:latest
```

