
# File: scripts/setup_dynamodb.py
"""
Seeds the DynamoDB Feeds table with default RSS feeds for SmartDigest AI.
Run this after deployment to populate initial feed sources.
"""

import boto3
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
feeds_table = dynamodb.Table('SmartDigest_Feeds')

# Default feeds to get started
DEFAULT_FEEDS = [
    {
        'feed_url': 'https://aws.amazon.com/blogs/aws/feed/',
        'name': 'AWS Blog',
        'category': 'tech',
        'description': 'Official AWS Blog - new services and features'
    },
    {
        'feed_url': 'https://news.ycombinator.com/rss',
        'name': 'Hacker News',
        'category': 'tech',
        'description': 'Top stories from Hacker News'
    },
    {
        'feed_url': 'https://dev.to/feed',
        'name': 'DEV Community',
        'category': 'dev',
        'description': 'Developer articles and tutorials'
    },
    {
        'feed_url': 'https://feeds.feedburner.com/TechCrunch/',
        'name': 'TechCrunch',
        'category': 'business',
        'description': 'Startup and technology news'
    },
    {
        'feed_url': 'https://www.reddit.com/r/aws/.rss',
        'name': 'Reddit r/aws',
        'category': 'tech',
        'description': 'AWS community discussions'
    },
    {
        'feed_url': 'https://blog.python.org/feeds/posts/default?alt=rss',
        'name': 'Python Blog',
        'category': 'dev',
        'description': 'Official Python language blog'
    }
]


def seed_feeds():
    """Insert default feeds into DynamoDB."""
    print("🌱 Seeding default feeds...")
    
    for feed_data in DEFAULT_FEEDS:
        item = {
            'feed_id': str(uuid.uuid4())[:8],
            'feed_url': feed_data['feed_url'],
            'name': feed_data['name'],
            'category': feed_data['category'],
            'description': feed_data['description'],
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        feeds_table.put_item(Item=item)
        print(f"  ✅ Added: {feed_data['name']} ({feed_data['category']})")
    
    print(f"\n🎉 Done! {len(DEFAULT_FEEDS)} feeds seeded successfully.")
    print("Your first digest will be generated on the next scheduled run (Monday 6 AM UTC)")
    print("Or trigger manually via the dashboard or AWS Console.")


if __name__ == '__main__':
    seed_feeds()