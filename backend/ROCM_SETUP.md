# ROCm Setup Guide for LegalEase

This guide explains how to deploy LegalEase on AMD GPUs using ROCm.

## Prerequisites

- AMD GPU with ROCm support (gfx900 or newer recommended)
- Ubuntu 20.04/22.04 or compatible Linux distribution
- Python 3.10+

## ROCm Installation

### 1. Install ROCm

```bash
# Add ROCm repository
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/jammy/amdgpu-install_5.7.50700-1_all.deb
sudo dpkg -i amdgpu-install_*.deb
sudo apt update

# Install ROCm
sudo amdgpu-install --usecase=rocm
```

### 2. Install PyTorch with ROCm Support

```bash
# Install PyTorch ROCm version
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.7

# Verify installation
python3 -c "import torch; print(f'ROCm available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"
```

### 3. Install ML Dependencies with ROCm Support

```bash
# WhisperX (transcription)
pip install git+https://github.com/m-bain/whisperx.git

# Sentence Transformers (search embeddings)
pip install sentence-transformers

# Pyannote.audio (speaker diarization)
pip install pyannote.audio
```

## Device Detection

LegalEase automatically detects ROCm GPUs via the `DeviceManager` service:

```python
from app.services.device_manager import get_device_manager

device_manager = get_device_manager()
print(f"Device Type: {device_manager.device_type.value}")
print(f"Device Name: {device_manager.device_name}")
print(f"VRAM: {device_manager._vram_gb:.2f} GB")
```

## Environment Variables

Set these environment variables for optimal ROCm performance:

```bash
# ROCm installation path
export ROCM_HOME=/opt/rocm

# HIP (ROCm's CUDA alternative) visibility
export HIP_VISIBLE_DEVICES=0  # Use first GPU

# Enable TF32 tensor cores (if available on your GPU)
export HSA_OVERRIDE_GFX_VERSION=10.3.0  # Adjust for your GPU

# PyTorch settings
export PYTORCH_ROCM_ARCH="gfx1030"  # Your GPU architecture
```

## GPU Architecture Detection

Common AMD GPU architectures:

- **gfx900**: Vega 10 (RX Vega, MI25)
- **gfx906**: Vega 20 (Radeon VII, MI50/MI60)
- **gfx908**: CDNA (MI100)
- **gfx90a**: CDNA2 (MI200 series)
- **gfx1030**: RDNA2 (RX 6000 series)
- **gfx1100**: RDNA3 (RX 7000 series)

Check your GPU architecture:

```bash
rocminfo | grep "Name:"
```

## Performance Considerations

### Compute Types

The DeviceManager automatically selects optimal compute type:

- **float16**: Modern AMD GPUs (gfx900+) - Faster, uses less VRAM
- **float32**: Older GPUs or maximum precision needed

### VRAM Usage

Typical VRAM usage for LegalEase components:

- **WhisperX (large-v3)**: ~10GB VRAM
- **Pyannote diarization**: ~2GB VRAM
- **Sentence Transformers**: ~1GB VRAM
- **Total recommended**: 16GB+ VRAM

For GPUs with less VRAM:

- Use WhisperX `base` or `small` models
- Reduce batch sizes in transcription
- Enable gradient checkpointing

## Troubleshooting

### ROCm Not Detected

```bash
# Check ROCm installation
rocm-smi

# Check PyTorch ROCm build
python3 -c "import torch; print(f'ROCm: {torch.version.hip}')"
```

### Out of Memory Errors

Reduce batch sizes in `app/core/config.py`:

```python
# Transcription settings
WHISPER_BATCH_SIZE = 8  # Reduce from 16
```

### Slow Performance

Enable mixed precision:

```bash
# In .env
USE_MIXED_PRECISION=true
```

## Docker Setup (ROCm)

```dockerfile
FROM rocm/pytorch:rocm5.7_ubuntu22.04_py3.10_pytorch_2.0.1

# Install LegalEase dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run with ROCm
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

Build and run:

```bash
docker build -t legalease-rocm -f Dockerfile.rocm .
docker run --device=/dev/kfd --device=/dev/dri --group-add video -p 8000:8000 legalease-rocm
```

## Verification

Test ROCm support:

```python
from app.services.device_manager import get_device_manager

dm = get_device_manager()
assert dm.device_type.value == "rocm", "ROCm not detected!"
assert dm.has_gpu, "No GPU found!"
print(f"✓ ROCm setup successful: {dm.device_name}")
```

## Support

For ROCm-specific issues:

- AMD ROCm GitHub: https://github.com/RadeonOpenCompute/ROCm
- PyTorch ROCm: https://pytorch.org/get-started/locally/
- ROCm Documentation: https://rocmdocs.amd.com/
