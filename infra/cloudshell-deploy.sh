#!/bin/bash
# ============================================================
# Run this in AWS CloudShell after uploading the zip to S3
# Usage: bash cloudshell-deploy.sh s3://YOUR-BUCKET/open-supply-chain-control-tower-deploy.zip
# ============================================================

set -e

if [ -z "$1" ]; then
  echo "Usage: bash cloudshell-deploy.sh s3://YOUR-BUCKET/open-supply-chain-control-tower-deploy.zip"
  exit 1
fi

S3_PATH=$1
REGION="us-east-1"
ECR_PUBLIC_REPO="open-supply-chain-control-tower"

echo "=== Deploying to ECR Public ==="

# Step 1: Download zip from S3
echo ">>> Downloading from $S3_PATH..."
mkdir -p /tmp/deploy && cd /tmp/deploy
aws s3 cp $S3_PATH ./deploy.zip
unzip -o deploy.zip

# Step 2: Create ECR Public repo (skip if exists)
echo ">>> Creating ECR Public repository..."
aws ecr-public create-repository \
  --repository-name $ECR_PUBLIC_REPO \
  --region us-east-1 \
  --catalog-data '{
    "description": "Open Supply Chain Control Tower - UI Dashboard for U.S. supply-chain resilience",
    "operatingSystems": ["Linux"],
    "architectures": ["x86-64"]
  }' \
  2>/dev/null || echo "ECR Public repo already exists, continuing..."

# Get the public registry URI
ECR_PUBLIC_URI=$(aws ecr-public describe-repositories \
  --repository-names $ECR_PUBLIC_REPO \
  --region us-east-1 \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR Public URI: $ECR_PUBLIC_URI"

# Step 3: Build Docker image
echo ">>> Building Docker image..."
docker build -t $ECR_PUBLIC_REPO:latest .

# Step 4: Login to ECR Public and push
echo ">>> Pushing to ECR Public..."
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
docker tag $ECR_PUBLIC_REPO:latest $ECR_PUBLIC_URI:latest
docker push $ECR_PUBLIC_URI:latest

echo ""
echo "============================================================"
echo "Docker image pushed to: $ECR_PUBLIC_URI:latest"
echo ""
echo "Anyone can pull it with:"
echo "  docker pull $ECR_PUBLIC_URI:latest"
echo "  docker run -p 3000:3000 $ECR_PUBLIC_URI:latest"
echo ""
echo "To deploy on App Runner:"
echo "  1. Go to: https://console.aws.amazon.com/apprunner"
echo "  2. Create service -> Container registry -> Amazon ECR Public"
echo "  3. Image URI: $ECR_PUBLIC_URI:latest"
echo "  4. Port: 3000"
echo "============================================================"
