"""
Calamity AI — Phase 18.3: Modal L40S Pure LoRA Training
=========================================================
Trains Qwen3-8B via pure bfloat16 LoRA (No Quantization).
"""
import os
import modal

os.environ["HF_TOKEN"] = "<INSERT_YOUR_HF_TOKEN_HERE>"

app = modal.App("calamity-qwen3-pure-lora")

# Image Environment
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch",
        "transformers",
        "peft",
        "trl",
        "accelerate",
        "datasets"
    )
)

# Storage Volume
volume = modal.Volume.from_name("calamity-model-cache", create_if_missing=True)

# Data Mount (Local to Cloud Bridge)
data_mount = modal.Mount.from_local_file(
    local_path="calamity_training_data.jsonl",
    remote_path="/data/calamity_training_data.jsonl"
)

@app.function(
    gpu="L40S",
    timeout=3600,
    image=image,
    volumes={"/model_cache": volume},
    mounts=[data_mount]
)
def train():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from peft import LoraConfig, get_peft_model
    from datasets import load_dataset
    from trl import SFTTrainer

    print("Loading base model in pure bfloat16...")
    model_id = "Qwen/Qwen3-8B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
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

    print("Loading dataset from mount...")
    dataset = load_dataset("json", data_files="/data/calamity_training_data.jsonl", split="train")

    def format_chatml(example):
        return {"text": tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)}

    dataset = dataset.map(format_chatml)

    print("Initializing SFTTrainer...")
    training_args = TrainingArguments(
        output_dir="/model_cache/calamity-qwen3-checkpoints",
        learning_rate=1e-4,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        num_train_epochs=10,
        bf16=True,
        logging_steps=5,
        save_strategy="no"
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        args=training_args,
        tokenizer=tokenizer,
        dataset_text_field="text",
        max_seq_length=2048,
    )

    print("Forging the model (Training)...")
    trainer.train()

    print("Saving forged adapters to persistent volume...")
    output_path = "/model_cache/calamity-qwen3-lora-v1"
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    
    print(f"Training complete! Artifacts saved to {output_path}")

if __name__ == "__main__":
    app.run()
