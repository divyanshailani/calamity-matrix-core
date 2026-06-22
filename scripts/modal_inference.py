import os
import modal

# Modal App Configuration
app = modal.App("calamity-qwen3-inference")

# Define the Image with vLLM and FastAPI dependencies
vllm_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "vllm",
        "fastapi",
        "sse-starlette",
        "peft",
        "hf-transfer"
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1", 
        "HF_TOKEN": os.environ["HF_TOKEN"],
        "VLLM_USE_FLASHINFER_SAMPLER": "0"
    })
)

# Connect to the persistent volume containing our trained LoRA adapters
volume = modal.Volume.from_name("calamity-model-cache", create_if_missing=True)

@app.cls(
    gpu="L40S",          # Massive compute for fast inference
    cpu=8.0,             # Fast loading
    memory=32768,        # Accommodate 8B model weights
    timeout=600,         # Maximum request length
    image=vllm_image,
    volumes={"/model_cache": volume}
)
class CalamityInference:
    @modal.enter()
    def load_model(self):
        """
        Cold Start Hook: This runs ONCE when the container wakes up.
        It loads the base model into the L40S VRAM.
        """
        from vllm import AsyncLLMEngine, AsyncEngineArgs
        print("[INIT] Waking up L40S Tensor Cores...")
        
        # Configure vLLM for Qwen3-8B with LoRA support
        engine_args = AsyncEngineArgs(
            model="Qwen/Qwen3-8B",
            enable_lora=True,
            max_loras=1,
            max_lora_rank=16,
            tensor_parallel_size=1,
            gpu_memory_utilization=0.90,
            dtype="bfloat16",
            trust_remote_code=True
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        print("[READY] Base model loaded. Neural Boot Sequence Complete.")

    @modal.fastapi_endpoint(method="POST")
    async def generate(self, request: dict):
        """
        The HTTP Webhook exposed to the internet.
        Expects a JSON payload: {"prompt": "..."}
        Streams SSE (Server-Sent Events) back to your FastAPI orchestrator.
        """
        from fastapi.responses import StreamingResponse
        from vllm import SamplingParams
        from vllm.utils import random_uuid
        from vllm.lora.request import LoRARequest
        
        prompt = request.get("prompt", "")
        if not prompt:
            return {"error": "Prompt is required in the JSON payload."}
            
        print(f"Received tactical request. Length: {len(prompt)} chars")
            
        # Calamity AI strict generation parameters
        sampling_params = SamplingParams(
            temperature=0.1,      # Cold, analytical
            top_p=0.9,
            max_tokens=1500,
            repetition_penalty=1.1,
            stop=["<|im_end|>"]   # ChatML stop token
        )
        
        request_id = random_uuid()
        
        # Dynamically mount the trained LoRA adapters from the Modal volume
        lora_request = LoRARequest(
            "calamity_lora", 
            1, 
            "/model_cache/calamity-qwen3-lora-v1"
        )
        
        # Start asynchronous generation
        results_generator = self.engine.generate(
            prompt, 
            sampling_params, 
            request_id,
            lora_request=lora_request
        )
        
        async def stream_results():
            last_text = ""
            async for request_output in results_generator:
                text = request_output.outputs[0].text
                # Only yield the new characters generated in this step
                new_text = text[len(last_text):]
                if new_text:
                    # SSE format requires "data: <payload>\n\n"
                    # We escape newlines in the chunk to prevent broken SSE
                    chunk = new_text.replace('\n', '\\n')
                    yield f"data: {chunk}\n\n"
                last_text = text
            # Signal the client that the stream has finished
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(stream_results(), media_type="text/event-stream")
