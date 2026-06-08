# NVIDIA Nemotron-3-Nano 30B A3B (Ollama)

This is an Olares application chart for the NVIDIA Nemotron-3-Nano 30B A3B model, optimized for agentic AI workflows on NVIDIA RTX GPUs.

## Model Information

- **Model**: NVIDIA Nemotron-3-Nano 30B A3B (Unsloth GGUF Q4_K_M)
- **Architecture**: Mixture-of-Experts (MoE) activating ~3B params per token
- **Optimization**: Designed for agentic AI workflows on NVIDIA RTX GPUs
- **Context Window**: 128k tokens
- **Backend**: Ollama 0.30.4

## Hardware Requirements

- NVIDIA RTX GPU with 16GB+ VRAM (optimized for RTX 5090M with 24GB)
- Minimum 16Gi GPU memory required
- Minimum 4Gi RAM required
- Minimum 50Mi disk space required

## Features

- Optimized for agentic AI workflows
- Efficient Q4_K_M quantization for local inference
- Support for tool calling and multimodal inputs
- Shared app deployment pattern (installed by Olares Admin)
- Proxy-based access through the Olares API

## Installation

This application should be installed by the Olares Admin. Once installed, all users in the cluster can use it through reference apps.

## Usage

Users can access this model through the reference app interface provided by the Olares Market.

## Deployment Structure

This is a shared application with two components:
1. **ollamaniemotron3nano30ba3bserver** - The Ollama backend service
2. **ollamaniemotron3nano30ba3b** - The proxy service that provides API access

Both components are deployed as subcharts and work together to provide the model functionality.