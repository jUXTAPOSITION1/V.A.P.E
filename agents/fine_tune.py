import os
from datasets import Dataset
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
from datetime import datetime

def collect_training_data():
    """Collect all reports as high-quality training data"""
    data = []
    for file in os.listdir("reports"):
        if file.endswith(".md"):
            with open(f"reports/{file}", "r", encoding="utf-8") as f:
                content = f.read()
                data.append({
                    "text": f"""### Instruction:
Improve this bug bounty report with more technical depth, concrete PoCs, and actionable recommendations.

### Input:
{content}

### Response:
"""
                })
    return data

def fine_tune():
    print("Starting self-fine-tuning cycle...")
    
    model_name = "meta-llama/Llama-3.1-8B-Instruct"
    model = AutoModelForCausalLM.from_pretrained(model_name)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )
    model = get_peft_model(model, lora_config)
    
    raw_data = collect_training_data()
    dataset = Dataset.from_list(raw_data)
    
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
    return "Fine-tuning completed."

if __name__ == "__main__":
    fine_tune()
