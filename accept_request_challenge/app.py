import boto3
from jwt import decode
from json import dumps as json_dumps
from json import loads as json_loads
from time import time
from os import environ as os_environ


def lambda_handler(event, context):
    try:
        token = decode(event['headers']['Authorization'].replace('Bearer ', ''), algorithms=['RS256'],
                       options={"verify_signature": False})

        if 'cognito:groups' not in token or 'Admin' not in token['cognito:groups']:
            return {
                'statusCode': 401,
                'body': json_dumps({"message": 'Unauthorized', "err": "unauthorized"})
            }

        if 'body' not in event:
            return {
                'statusCode': 400,
                'body': json_dumps({"message": 'Missing body', "err": "emptyBody"})
            }

        body = json_loads(event['body'])

        dynamodb = boto3.resource('dynamodb')

        user_table = dynamodb.Table(os_environ['USER_TABLE'])
        username = event['pathParameters']['username']
        # Get the team and check if user is in pending
        user = user_table.get_item(
            Key={
                'username': username
            }
        )

        if user['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error getting user', "err": "dynamodbError"})
            }

        if 'Item' not in user:
            return {
                'statusCode': 404,
                'body': json_dumps({"message": 'User not found', "err": "notFound"})
            }

        user = user['Item']

        if body['challenge'] not in user['challenges_pending']:
            return {
                'statusCode': 400,
                'body': json_dumps({"message": 'Player didn\'t request this challenge', "err": "notInPending"})
            }

        index = user['challenges_pending'].index(body['challenge'])

        if 'challenges_times' not in user:
            user['challenges_times'] = {}

        if body['challenge'] not in user['challenges_times']:
            user['challenges_times'][body['challenge']] = int(time())

        response = user_table.update_item(
            Key={
                'username': username
            },
            UpdateExpression=f'SET challenges_done = list_append(challenges_done, :challenge), challenges_times = :times REMOVE challenges_pending[{index}]',
            ExpressionAttributeValues={
                ':challenge': [body['challenge']],
                ':times': user['challenges_times']
            },
            ReturnValues="UPDATED_NEW"
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error accepting challenge', "err": "dynamodbError"})
            }

        return {
            'statusCode': 200,
            'body': json_dumps({"message": 'Challenge accepted'})
        }
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json_dumps({"message": str(error), "err": "internalError"})
        }
