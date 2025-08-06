# Models Directory

This directory should contain your GGUF format AI models.

## Recommended Models

Download any of these models and place them in this folder:

### Small Models (2-4GB):
- **Phi-3-mini-4k-instruct** (Microsoft, 3.8B parameters)
  - Download: https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf
  - Good for: Fast responses, general chat

### Medium Models (4-8GB):
- **Mistral-7B-Instruct** (7B parameters)
  - Download: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GGUF
  - Good for: Better quality responses, still reasonable speed

## Installation Instructions

1. Visit the Hugging Face link for your chosen model
2. Download the `.gguf` file (choose Q4_K_M for best balance of quality/size)
3. Place the `.gguf` file in this `models/` directory
4. The filename should be something like: `model-name-q4.gguf`

## Model Format Requirements

- **Format**: GGUF (`.gguf` files)
- **Quantization**: Q4_K_M recommended for best quality/size balance
- **Size**: Smaller models (2-4GB) for faster inference, larger models (8GB+) for better quality