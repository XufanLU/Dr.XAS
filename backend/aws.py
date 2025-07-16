import io
import os
import uuid

import boto3
from boto3.s3.transfer import S3UploadFailedError
from botocore.exceptions import ClientError

from dotenv import load_dotenv
import logging
load_dotenv()


#https://github.com/awsdocs/aws-doc-sdk-examples/blob/main/python/example_code/s3/s3_basics/hello.py
#https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
# https://aws.amazon.com/sdk-for-python/
# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-examples.html



#TODO 
# add cif_files. FEFF_path . viz to the bucket

def create_s3_client():
    """
    Create an S3 client using boto3.
    """

    print("Creating S3 client...")
    try:
        s3_client = boto3.client('s3',region_name='eu-north-1')
        print("S3 client created successfully.")
        return s3_client
    except Exception as e:
        print(f"Error creating S3 client: {e}")
        return None 
  



def create_bucket( bucket_name, keep_bucket=True):

    s3_client=create_s3_client()

    try:
        bucket=s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' exists")
    except ClientError as e:
            try:
                print("\nCreating new bucket:", bucket_name)
                bucket = s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={
                        "LocationConstraint": 'eu-north-1'},
                )
                print(f"Bucket {bucket_name} created successfully.")

            except ClientError as e:
                print(
                    f"Couldn't create a bucket. Here's why: "
                    f"{e.response['Error']['Message']}"
                )
                raise


def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    s3_client=create_s3_client()


    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)
    try:
    # Upload the file
        with open(file_name, "rb") as f:
         response = s3_client.upload_fileobj(f,bucket, object_name)

        print(response)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def download_file(bucket, object_name, file_name=None):
    """Download a file from an S3 bucket

    :param bucket: Bucket to download from
    :param object_name: S3 object name
    :param file_name: File to download to. If not specified then object_name is used
    :return: True if file was downloaded, else False
    """
    s3_client=create_s3_client()

    if file_name is None:
        file_name = object_name

    try:
        s3_client.download_file(bucket, object_name, file_name)
        print(f"Downloaded {object_name} from bucket {bucket} to {file_name}")
    except ClientError as e:
        logging.error(e)
        return False
    return True

def delete_file(bucket, object_name):
    """Delete a file from an S3 bucket

    :param bucket: Bucket to delete from
    :param object_name: S3 object name
    :return: True if file was deleted, else False
    """
    s3_client=create_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        print(f"Deleted {object_name} from bucket {bucket}")
    except ClientError as e:
        logging.error(e)
        return False
    return True


    
if __name__ == "__main__":

    create_bucket("test-dr-xas")
    upload_file("/Users/xufanlu/Projects/MT/Dr.XAFS/physics/cif_files/Ni_foil.cif", "test-dr-xas", "cif_file")
    #download_file("test-dr-xas", "cif_file", "Ni_foil.cif")
    #delete_file("test-dr-xas", "cif_file")
