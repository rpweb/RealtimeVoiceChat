#!/bin/bash

echo "🐳 Building RunPod Function Docker Image..."

# Set image name
IMAGE_NAME="realtime-voice-chat-runpod"
TAG="latest"

# Check if DOCKERHUB_USERNAME is provided
if [ -z "$DOCKERHUB_USERNAME" ]; then
    echo "⚠️  DOCKERHUB_USERNAME not set. Building local image only."
    FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
else
    FULL_IMAGE_NAME="$DOCKERHUB_USERNAME/$IMAGE_NAME:$TAG"
fi

# Build the Docker image
echo "📦 Building Docker image: $FULL_IMAGE_NAME"
docker build -t $FULL_IMAGE_NAME .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    
    if [ -n "$DOCKERHUB_USERNAME" ]; then
        echo "🚀 To push to Docker Hub:"
        echo "   docker push $FULL_IMAGE_NAME"
        echo ""
        echo "🤖 Or use GitHub Actions for automatic build and push:"
        echo "   git add . && git commit -m 'Update RunPod function' && git push"
    fi
    
    echo ""
    echo "🚀 To deploy to RunPod:"
    echo "   1. Use image: $FULL_IMAGE_NAME"
    echo "   2. Create a new template on RunPod using this image"
    echo "   3. Deploy as a serverless function"
    echo ""
    echo "📋 GitHub Actions will automatically build and push when you:"
    echo "   - Push changes to main/master branch"
    echo "   - Modify files in runpod-function/ directory"
else
    echo "❌ Docker build failed!"
    exit 1
fi 