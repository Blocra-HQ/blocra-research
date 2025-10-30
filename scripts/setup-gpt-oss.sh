#!/bin/bash

echo "🚀 Setting up GPT-OSS 120B for Starklytics Suite"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Install required packages
echo "📦 Installing required packages..."
pip install -U transformers torch

# Alternative: Install vLLM for better performance
echo "🔧 Installing vLLM (recommended for production)..."
pip install --pre vllm==0.10.1+gptoss \
    --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
    --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
    --index-strategy unsafe-best-match

echo "✅ Installation complete!"
echo ""
echo "🎯 To start the GPT-OSS model server:"
echo "   Option 1 (vLLM - Recommended):"
echo "   vllm serve openai/gpt-oss-120b"
echo ""
echo "   Option 2 (Transformers):"
echo "   transformers serve"
echo "   transformers chat localhost:8000 --model-name-or-path openai/gpt-oss-120b"
echo ""
echo "   Option 3 (Ollama - For consumer hardware):"
echo "   ollama pull gpt-oss:120b"
echo "   ollama run gpt-oss:120b"
echo ""
echo "🌐 The model will be available at http://localhost:8000"
echo "💡 Make sure to start the model server before using the AI features in Starklytics Suite"