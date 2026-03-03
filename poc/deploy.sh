#!/bin/bash
set -e  # Exit immediately if a command fails

# =============================
# CONFIG
# =============================
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="master"
PORT=8501
LOG_DIR="$APP_DIR/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
DEPLOY_LOG="$LOG_DIR/deploy_$TIMESTAMP.log"
APP_LOG="$LOG_DIR/streamlit.log"

mkdir -p "$LOG_DIR"

# Redirect everything to deploy log
exec > >(tee -a "$DEPLOY_LOG") 2>&1

echo "======================================="
echo "🚀 Deployment started at $TIMESTAMP"
echo "======================================="

cd "$APP_DIR"

echo "📥 Fetching latest code..."
git fetch origin
git reset --hard origin/$BRANCH

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source "$APP_DIR/poc/venv/bin/activate"

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🛑 Stopping existing Streamlit..."
pkill -f "streamlit run" || true
sleep 3

echo "🚀 Starting Streamlit..."
nohup "$APP_DIR/venv/bin/streamlit" run app.py \
    --server.port $PORT \
    --server.address 0.0.0.0 \
    >> "$APP_LOG" 2>&1 &
sleep 5

if lsof -i:$PORT > /dev/null
then
    echo "✅ Deployment successful!"
else
    echo "❌ Streamlit failed to start."
    exit 1
fi

echo "======================================="
echo "🎉 Deployment completed"
echo "Deploy log: $DEPLOY_LOG"
echo "======================================="