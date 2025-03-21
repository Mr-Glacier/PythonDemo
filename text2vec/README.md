# text2vec 向量化

> Thanks for [text2vec](https://github.com/shibing624/text2vec)

## 用于构建解析向量服务

### 1. 构建镜像

```shell
docker build -t text2vec:latest .
```

### 2. 下载所需模型

[huggingface.co --> text2vec-base-chinese](https://huggingface.co/shibing624/text2vec-base-chinese)  
[modelscope.cn --> text2vec-base-chinese](https://modelscope.cn/models/thomas/text2vec-base-chinese/files)

### 3. 运行容器
> cpu 使用
```shell
docker run -d --name text2vec -p 13100:3100 -v /path/to/model:/workspace/model -e MODEL_NAME=text2vec-base-chinese --restart always text2vec:latest
```
> gpu 使用
```shell
docker run -d --name text2vec -p 13100:3100 --gpus all -v /path/to/model:/workspace/model -e MODEL_NAME=text2vec-base-chinese --restart always text2vec:latest
```

### 4. 其他模型的使用
[huggingface.co  --> other models](https://huggingface.co/models?sort=trending&search=text2vec)