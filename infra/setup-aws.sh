#!/bin/bash
# ============================================================
# AWS Infrastructure Setup for Open Supply Chain Control Tower
# Run this script once to create all required AWS resources.
# Prerequisites: AWS CLI configured with admin permissions
# ============================================================

set -e

REGION="us-east-1"
ECR_REPO="open-supply-chain-control-tower"
APP_RUNNER_SERVICE="open-supply-chain-control-tower"
GITHUB_ORG="Resilient-Supply-Chain"
GITHUB_REPO="open-supply-chain-control-tower"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "=== AWS Account: $ACCOUNT_ID ==="
echo "=== Region: $REGION ==="

# ----------------------------------------------------------
# Step 1: Create ECR Repository
# ----------------------------------------------------------
echo ">>> Creating ECR repository..."
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $REGION \
  --image-scanning-configuration scanOnPush=true \
  2>/dev/null || echo "ECR repo already exists"

ECR_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO"
echo "ECR URI: $ECR_URI"

# ----------------------------------------------------------
# Step 2: Create IAM OIDC Provider for GitHub Actions
# ----------------------------------------------------------
echo ">>> Setting up GitHub OIDC provider..."
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 \
  2>/dev/null || echo "OIDC provider already exists"

# ----------------------------------------------------------
# Step 3: Create IAM Role for GitHub Actions
# ----------------------------------------------------------
echo ">>> Creating IAM role for GitHub Actions..."

TRUST_POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:${GITHUB_ORG}/${GITHUB_REPO}:*"
        }
      }
    }
  ]
}
EOF
)

ROLE_NAME="github-actions-deploy-role"

aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document "$TRUST_POLICY" \
  2>/dev/null || echo "Role already exists"

# Attach permissions
POLICY=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "apprunner:StartDeployment",
        "apprunner:DescribeService"
      ],
      "Resource": "*"
    }
  ]
}
EOF
)

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name deploy-policy \
  --policy-document "$POLICY"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo "Role ARN: $ROLE_ARN"

# ----------------------------------------------------------
# Step 4: Create App Runner Service
# ----------------------------------------------------------
echo ">>> Creating App Runner service..."
echo "NOTE: You need to first push a Docker image to ECR before creating App Runner."
echo ""
echo "Run these commands first to push an initial image:"
echo "  cd Asset_UI_Team/web"
echo "  aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI"
echo "  docker build -t $ECR_URI:latest ."
echo "  docker push $ECR_URI:latest"
echo ""
echo "Then create App Runner with:"
echo "  aws apprunner create-service \\"
echo "    --service-name $APP_RUNNER_SERVICE \\"
echo "    --source-configuration '{\"AuthenticationConfiguration\":{\"AccessRoleArn\":\"arn:aws:iam::${ACCOUNT_ID}:role/AppRunnerECRAccessRole\"},\"AutoDeploymentsEnabled\":false,\"ImageRepository\":{\"ImageIdentifier\":\"${ECR_URI}:latest\",\"ImageRepositoryType\":\"ECR\",\"ImageConfiguration\":{\"Port\":\"3000\"}}}' \\"
echo "    --region $REGION"

# ----------------------------------------------------------
# Summary
# ----------------------------------------------------------
echo ""
echo "============================================================"
echo "SETUP COMPLETE. Add these GitHub Secrets to your repo:"
echo "============================================================"
echo ""
echo "  AWS_ROLE_ARN          = $ROLE_ARN"
echo "  APP_RUNNER_SERVICE_ARN = (from App Runner after creation)"
echo ""
echo "Go to: https://github.com/${GITHUB_ORG}/${GITHUB_REPO}/settings/secrets/actions"
echo "============================================================"
