
#!/bin/bash
# File: scripts/deploy.sh
# SmartDigest AI - One-Click Deployment Script

set -e

echo "🧠 SmartDigest AI - Deployment Script"
echo "======================================"

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo "❌ AWS SAM CLI not found. Install: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
    exit 1
fi

echo "✅ Prerequisites met"

# Get user email
read -p "Enter your email for digest delivery: " USER_EMAIL

# Navigate to infrastructure
cd "$(dirname "$0")/../backend/infrastructure"

# Build SAM application
echo ""
echo "📦 Building SAM application..."
sam build

# Deploy
echo ""
echo "🚀 Deploying to AWS..."
sam deploy \
    --stack-name SmartDigest-AI \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides SubscriberEmail=$USER_EMAIL \
    --resolve-s3 \
    --no-confirm-changeset

# Get outputs
echo ""
echo "📋 Getting deployment outputs..."
FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name SmartDigest-AI --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" --output text)
API_URL=$(aws cloudformation describe-stacks --stack-name SmartDigest-AI --query "Stacks[0].Outputs[?OutputKey=='ApiURL'].OutputValue" --output text)

# Update frontend with API URL
echo ""
echo "🔧 Configuring frontend..."
cd ../../frontend
sed -i "s|const API_BASE_URL = '';|const API_BASE_URL = '${API_URL}';|g" app.js

# Get S3 bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name SmartDigest-AI --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" --output text | sed 's|http://||' | sed 's|.s3-website.*||')

# Upload frontend to S3
echo "📤 Uploading frontend to S3..."
aws s3 sync . s3://${BUCKET_NAME}/ --content-type "text/html" --exclude "*.css" --exclude "*.js"
aws s3 sync . s3://${BUCKET_NAME}/ --content-type "text/css" --exclude "*.html" --exclude "*.js" --include "*.css"
aws s3 sync . s3://${BUCKET_NAME}/ --content-type "application/javascript" --exclude "*.html" --exclude "*.css" --include "*.js"

# Seed default feeds
echo ""
echo "🌱 Seeding default feeds..."
cd ../scripts
python3 setup_dynamodb.py

# Verify SES email
echo ""
echo "📧 Verifying email with SES..."
aws ses verify-email-identity --email-address $USER_EMAIL
echo "⚠️  Check your email ($USER_EMAIL) and click the verification link from AWS SES"

# Done!
echo ""
echo "======================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "======================================"
echo ""
echo "🌐 Frontend URL: $FRONTEND_URL"
echo "🔗 API URL: $API_URL"
echo ""
echo "📅 Your digest will auto-generate every Monday at 6 AM UTC"
echo "💡 Or click 'Generate Now' on the dashboard to test immediately"
echo ""
echo "Happy reading! 🎉"