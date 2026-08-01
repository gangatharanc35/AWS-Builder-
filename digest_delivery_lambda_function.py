
# File: backend/lambda_functions/digest_delivery/lambda_function.py

import json
import boto3
from datetime import datetime, timezone

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
digests_table = dynamodb.Table('SmartDigest_Digests')
ses_client = boto3.client('ses', region_name='us-east-1')
s3_client = boto3.client('s3')

S3_BUCKET = 'smartdigest-frontend'
SENDER_EMAIL = 'digest@yourdomain.com'


def lambda_handler(event, context):
    """
    Delivers the weekly digest via email (SES) and updates the S3 frontend.
    Triggered by the AI Summarizer after digest generation.
    """
    digest_id = event.get('digest_id')
    
    if not digest_id:
        return {'statusCode': 400, 'body': 'Missing digest_id'}
    
    # Fetch the digest
    digest = get_digest(digest_id)
    if not digest:
        return {'statusCode': 404, 'body': 'Digest not found'}
    
    # Generate HTML for email and frontend
    html_content = generate_html_digest(digest)
    
    # Upload to S3 for web dashboard
    upload_to_s3(html_content, digest_id)
    
    # Send email notification
    send_email_digest(html_content, digest)
    
    # Update digest status
    update_digest_status(digest_id, 'delivered')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Digest delivered successfully',
            'digest_id': digest_id
        })
    }


def get_digest(digest_id):
    """Retrieve digest from DynamoDB."""
    response = digests_table.get_item(Key={'digest_id': digest_id})
    return response.get('Item')


def generate_html_digest(digest):
    """Generate a beautiful HTML email/page from the digest data."""
    articles = json.loads(digest.get('articles', '[]'))
    
    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
    priority_label = {'high': 'Must Read', 'medium': 'Worth Knowing', 'low': 'Optional'}
    
    articles_html = ''
    current_priority = None
    
    for article in articles:
        priority = article.get('priority', 'medium')
        
        # Add section header when priority changes
        if priority != current_priority:
            current_priority = priority
            articles_html += f"""
            <div class="priority-section">
                <h2>{priority_emoji.get(priority, '⚪')} {priority_label.get(priority, 'Other')}</h2>
            </div>"""
        
        tags_html = ' '.join([f'<span class="tag">{tag}</span>' for tag in article.get('tags', [])])
        
        articles_html += f"""
        <div class="article-card priority-{priority}">
            <h3><a href="{article.get('link', '#')}">{article.get('title', 'Untitled')}</a></h3>
            <p class="summary">{article.get('summary', 'No summary available')}</p>
            <div class="meta">
                <span class="category">{article.get('category', 'General')}</span>
                {tags_html}
            </div>
        </div>"""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SmartDigest AI - Weekly Summary</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 700px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                   color: white; padding: 30px; border-radius: 12px; margin-bottom: 24px; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .stats {{ display: flex; gap: 16px; margin-top: 16px; }}
        .stat {{ background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 8px; }}
        .priority-section h2 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
        .article-card {{ background: white; padding: 20px; border-radius: 8px; 
                        margin-bottom: 12px; border-left: 4px solid #ddd; }}
        .article-card.priority-high {{ border-left-color: #e53e3e; }}
        .article-card.priority-medium {{ border-left-color: #ecc94b; }}
        .article-card.priority-low {{ border-left-color: #48bb78; }}
        .article-card h3 {{ margin: 0 0 8px 0; }}
        .article-card h3 a {{ color: #2d3748; text-decoration: none; }}
        .article-card h3 a:hover {{ color: #667eea; }}
        .summary {{ color: #4a5568; line-height: 1.6; }}
        .tag {{ background: #edf2f7; padding: 2px 8px; border-radius: 4px; 
                font-size: 12px; color: #4a5568; }}
        .category {{ font-weight: 600; color: #667eea; font-size: 12px; }}
        .meta {{ display: flex; gap: 8px; align-items: center; margin-top: 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 SmartDigest AI</h1>
        <p>Your Weekly Intelligence Brief — {datetime.now(timezone.utc).strftime('%B %d, %Y')}</p>
        <div class="stats">
            <div class="stat">📊 {digest.get('total_articles', 0)} Articles</div>
            <div class="stat">🔴 {digest.get('high_priority', 0)} Must Read</div>
            <div class="stat">🟡 {digest.get('medium_priority', 0)} Worth It</div>
        </div>
    </div>
    {articles_html}
    <div style="text-align: center; color: #a0aec0; padding: 20px;">
        <p>Generated by SmartDigest AI • Powered by Amazon Bedrock</p>
    </div>
</body>
</html>"""
    
    return html


def upload_to_s3(html_content, digest_id):
    """Upload the digest HTML to S3 for the web dashboard."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key='digests/latest.html',
            Body=html_content,
            ContentType='text/html'
        )
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=f'digests/{digest_id}.html',
            Body=html_content,
            ContentType='text/html'
        )
        print(f"Uploaded digest to S3: {digest_id}")
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")


def send_email_digest(html_content, digest):
    """Send the digest via Amazon SES."""
    try:
        import os
        subscribers = [os.environ.get('SUBSCRIBER_EMAIL', 'user@example.com')]
        
        for email in subscribers:
            ses_client.send_email(
                Source=SENDER_EMAIL,
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {
                        'Data': f"🧠 Your SmartDigest: {digest.get('high_priority', 0)} must-reads this week",
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': html_content,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
        print(f"Email sent to {len(subscribers)} subscribers")
    except Exception as e:
        print(f"Error sending email: {str(e)}")


def update_digest_status(digest_id, status):
    """Update digest delivery status."""
    digests_table.update_item(
        Key={'digest_id': digest_id},
        UpdateExpression='SET #status = :status, delivered_at = :ts',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':status': status,
            ':ts': datetime.now(timezone.utc).isoformat()
        }
    )