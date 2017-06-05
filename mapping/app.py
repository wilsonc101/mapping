import botocore
import boto3
import jinja2
import sys
import json
import os

from chalice import Chalice, Response

app = Chalice(app_name='mapping')

S3_CLIENT = boto3.client('s3', region_name="eu-west-1")
DDB_CLIENT = boto3.client('dynamodb')

POST_URL = os.environ['posturl']
GET_URL = os.environ['geturl']
IMAGE_URL = os.environ['imageurl']

S3_BUCKET = os.environ['posturl']
S3_EMAIL_BUCKET = os.environ['emailbucket']
 
DDB_TABLE = os.environ['ddbtable']


def render_s3_template(client, bucket, template_name, content=None):
    # If no conent is supplied, set to empty dict
    if content is None:
        content = dict()

    file_object = client.get_object(Bucket=bucket, Key=template_name)
    file_content = file_object['Body'].read().decode('utf-8')
    rendered_html = jinja2.Environment().from_string(file_content).render(content)

    return(rendered_html)


@app.route('/')
def index():
    post_url = POST_URL
    get_url = GET_URL
    image_url = IMAGE_URL

    template_data = {"postURL" : post_url,
                     "getURL" : get_url,
                     "imagesURL": image_url}

    try:
        html_content = render_s3_template(S3_CLIENT, S3_BUCKET, "mapbox.j2", template_data)

        return Response(body=html_content,
                        status_code=200,
                        headers={'Content-Type': 'text/html',
                                 'Access-Control-Allow-Origin': '*',
                                 'Set-Cookie': 'token1=data1',
                                 'Set-cookie': 'token2=data2'})
    except:
        S3_CLIENT.put_object(Body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]), Bucket=S3_BUCKET, Key="index_error.txt")
        return Response(body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]),
                        status_code=500,
                        headers={'Content-Type': 'text/html'})


@app.route('/getdata')
def getdata():
    try:
        map_data = dict()

        response = DDB_CLIENT.scan(TableName=DDB_TABLE)
        for item in response['Items']:
            id = item['id']['S'] 
            type = item['type']['S'] 
            action = item['action']['S']
            data = json.loads(item['data']['S'])


            map_data[id] = {'type': type,
                            'action': action, 
                            'coordinates': data['geometry']['coordinates']}

            if type == "circle":
                map_data[id]['radius'] = data['radius']


        return Response(body=map_data,
                        status_code=200,
                        headers={'Content-Type': 'application/json',
                                 'Access-Control-Allow-Origin': '*'})

    except:
        S3_CLIENT.put_object(Body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]), Bucket=S3_BUCKET, Key="getdata_error.txt")
        return Response(body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]),
                        status_code=500,
                        headers={'Content-Type': 'text/plain'})


@app.route('/postdata', methods=['POST'])
def postdata():
    try:
        json_data = {}
        json_data['input'] = app.current_request.json_body

        action = json_data['input']['action']

        db_item = dict()
        db_item['id'] = {'S': json_data['input']['id']}
        db_item['type'] = {'S': json_data['input']['type']}
        db_item['data'] = {'S': json_data['input']['data']}
        db_item['action'] = {'S': action}

        
        if action == "create" or action == "edit":
            DDB_CLIENT.put_item(TableName=DDB_TABLE, 
                                Item=db_item)

        elif action == "delete":
            DDB_CLIENT.delete_item(TableName=DDB_TABLE, 
                                   Key={'id': {'S': db_item['id']['S']}})

        return Response(body="success",
                        status_code=200,
                        headers={'Content-Type': 'text/plain'})

    except:
        S3_CLIENT.put_object(Body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]), Bucket=S3_BUCKET, Key="postdata_error.txt")
        return Response(body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]),
                        status_code=500,
                        headers={'Content-Type': 'text/plain'})


@app.route('/emaildata', methods=['POST'])
def emaildata():
    try:
        json_data = {}
        json_data['input'] = app.current_request.json_body

        db_item = dict()
        
        for message in json_data['input']:
            coordinates = [json_data['input'][message]['lat'], json_data['input'][message]['long']]
            geo_data = {"geometry":{"coordinates": coordinates}}

            db_item['id'] = {'S': json_data['input'][message]['id']}
            db_item['type'] = {'S': 'marker'}
            db_item['action'] = {'S': json_data['input'][message]['action']}
            db_item['data'] = {'S': json.dumps(geo_data)}

            DDB_CLIENT.put_item(TableName=DDB_TABLE, Item=db_item)

            S3_CLIENT.delete_object(Bucket=S3_EMAIL_BUCKET, Key=message)

        return Response(body="success",
                        status_code=200,
                        headers={'Content-Type': 'text/plain'})


    except:
        S3_CLIENT.put_object(Body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]), Bucket=S3_BUCKET, Key="emaildata_error.txt")
        return Response(body=str(sys.exc_info()[0]) + " -- " + str(sys.exc_info()[1]),
                        status_code=500,
                        headers={'Content-Type': 'text/plain'})
