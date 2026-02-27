#!/usr/bin/env python3
"""
S3 Handler
Manages screenshot uploads to AWS S3
Replaces local filesystem storage for scalability
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET', 'linkedin-bot-screenshots')

# Initialize S3 client
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    logger.info(f"S3 client initialized for bucket: {S3_BUCKET_NAME}")
except (ClientError, NoCredentialsError) as e:
    logger.warning(f"S3 client initialization failed: {e}. Screenshot uploads will fail.")
    s3_client = None


def upload_screenshot_to_s3(
    file_path: str,
    telegram_id: int,
    tag: str = "screenshot",
    delete_local: bool = True
) -> Optional[str]:
    """
    Upload screenshot to S3

    Args:
        file_path: Local path to screenshot file
        telegram_id: User's Telegram ID
        tag: Tag/category for the screenshot
        delete_local: Whether to delete local file after upload

    Returns:
        S3 URL of uploaded file, or None if upload failed
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot upload screenshot")
        return None

    if not os.path.exists(file_path):
        logger.error(f"Screenshot file not found: {file_path}")
        return None

    try:
        # Generate S3 key (path in bucket)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        s3_key = f"screenshots/{telegram_id}/{tag}/{timestamp}_{filename}"

        # Upload file
        s3_client.upload_file(
            file_path,
            S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': 'image/png',
                'Metadata': {
                    'telegram_id': str(telegram_id),
                    'tag': tag,
                    'uploaded_at': datetime.now().isoformat()
                }
            }
        )

        logger.info(f"Uploaded screenshot to S3: {s3_key}")

        # Delete local file if requested
        if delete_local:
            try:
                os.remove(file_path)
                logger.debug(f"Deleted local screenshot: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete local screenshot: {e}")

        # Generate presigned URL (valid for 7 days)
        url = generate_presigned_url(s3_key, expiration=7 * 24 * 3600)
        return url

    except ClientError as e:
        logger.error(f"S3 upload failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during S3 upload: {e}")
        return None


def generate_presigned_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate presigned URL for S3 object

    Args:
        s3_key: S3 object key
        expiration: URL expiration time in seconds (default 1 hour)

    Returns:
        Presigned URL, or None if generation failed
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot generate presigned URL")
        return None

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        return url

    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        return None


def delete_screenshot_from_s3(s3_key: str) -> bool:
    """
    Delete screenshot from S3

    Args:
        s3_key: S3 object key

    Returns:
        True if deleted successfully, False otherwise
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot delete screenshot")
        return False

    try:
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
        logger.info(f"Deleted screenshot from S3: {s3_key}")
        return True

    except ClientError as e:
        logger.error(f"Failed to delete S3 object: {e}")
        return False


def list_user_screenshots(telegram_id: int, tag: Optional[str] = None, max_keys: int = 100) -> list:
    """
    List screenshots for a user

    Args:
        telegram_id: User's Telegram ID
        tag: Optional tag filter
        max_keys: Maximum number of results

    Returns:
        List of S3 object metadata
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot list screenshots")
        return []

    try:
        prefix = f"screenshots/{telegram_id}/"
        if tag:
            prefix += f"{tag}/"

        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET_NAME,
            Prefix=prefix,
            MaxKeys=max_keys
        )

        if 'Contents' not in response:
            return []

        screenshots = []
        for obj in response['Contents']:
            screenshots.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'],
                'url': generate_presigned_url(obj['Key'], expiration=3600)
            })

        return screenshots

    except ClientError as e:
        logger.error(f"Failed to list S3 objects: {e}")
        return []


def setup_s3_lifecycle_policy():
    """
    Setup S3 lifecycle policy to auto-delete old screenshots (7 days)

    Note: This should be run once during deployment setup
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot setup lifecycle policy")
        return False

    try:
        lifecycle_policy = {
            'Rules': [
                {
                    'Id': 'DeleteOldScreenshots',
                    'Status': 'Enabled',
                    'Prefix': 'screenshots/',
                    'Expiration': {
                        'Days': 7
                    }
                }
            ]
        }

        s3_client.put_bucket_lifecycle_configuration(
            Bucket=S3_BUCKET_NAME,
            LifecycleConfiguration=lifecycle_policy
        )

        logger.info(f"S3 lifecycle policy configured for bucket {S3_BUCKET_NAME}")
        return True

    except ClientError as e:
        logger.error(f"Failed to setup S3 lifecycle policy: {e}")
        return False


def ensure_bucket_exists():
    """
    Ensure S3 bucket exists, create if it doesn't

    Note: This should be run once during deployment setup
    """
    if not s3_client:
        logger.error("S3 client not initialized, cannot ensure bucket exists")
        return False

    try:
        # Check if bucket exists
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        logger.info(f"S3 bucket {S3_BUCKET_NAME} exists")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            # Bucket doesn't exist, create it
            try:
                if AWS_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                else:
                    s3_client.create_bucket(
                        Bucket=S3_BUCKET_NAME,
                        CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
                    )

                logger.info(f"Created S3 bucket: {S3_BUCKET_NAME}")

                # Setup lifecycle policy
                setup_s3_lifecycle_policy()

                return True

            except ClientError as create_error:
                logger.error(f"Failed to create S3 bucket: {create_error}")
                return False
        else:
            logger.error(f"Error checking S3 bucket: {e}")
            return False


if __name__ == '__main__':
    # Test S3 configuration
    print(f"S3 Bucket: {S3_BUCKET_NAME}")
    print(f"AWS Region: {AWS_REGION}")
    print(f"S3 Client Initialized: {s3_client is not None}")

    if s3_client:
        ensure_bucket_exists()
