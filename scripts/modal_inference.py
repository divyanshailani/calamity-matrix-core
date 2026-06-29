import os
import modal
import subprocess

# Define the Image with vLLM
# Adding hf-transfer for faster model downloading
vllm_image = (
    modal.Image.debian_slim()
    .pip_install("vllm", "hf-transfer")
    .env({
        "HF_XET_HIGH_PERFORMANCE": "1", 
        "HF_HOME": "/models/hf_cache",
        "XDG_CACHE_HOME": "/models/.cache"
    })
)

# Optional: If HF_TOKEN is in the local environment, pass it in case the base model is gated.
if "HF_TOKEN" in os.environ:
    vllm_image = vllm_image.env({"HF_TOKEN": os.environ["HF_TOKEN"]})

app = modal.App("calamity-qwen-endpoint")
volume = modal.Volume.from_name("calamity-model-cache")

@app.function(
    image=vllm_image,
    gpu="A10G", # The Goldilocks GPU (24GB VRAM)
    volumes={"/models": volume},
    scaledown_window=60,
    timeout=900,
)
@modal.concurrent(max_inputs=100)
@modal.web_server(8000, startup_timeout=900)
def openai_compatible_server():
    cmd = [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", "Qwen/Qwen3-8B",
        "--enable-lora",
        "--lora-modules", "calamity-ai=/models/calamity-qwen3-lora-v1",
        "--port", "8000",
        "--max-model-len", "4096",
        "--safetensors-load-strategy", "prefetch"
    ]
    subprocess.Popen(cmd)
