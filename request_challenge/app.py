import boto3
import json
import os
import jwt
from urllib import parse
import time

def lambda_handler(event, context):
    try:
        token = jwt.decode(event['headers']['Authorization'].replace('Bearer ', ''), algorithms=['RS256'],
                       options={"verify_signature": False})

        if 'cognito:groups' in token and 'Admin' in token['cognito:groups']:
            return {
                'statusCode': 401,
                'body': json.dumps({"message": 'You must be a player to request a challenge', "err": "unauthorized"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        dynamodb = boto3.resource('dynamodb')

        user_table = dynamodb.Table(os.environ['USER_TABLE'])
        user = user_table.get_item(Key={'username': token['cognito:username']})

        if user['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 404,
                'body': json.dumps({"message": 'Error connecting to database', "err": "dynamodbError"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        if 'Item' not in user:
            return {
                'statusCode': 404,
                'body': json.dumps({"message": 'User not found', "err": "notFound"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        user = user['Item']

        # Get challenge
        challenge_id = parse.unquote(event['pathParameters']['challenge'])
        challenge_table = dynamodb.Table(os.environ['CHALLENGES_TABLE'])
        challenge = challenge_table.get_item(Key={'challenge': challenge_id})

        if challenge['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 404,
                'body': json.dumps({"message": 'Error connecting to database', "err": "dynamodbError"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        if 'Item' not in challenge:
            return {
                'statusCode': 404,
                'body': json.dumps({"message": 'Challenge not found', "err": "notFound"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        challenge = challenge['Item']

        if not challenge:
            return {
                'statusCode': 404,
                'body': json.dumps({"message": 'Challenge not found', "err": "notFound"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        if user['challenges_done'].count(challenge['challenge']) + user['challenges_pending'].count(
                challenge['challenge']) >= challenge['max_count']:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": 'You have already completed this challenge the maximum number of times',
                                    "err": "challengeLimit"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        t = int(time.time())
        print(f'Time : {t}')
        if challenge['start'] > t or challenge['end'] < t:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": 'Challenge not active', "err": "challengeNotActive"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        # Add the challenge to the user's pending challenges
        response = user_table.update_item(
            Key={
                'username': user['username']
            },
            UpdateExpression='SET challenges_pending = list_append(challenges_pending, :challenge)',
            ExpressionAttributeValues={
                ':challenge': [challenge['challenge']],
            }
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json.dumps({"message": 'Error requesting challenge', "err": "dynamodbError"}),
                'headers': {
                    'Access-Control-Allow-Origin': '*'
                }
            }

        return {
            'statusCode': 200,
            'body': json.dumps({"message": 'Challenge requested'}),
            'headers': {
                'Access-Control-Allow-Origin': '*'
            }
        }

    except Exception as error:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": str(error), "err": "internalError"}),
            'headers': {
                'Access-Control-Allow-Origin': '*'
            }
        }
