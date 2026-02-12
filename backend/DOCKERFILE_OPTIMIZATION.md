# Docker Image Size Optimization

## Changes Made

### 1. **CPU-Only PyTorch Installation**
   - **Before:** Installing PyTorch with CUDA support (~900MB+)
   - **After:** Installing CPU-only PyTorch (~200MB)
   - **Savings:** ~700MB
   - **Impact:** Models download at runtime anyway, CPU version is sufficient for inference

### 2. **Installation Order Optimization**
   - Install PyTorch CPU-only **before** sentence-transformers
   - This prevents pip from pulling CUDA dependencies
   - sentence-transformers will use the already-installed CPU PyTorch

### 3. **.dockerignore Enhancements**
   - Exclude test files, documentation, and cache directories
   - Exclude Input/Output folders (not needed in backend API)
   - Exclude model cache (models download at runtime)
   - **Savings:** ~50-100MB

### 4. **Build Layer Optimization**
   - Combined system package installation in one RUN command
   - Removed unnecessary pip cache
   - **Savings:** ~20-30MB

## Expected Image Size Reduction

- **Before:** ~3-4GB (with CUDA PyTorch)
- **After:** ~1.5-2GB (with CPU PyTorch)
- **Total Savings:** ~1.5-2GB

## Model Download Behavior

Models are downloaded at **runtime** (not included in image):
- `all-MiniLM-L6-v2` (~80MB) downloads on first use
- Cached in `~/.cache/huggingface/` for subsequent uses
- Can be pre-downloaded in a volume if needed

## Additional Optimization Options

If you need even smaller images, consider:

1. **Multi-stage build** - Copy only runtime dependencies
2. **Alpine base image** - Smaller base (~50MB vs ~150MB)
3. **Pre-download models** - Include models in image (increases size but faster startup)
4. **Separate ML service** - Run ML models in separate container

## Testing

After building, verify:
```bash
docker images | grep backend-api
docker run --rm backend-api python -c "import torch; print(torch.__version__)"
docker run --rm backend-api python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```
