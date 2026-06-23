import os
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
from datetime import datetime

def collect_training_data():
    """Collect all reports as training data"""
    data = []
    for file in os.listdir("reports"):
        if file.endswith(".md"):
            with open(f"reports/{file}", "r") as f:
                content = f.read()
                data.append({"text": content})
    return data

def fine_tune():
    print("Starting self-fine-tuning cycle...")
    
    # Load base model (use 8B for faster training on limited hardware)
    model_name = "meta-llama/Llama-3.1-8B-Instruct"
    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    # LoRA config for efficient fine-tuning
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    
    # Training data from our own reports
    dataset = collect_training_data()
    
    training_args = TrainingArguments(
        output_dir="fine_tuned_model",
        num_train_epochs=1,
        per_device_train_batch_size=4,
        save_steps=100,
        logging_steps=10,
    )
    
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=dataset,
    )
    
    trainer.train()
    print("Self-fine-tuning complete. Model saved to fine_tuned_model/")

if __name__ == "__main__":
    fine_tune()
