import boto3
from os import environ as os_environ
from jwt import decode
from json import dumps as json_dumps


def lambda_handler(event, context):
    try:
        token = decode(event['headers']['Authorization'].replace('Bearer ', ''), algorithms=['RS256'],
                       options={"verify_signature": False})

        dynamodb = boto3.resource('dynamodb')

        user_table = dynamodb.Table(os_environ['USER_TABLE'])
        user = user_table.get_item(Key={'username': token['cognito:username']})
        if user['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error retrieving user', "err": "dynamodbError"})
            }

        if 'Item' not in user:
            return {
                "statusCode": 404,
                "body": json_dumps({"message": "User not found", "err": "notFound"})
            }
        user = user['Item']


        challenge_table = dynamodb.Table(os_environ['CHALLENGES_TABLE'])
        challenges = challenge_table.scan()
        if challenges['ResponseMetadata']['HTTPStatusCode'] != 200 or 'Items' not in challenges:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error retrieving challenges', "err": "dynamodbError"})
            }
        challenges = challenges['Items']

        user['points'] = 0
        for challenge_id in user['challenges_done']:
            # Filter to get the correct challenge
            t = list(filter(lambda x: x['challenge'] == challenge_id, challenges))
            if len(t) == 0:
                continue
            challenge = t[0]
            user['points'] += challenge['points']

        user['is_admin'] = 'cognito:groups' in token and 'Admin' in token['cognito:groups']
        return {
            "statusCode": 200,
            "body": json_dumps(user, default=int)
        }
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json_dumps({"message": str(error), "err": "internalError"})
        }
