from minio import Minio
from minio.error import S3Error

class MinioService:
    def __init__(self, host="localhost:9000", user="minioadmin", password="minioadmin"):
        self.client = Minio(host, access_key=user, secret_key=password, secure=False)
        self.bucket = "rag-documents"
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            print(f"Error creating bucket: {e}")

    def upload(self, object_name: str, file_path: str) -> str:
        try:
            self.client.fput_object(self.bucket, object_name, file_path)
            return f"s3://{self.bucket}/{object_name}"
        except S3Error as e:
            raise Exception(f"Upload failed: {e}")

    def download(self, object_name: str, file_path: str):
        try:
            self.client.fget_object(self.bucket, object_name, file_path)
        except S3Error as e:
            raise Exception(f"Download failed: {e}")
