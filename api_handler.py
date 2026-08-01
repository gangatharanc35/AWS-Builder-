
import json
import boto3
import hashlib
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
feeds_table = dynamodb.Table('SmartDigest_Feeds')
digests_table = dynamodb.Table('SmartDigest_Digests')
articles_table = dynamodb.Table('SmartDigest_Articles')
lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')

    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS'
    }

    try:
        if http_method == 'OPTIONS':
            return {'statusCode': 200, 'headers': headers, 'body': ''}

        elif path == '/digest/latest' and http_method == 'GET':
            return get_latest_digest(headers)

        elif path == '/feeds' and http_method == 'GET':
            return get_feeds(headers)

        elif path == '/feeds' and http_method == 'POST':
            body = json.loads(event.get('body', '{}'))
            return add_feed(body, headers)

        elif '/feeds/' in path and http_method == 'DELETE':
            feed_id = event.get('pathParameters', {}).get('feed_id', '')
            return delete_feed(feed_id, headers)

        elif path == '/digest/generate' and http_method == 'POST':
            return trigger_generation(headers)

        else:
            return {'statusCode': 404, 'headers': headers, 'body': json.dumps({'error': 'Not found'})}

    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': str(e)})}


def get_latest_digest(headers):
    response = digests_table.scan()
    items = response.get('Items', [])

    if not items:
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'No digests yet', 'digest': None})}

    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    latest = items[0]

    if 'articles' in latest and isinstance(latest['articles'], str):
        latest['articles'] = json.loads(latest['articles'])

    return {'statusCode': 200, 'headers': headers, 'body': json.dumps(latest, default=str)}


def get_feeds(headers):
    response = feeds_table.scan()
    feeds = response.get('Items', [])
    return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'feeds': feeds, 'total': len(feeds)}, default=str)}


def add_feed(body, headers):
    feed_url = body.get('feed_url', '')
    category = body.get('category', 'general')
    name = body.get('name', feed_url)

    if not feed_url:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'feed_url is required'})}

    feed = {
        'feed_id': hashlib.md5(feed_url.encode()).hexdigest()[:12],
        'feed_url': feed_url,
        'name': name,
        'category': category,
        'status': 'active',
        'added_at': datetime.now(timezone.utc).isoformat()
    }

    feeds_table.put_item(Item=feed)
    return {'statusCode': 201, 'headers': headers, 'body': json.dumps({'message': 'Feed added successfully', 'feed': feed})}


def delete_feed(feed_id, headers):
    if not feed_id:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'feed_id is required'})}

    feeds_table.delete_item(Key={'feed_id': feed_id})
    return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': f'Feed {feed_id} deleted'})}


def trigger_generation(headers):
    try:
        lambda_client.invoke(
            FunctionName='SmartDigest_Feed_Collector',
            InvocationType='Event',
            Payload=json.dumps({'manual_trigger': True})
        )
        return {'statusCode': 200, 'headers': headers, 'body': json.dumps({'message': 'Digest generation triggered! Check your email in ~5 minutes.'})}
    except Exception as e:
        return {'statusCode': 500, 'headers': headers, 'body': json.dumps({'error': f'Failed to trigger: {str(e)}'})}

