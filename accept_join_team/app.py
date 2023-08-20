import boto3
from os import environ as os_environ
from jwt import decode
from json import loads as json_loads
from json import dumps as json_dumps


def lambda_handler(event, context):
    try:
        token = decode(event['headers']['Authorization'].replace('Bearer ', ''), algorithms=['RS256'],
                           options={"verify_signature": False})

        if 'cognito:groups' not in token or 'Admin' not in token['cognito:groups']:
            return {
                'statusCode': 401,
                'body': json_dumps({"message": 'Unauthorized', "err": "unauthorized"})
            }

        body = json_loads(event['body'])

        dynamodb = boto3.resource('dynamodb')

        teams_table = dynamodb.Table(os_environ['TEAMS_TABLE'])
        team_id = event['pathParameters']['team']

        # Get the team and check if user is in pending
        team = teams_table.get_item(
            Key={
                'team': team_id
            }
        )

        if team['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error getting team', "err": "dynamodbError"})
            }

        if 'Item' not in team:
            return {
                'statusCode': 404,
                'body': json_dumps({"message": 'Team not found', "err": "notFound"})
            }

        team = team['Item']

        if body['username'] not in team['pending']:
            return {
                'statusCode': 400,
                'body': json_dumps({"message": 'Player not in pending', "err": "notInPending"})
            }

        index = team['pending'].index(body['username'])

        response = teams_table.update_item(
            Key={
                'team': team_id
            },
            UpdateExpression=f'SET members = list_append(members, :player) REMOVE pending[{index}]',
            ExpressionAttributeValues={
                ':player': [body['username']]
            },
            ReturnValues="UPDATED_NEW"
        )

        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            return {
                'statusCode': 500,
                'body': json_dumps({"message": 'Error joining team', "err": "dynamodbError"})
            }

        return {
            'statusCode': 200,
            'body': json_dumps({"message": 'Team joined successfully'})
        }
    except Exception as error:
        return {
            "statusCode": 500,
            "body": json_dumps({"message": str(error), "err": "internalError"})
        }
