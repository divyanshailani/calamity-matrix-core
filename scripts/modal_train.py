"""
Calamity AI — Phase 18.5: Bulletproof L40S Pure LoRA Training
=============================================================
Trains Qwen3-8B via pure bfloat16 LoRA with preemption armor.
"""
import os
import modal

os.environ["HF_TOKEN"] = "<INSERT_YOUR_HF_TOKEN_HERE>"

app = modal.App("calamity-qwen3-pure-lora")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers",
        "peft",
        "trl",
        "accelerate",
        "datasets",
    )
)

volume = modal.Volume.from_name("calamity-model-cache", create_if_missing=True)

data_mount = modal.Mount.from_local_file(
    local_path="calamity_training_data.jsonl",
    remote_path="/data/calamity_training_data.jsonl"
)

@app.function(
    gpu="L40S",
    cpu=8.0,
    memory=32768,
    timeout=3600,
    retries=modal.Retries(max_retries=3, backoff_delay=10.0),
    image=image,
    volumes={"/model_cache": volume},
    mounts=[data_mount]
)
def train():
    import torch
    import time
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from datasets import load_dataset
    from trl import SFTTrainer

    def safe_load(fn, *args, retries=5, delay=10, **kwargs):
        """Robust loading to survive network drops."""
        for attempt in range(retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                print(f"[Attempt {attempt+1}/{retries}] Network drop or failure: {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(delay)

    print("Loading base model securely...")
    model_id = "Qwen/Qwen3-8B-Instruct"
    
    tokenizer = safe_load(AutoTokenizer.from_pretrained, model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = safe_load(
        AutoModelForCausalLM.from_pretrained,
        model_id,
        torch_dtype=torch.bfloat16,
        device_map="auto"
    )

    print("Configuring Pure LoRA adapters...")
    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM"
    )
    
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    print("Loading dataset securely...")
    dataset = safe_load(load_dataset, "json", data_files="/data/calamity_training_data.jsonl", split="train")

    def format_chatml(example):
        return {"text": tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)}

    dataset = dataset.map(format_chatml)

    print("Initializing Armored SFTTrainer...")
    output_dir = "/model_cache/calamity-qwen3-checkpoints"
    training_args = TrainingArguments(
        output_dir=output_dir,
        learning_rate=1e-4,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=10,
        bf16=True,
        logging_steps=5,
        save_strategy="steps",
        save_steps=10,
        save_total_limit=2,
        gradient_checkpointing=True
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=2048,
    )

    # Checkpoint Routing Logic
    resume = False
    if os.path.exists(output_dir):
        checkpoints = [d for d in os.listdir(output_dir) if d.startswith("checkpoint")]
        if checkpoints:
            print(f"Discovered {len(checkpoints)} existing checkpoints. Engaging resume routing...")
            resume = True

    print("Forging the model (Training)...")
    trainer.train(resume_from_checkpoint=resume)

    print("Saving final forged adapters to persistent volume...")
    final_output_path = "/model_cache/calamity-qwen3-lora-v1"
    model.save_pretrained(final_output_path)
    tokenizer.save_pretrained(final_output_path)
    
    print(f"Training complete! Artifacts securely saved to {final_output_path}")

if __name__ == "__main__":
    app.run()
