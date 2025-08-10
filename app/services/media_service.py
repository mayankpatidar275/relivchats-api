import os
import boto3
from botocore.exceptions import ClientError
import logging
from app.core.config import settings
import mimetypes # To infer content type

logger = logging.getLogger(__name__)

class MediaService:
    def __init__(self):
        # Initialize S3 client. AWS credentials should be handled securely (e.g., IAM roles, environment variables).
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.S3_BUCKET_NAME
            # Verify bucket exists/create (optional, can be done manually or via deployment script)
            # self._ensure_bucket_exists()
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None # Set to None if initialization fails
            # Raise an error to prevent the app from starting if S3 is critical
            # raise RuntimeError("S3 service initialization failed. Check AWS credentials and configuration.")

    # def _ensure_bucket_exists(self):
    #     try:
    #         self.s3_client.head_bucket(Bucket=self.bucket_name)
    #         logger.info(f"S3 bucket '{self.bucket_name}' exists.")
    #     except ClientError as e:
    #         error_code = int(e.response['Error']['Code'])
    #         if error_code == 404:
    #             logger.info(f"S3 bucket '{self.bucket_name}' not found. Attempting to create.")
    #             try:
    #                 # For regions other than 'us-east-1', LocationConstraint is required
    #                 if settings.AWS_REGION == 'us-east-1':
    #                     self.s3_client.create_bucket(Bucket=self.bucket_name)
    #                 else:
    #                     self.s3_client.create_bucket(Bucket=self.bucket_name, CreateBucketConfiguration={
    #                         'LocationConstraint': settings.AWS_REGION
    #                     })
    #                 logger.info(f"S3 bucket '{self.bucket_name}' created successfully.")
    #             except ClientError as ce:
    #                 logger.error(f"Failed to create S3 bucket '{self.bucket_name}': {ce}")
    #                 raise
    #         else:
    #             logger.error(f"Error checking S3 bucket '{self.bucket_name}': {e}")
    #             raise

    async def upload_media_file(self, file_content: bytes, file_name: str, chat_id: int, message_id: int) -> str:
        """
        Uploads a media file to S3 and returns its public URL.
        """
        if not self.s3_client:
            logger.error("S3 client not initialized. Cannot upload media.")
            raise ConnectionError("S3 service not available.")

        # Generate a unique key for the S3 object
        # Format: chats/{chat_id}/media/{message_id}-{file_name}
        # Using a UUID for message_id for more robust uniqueness, or actual message.id from DB
        # For now, using passed message_id (which could be temp index or actual DB ID)
        s3_key = f"chats/{chat_id}/media/{message_id}-{file_name}"

        # Infer content type based on file extension
        content_type, _ = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/octet-stream' # Default if type cannot be inferred

        try:
            # Upload the file
            # Boto3's put_object is sync, but FastAPI allows await if the underlying I/O is async
            # For simplicity here, we'll keep it sync, but for heavy loads, use ThreadPoolExecutor or async boto3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                ACL='public-read' # Make the object publicly readable (adjust as per security needs)
            )
            # Construct the public URL
            # This URL format might vary based on your S3 region and bucket configuration
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            logger.info(f"Media file '{file_name}' uploaded to S3: {s3_url}")
            return s3_url
        except ClientError as e:
            logger.error(f"S3 upload failed for {file_name} (key: {s3_key}): {e}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during S3 upload for {file_name}: {e}")
            raise

media_service = MediaService()