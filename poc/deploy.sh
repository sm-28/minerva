#!/bin/bash

set -e  # stop on first error

echo "🚀 Starting Minerva deployment..."

cd /home/ubuntu/minerva

echo "📥 Pulling latest code..."
git pull origin master

echo "📦 Installing dependencies..."
source poc/venv/bin/activate
pip install -r poc/requirements.txt

echo "🔄 Restarting Streamlit service..."
sudo systemctl restart minerva

echo "✅ Deployment complete!"