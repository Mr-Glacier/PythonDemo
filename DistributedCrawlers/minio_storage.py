from typing import Optional, List

from minio import Minio
from minio.error import S3Error
import io
import os
import mimetypes


class MinioStorage:
    def __init__(self, endpoint, access_key, secret_key, bucket_name, secure=False):
        """
        MinIO 文件存储工具类
        :param endpoint: MinIO 服务地址 (不带 http://)
        :param access_key: MinIO Access Key
        :param secret_key: MinIO Secret Key
        :param bucket_name: 存储桶名称
        :param secure: 是否使用 https
        """
        self.endpoint = endpoint
        self.secure = secure
        self.bucket_name = bucket_name

        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )

        # 确保桶存在
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def _make_url(self, object_name: str) -> str:
        """生成对象的访问 URL"""
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"

    def _get_content_type(self, file_path_or_name: str, default="application/octet-stream") -> str:
        """根据文件名自动推断 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(file_path_or_name)
        return mime_type or default

    def upload_bytes(self, file_bytes: bytes, object_name: str, content_type=None) -> Optional[str]:
        """上传二进制数据到 MinIO"""
        try:
            if not content_type:
                content_type = self._get_content_type(object_name)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(file_bytes),
                length=len(file_bytes),
                content_type=content_type
            )
            return self._make_url(object_name)
        except S3Error as e:
            print(f"[MinIO] 上传失败: {e}")
            return None

    def upload_file(self, file_path: str, object_name: str = None, content_type=None) -> Optional[str]:
        """上传本地文件到 MinIO"""
        if not os.path.exists(file_path):
            print(f"[MinIO] 文件不存在: {file_path}")
            return None

        if object_name is None:
            object_name = os.path.basename(file_path)

        if not content_type:
            content_type = self._get_content_type(file_path)

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            return self.upload_bytes(file_bytes, object_name, content_type)
        except Exception as e:
            print(f"[MinIO] 文件上传异常: {e}")
            return None

    def download_file(self, object_name: str, local_path: str) -> Optional[str]:
        """下载文件到本地"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.client.fget_object(self.bucket_name, object_name, local_path)
            return local_path
        except S3Error as e:
            print(f"[MinIO] 下载失败: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """删除 MinIO 文件"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            print(f"[MinIO] 删除成功: {object_name}")
            return True
        except S3Error as e:
            print(f"[MinIO] 删除失败: {e}")
            return False

    def list_files(self, prefix: str = "", recursive: bool = True) -> List[dict]:
        """
        列出 MinIO 中指定路径下的文件列表
        :param prefix: 路径前缀，例如 "folder/subfolder/"，必须以 / 结尾才能精确匹配路径
        :param recursive: 是否递归列出子目录
        :return: 文件信息列表 [{"name": 文件路径, "size": 大小(字节), "url": 访问链接}]
        """
        files = []
        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=recursive
            )
            for obj in objects:
                files.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "url": self._make_url(obj.object_name)
                })
        except S3Error as e:
            print(f"[MinIO] 获取文件列表失败: {e}")
        return files

    def get_file_bytes(self, object_name: str) -> Optional[bytes]:
        """获取 MinIO 中对象的二进制内容"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()  # 读取全部内容
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            print(f"[MinIO] 读取文件失败: {e}")
            return None
