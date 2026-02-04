#!/bin/bash
# Deploy Event Ticket System to Fly.io

set -e

echo "=========================================="
echo "  Event Ticket System - Fly.io Deployment"
echo "=========================================="

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    echo "Error: Fly CLI not installed"
    echo "Install with: brew install flyctl"
    exit 1
fi

# Check if logged in
if ! fly auth whoami &> /dev/null; then
    echo "Please log in to Fly.io:"
    fly auth login
fi

# Parse arguments
DEPLOY_MCP=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --mcp) DEPLOY_MCP=true ;;
        --all) DEPLOY_MCP=true ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Deploy main API
echo ""
echo "=== Deploying Main API ==="

# Create app if doesn't exist
if ! fly apps list | grep -q "ai-tickets"; then
    echo "Creating app: ai-tickets"
    fly apps create ai-tickets

    # Create volume for SQLite
    echo "Creating volume for database..."
    fly volumes create tickets_data --size 1 --region sjc -a ai-tickets
fi

# Set secrets (if not already set)
echo ""
echo "Setting secrets..."
echo "Note: Set these manually if not already configured:"
echo "  fly secrets set STRIPE_SECRET_KEY=sk_xxx -a ai-tickets"
echo "  fly secrets set STRIPE_WEBHOOK_SECRET=whsec_xxx -a ai-tickets"
echo "  fly secrets set RESEND_API_KEY=re_xxx -a ai-tickets"
echo "  fly secrets set TWILIO_ACCOUNT_SID=xxx -a ai-tickets"
echo "  fly secrets set TWILIO_AUTH_TOKEN=xxx -a ai-tickets"
echo "  fly secrets set TWILIO_PHONE_NUMBER=+1xxx -a ai-tickets"

# Deploy
echo ""
echo "Deploying main API..."
fly deploy

echo ""
echo "Main API deployed!"
echo "URL: https://ai-tickets.fly.dev"

# Deploy MCP server if requested
if [ "$DEPLOY_MCP" = true ]; then
    echo ""
    echo "=== Deploying MCP HTTP Server ==="

    if ! fly apps list | grep -q "ai-tickets-mcp"; then
        echo "Creating app: ai-tickets-mcp"
        fly apps create ai-tickets-mcp

        # Create volume
        fly volumes create tickets_data --size 1 --region sjc -a ai-tickets-mcp
    fi

    echo "Deploying MCP server..."
    fly deploy --config fly.mcp.toml

    echo ""
    echo "MCP Server deployed!"
    echo "URL: https://ai-tickets-mcp.fly.dev"
fi

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Main API:    https://ai-tickets.fly.dev"
echo "API Docs:    https://ai-tickets.fly.dev/docs"
if [ "$DEPLOY_MCP" = true ]; then
    echo "MCP Server:  https://ai-tickets-mcp.fly.dev"
    echo "MCP Tools:   https://ai-tickets-mcp.fly.dev/tools"
    echo "Voice Agent: https://ai-tickets-mcp.fly.dev/voice/action"
fi
echo ""
