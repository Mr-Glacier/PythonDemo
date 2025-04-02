# .CSV文件处理 DEMO

> 系统共两个页面：

<img src="../images/dataProcessing-login.png">
<img src="../images/dataProcessing-home.png">

### 部署方式：Docker部署
> 1. 制作镜像
```shell
docker build -t dataprocess:latest .
```
> 2. 启动容器
```shell
docker run -itd --name dataprocess -p 9997:8080 -v /data/zkzd/youyan-dataProcess:/csv  -e QDRANT_URL=172.17.0.3  -e TEXT2VEC_URL=http://172.17.0.1:13100/text2vec  --restart always dataprocess:latest
```