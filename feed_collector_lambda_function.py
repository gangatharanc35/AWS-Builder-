
import json
import boto3
import feedparser
import hashlib
from datetime import datetime, timezone

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
feeds_table = dynamodb.Table('SmartDigest_Feeds')
articles_table = dynamodb.Table('SmartDigest_Articles')


def lambda_handler(event, context):
    """
    Collects articles from configured RSS feeds and stores them in DynamoDB.
    Triggered by EventBridge on a weekly schedule (every Monday at 6 AM UTC).
    """
    print("Starting feed collection...")

    # Get all configured feeds from DynamoDB
    feeds = get_configured_feeds()
    total_new_articles = 0

    for feed in feeds:
        try:
            new_count = process_feed(feed)
            total_new_articles += new_count
            print(f"Processed feed: {feed['feed_url']} - {new_count} new articles")
        except Exception as e:
            print(f"Error processing feed {feed['feed_url']}: {str(e)}")
            continue

    # Trigger the AI summarizer Lambda
    trigger_summarizer()

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Feed collection complete',
            'feeds_processed': len(feeds),
            'new_articles': total_new_articles,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    }


def get_configured_feeds():
    """Retrieve all active RSS feed configurations from DynamoDB."""
    response = feeds_table.scan(
        FilterExpression='#status = :active',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':active': 'active'}
    )
    return response.get('Items', [])


def process_feed(feed):
    """Parse an RSS feed and store new articles."""
    parsed = feedparser.parse(feed['feed_url'])
    new_articles = 0

    for entry in parsed.entries[:20]:  # Limit to 20 most recent per feed
        article_id = generate_article_id(entry.get('link', entry.get('title', '')))

        # Check if article already exists
        if article_exists(article_id):
            continue

        # Extract article data
        article = {
            'article_id': article_id,
            'feed_id': feed['feed_id'],
            'title': entry.get('title', 'Untitled'),
            'link': entry.get('link', ''),
            'description': clean_html(entry.get('description', entry.get('summary', ''))),
            'published': entry.get('published', datetime.now(timezone.utc).isoformat()),
            'category': feed.get('category', 'general'),
            'status': 'pending_summary',
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'priority': 'unscored'
        }

        # Store in DynamoDB
        articles_table.put_item(Item=article)
        new_articles += 1

    return new_articles


def generate_article_id(url_or_title):
    """Generate a unique ID for an article based on its URL or title."""
    return hashlib.sha256(url_or_title.encode()).hexdigest()[:16]


def article_exists(article_id):
    """Check if an article already exists in the database."""
    try:
        response = articles_table.get_item(Key={'article_id': article_id})
        return 'Item' in response
    except Exception:
        return False


def clean_html(text):
    """Remove HTML tags from text for clean storage."""
    import re
    clean = re.sub(r'<[^>]+>', '', text)
    return clean[:2000]  # Limit description length


def trigger_summarizer():
    """Invoke the AI Summarizer Lambda function."""
    lambda_client = boto3.client('lambda')
    try:
        lambda_client.invoke(
            FunctionName='SmartDigest_AI_Summarizer',
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({'action': 'summarize_pending'})
        )
        print("AI Summarizer triggered successfully")
    except Exception as e:
        print(f"Error triggering summarizer: {str(e)}")