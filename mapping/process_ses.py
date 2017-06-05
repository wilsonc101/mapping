import boto3
import os
import urllib
import json
import re


S3_CLIENT = boto3.client('s3', region_name="eu-west-1")

S3_EMAIL_BUCKET = os.environ['emailbucket']
POST_URL = os.environ['posturl']
EMAIL_DOMAIN = os.environ['emailDomain']


def lambda_handler(event, context):
    non_decimal = re.compile(r'[^((\-)?\d.)]+')

    mail = event['Records'][0]['ses']['mail']
    mail_message_id = mail['messageId']
    mail_subject = mail['commonHeaders']['subject']
    mail_from = mail['source']

    mail_data = dict()
    mail_data[mail_message_id] = dict()
    mail_data[mail_message_id]['id'] = mail_subject
    
    for item in mail['headers']:
        if item['name'] == "Content-Type":
            mail_content_boundary = item['value'].split("boundary=")[1].replace('"', "").replace("'", "")
 
    email_file = S3_CLIENT.get_object(Bucket=S3_EMAIL_BUCKET, Key=mail_message_id)
    email_file_content = email_file['Body'].read().decode('utf-8')

    content_list = email_file_content.split("--" + str(mail_content_boundary))
    for content_item in content_list:
        if "text/plain" in content_item:
            content = content_item.split("\n")
            for text_item in content:
                if "Action" in text_item:
                    mail_data[mail_message_id]['action'] = str(text_item).split(":")[1].rstrip()
                elif "Lat" in text_item:
                    mail_data[mail_message_id]['lat'] = non_decimal.sub('', text_item)
                elif "Long" in text_item:
                    mail_data[mail_message_id]['long'] = non_decimal.sub('', text_item)

    req = urllib.request.Request(POST_URL)
    req.add_header('Content-Type', 'application/json')
    encoded_data = json.dumps(mail_data).encode("utf-8")
    response = urllib.request.urlopen(req, encoded_data)

