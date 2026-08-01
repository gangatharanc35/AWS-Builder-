
# File: backend/lambda_functions/ai_summarizer/lambda_function.py

import json
import boto3
from datetime import datetime, timezone

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
articles_table = dynamodb.Table('SmartDigest_Articles')
digests_table = dynamodb.Table('SmartDigest_Digests')
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')

# Model ID for Amazon Nova Micro (free tier eligible)
MODEL_ID = 'amazon.nova-micro-v1:0'


def lambda_handler(event, context):
    """
    Uses Amazon Bedrock (Nova) to summarize articles and assign priority scores.
    Triggered asynchronously by the Feed Collector Lambda.
    """
    print("Starting AI summarization...")
    
    # Get all pending articles
    pending_articles = get_pending_articles()
    print(f"Found {len(pending_articles)} articles to process")
    
    summarized_articles = []
    
    for article in pending_articles:
        try:
            result = summarize_and_score(article)
            update_article(article['article_id'], result)
            summarized_articles.append({
                **article,
                **result
            })
            print(f"Summarized: {article['title'][:50]}...")
        except Exception as e:
            print(f"Error summarizing article {article['article_id']}: {str(e)}")
            continue
    
    # Generate the weekly digest
    if summarized_articles:
        digest_id = generate_digest(summarized_articles)
        trigger_delivery(digest_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Summarization complete',
            'articles_processed': len(summarized_articles)
        })
    }


def get_pending_articles():
    """Get all articles that haven't been summarized yet."""
    response = articles_table.scan(
        FilterExpression='#status = :pending',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':pending': 'pending_summary'}
    )
    return response.get('Items', [])


def summarize_and_score(article):
    """
    Use Amazon Bedrock Nova to:
    1. Generate a 2-3 sentence summary
    2. Assign a priority score (high/medium/low)
    3. Extract key topics/tags
    """
    prompt = f"""You are an intelligent content curator. Analyze the following article and provide:
1. A concise 2-3 sentence summary capturing the key takeaway
2. A priority level: "high" (must-read, actionable or breaking), "medium" (worth knowing), or "low" (optional/nice-to-know)
3. Up to 3 relevant topic tags

Article Title: {article['title']}
Article Content: {article.get('description', 'No description available')[:1500]}
Category: {article.get('category', 'general')}

Respond in this exact JSON format:
{{
    "summary": "Your 2-3 sentence summary here",
    "priority": "high|medium|low",
    "tags": ["tag1", "tag2", "tag3"],
    "reasoning": "Brief explanation of why this priority was assigned"
}}"""

    # Call Amazon Bedrock using the Converse API
    response = bedrock_runtime.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        inferenceConfig={
            "maxTokens": 500,
            "temperature": 0.3,
            "topP": 0.9
        }
    )
    
    result_text = response['output']['message']['content'][0]['text']
    
    # Parse the JSON response from the model
    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        # Fallback if model doesn't return perfect JSON
        result = {
            'summary': result_text[:200],
            'priority': 'medium',
            'tags': [article.get('category', 'general')],
            'reasoning': 'Auto-classified'
        }
    
    return result


def update_article(article_id, result):
    """Update the article in DynamoDB with summary and priority."""
    articles_table.update_item(
        Key={'article_id': article_id},
        UpdateExpression='SET #status = :done, summary = :summary, priority = :priority, tags = :tags, summarized_at = :ts',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={
            ':done': 'summarized',
            ':summary': result.get('summary', ''),
            ':priority': result.get('priority', 'medium'),
            ':tags': result.get('tags', []),
            ':ts': datetime.now(timezone.utc).isoformat()
        }
    )


def generate_digest(articles):
    """Create a weekly digest document from summarized articles."""
    digest_id = f"digest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    
    # Sort articles by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    sorted_articles = sorted(articles, key=lambda x: priority_order.get(x.get('priority', 'low'), 2))
    
    # Build digest content
    digest_content = {
        'digest_id': digest_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'total_articles': len(articles),
        'high_priority': len([a for a in articles if a.get('priority') == 'high']),
        'medium_priority': len([a for a in articles if a.get('priority') == 'medium']),
        'low_priority': len([a for a in articles if a.get('priority') == 'low']),
        'articles': json.dumps([{
            'title': a['title'],
            'summary': a.get('summary', ''),
            'priority': a.get('priority', 'medium'),
            'link': a.get('link', ''),
            'tags': a.get('tags', []),
            'category': a.get('category', 'general')
        } for a in sorted_articles]),
        'status': 'ready'
    }
    
    digests_table.put_item(Item=digest_content)
    print(f"Digest generated: {digest_id}")
    return digest_id


def trigger_delivery(digest_id):
    """Trigger the digest delivery Lambda."""
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName='SmartDigest_Delivery',
        InvocationType='Event',
        Payload=json.dumps({'digest_id': digest_id})
    )