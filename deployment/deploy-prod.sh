#!/bin/bash

# Production deployment script for insulin-recommendation microservice
# This script deploys to production environment as a public service

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    echo -e "${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error "Environment file .env not found!"
    echo "Please create a .env file with the following variables:"
    echo "  PROJECT_ID=patientview-9uxml"
    echo "  REGION=asia-south1"
    echo "  SERVICE_NAME=insulin-recommendation"
    exit 1
fi

# Load environment variables from .env file
print_status "Loading environment variables from .env file..."
source .env

# Set defaults
PROJECT_ID=${PROJECT_ID:-"patientview-9uxml"}
REGION=${REGION:-"asia-south1"}
SERVICE_NAME=${SERVICE_NAME:-"insulin-recommendation"}

if [ -z "$PROJECT_ID" ]; then
    print_error "PROJECT_ID is not set in .env file"
    exit 1
fi

# Display configuration
print_status "Production Deployment Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Authentication: Public (no authentication required)"
echo "  Memory: 512Mi"
echo "  CPU: 1"
echo "  Min Instances: 0 (scales to zero)"
echo "  Max Instances: 10"

# Confirm deployment
echo
print_warning "⚠️  You are about to deploy to PRODUCTION environment!"
read -p "Are you sure you want to proceed with PRODUCTION deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Production deployment cancelled"
    exit 0
fi

# Check if gcloud is installed and authenticated
print_status "Checking gcloud configuration..."
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set the project
print_status "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
print_status "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com --quiet
gcloud services enable run.googleapis.com --quiet
gcloud services enable containerregistry.googleapis.com --quiet

print_success "All required APIs enabled!"

# Build and deploy using Cloud Build
print_status "Building and deploying PRODUCTION service using Cloud Build..."
gcloud builds submit \
    --config deployment/cloudbuild.yaml \
    --substitutions=_REGION="$REGION" \
    --project $PROJECT_ID

if [ $? -ne 0 ]; then
    print_error "Cloud Build failed. Please check the logs above."
    exit 1
fi

# Get the service URL
print_status "Getting production service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null || echo "")

if [ -n "$SERVICE_URL" ]; then
    print_success "Production deployment completed successfully!"
    echo ""
    echo "🌐 Service Information:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Production URL: $SERVICE_URL"
    echo "  Health check: $SERVICE_URL/"
    echo "  API endpoint: $SERVICE_URL/recommend"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Test the health endpoint
    print_status "Testing production health endpoint..."
    sleep 5  # Wait for service to be fully ready
    
    if curl -s -f "$SERVICE_URL/" > /dev/null; then
        print_success "Production health check passed!"
        
        # Show example curl command
        echo ""
        echo "📝 Example API call:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "curl -X POST $SERVICE_URL/recommend \\"
        echo "  -H \"Content-Type: application/json\" \\"
        echo "  -d '{"
        echo "    \"GRBS\": [180, 200, 190],"
        echo "    \"Insulin\": [2, 3],"
        echo "    \"CKD\": false,"
        echo "    \"Dual inotropes\": false,"
        echo "    \"route\": \"sc\","
        echo "    \"diet_order\": \"NPO\""
        echo "  }'"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        print_warning "Production health check failed. Service might still be starting up."
        echo "Please wait a few moments and try accessing: $SERVICE_URL/"
    fi
else
    print_error "Failed to get production service URL. Please check the deployment logs."
    exit 1
fi

print_success "Production deployment script completed!"

