# Explainable Fake News Detection - DistilBERT Training Script
# Optimized for Google Colab (T4 GPU)

# Step 1: Install Dependencies
# Run this cell in Colab:
# !pip install transformers datasets evaluate torch scikit-learn

import pandas as pd
import numpy as np
import torch
from datasets import load_dataset, Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer
import evaluate

def run_training():
    print("Loading Fake News Dataset...")
    # Example using a public dataset from huggingface (e.g. LIAR dataset or similar fake news datasets)
    # You can also load your custom CSV: 
    # dataset = load_dataset('csv', data_files={'train': 'train.csv', 'test': 'test.csv'})
    # Ensure your labels are 0 for FAKE and 1 for REAL, and your text col is 'text' or 'claim'
    dataset = load_dataset("chengxuphd/liar2")

    # The LIAR dataset has 6 labels. We want binary: Real/Half-True/Mostly-True -> 1 (Real), 
    # False/Pants-Fire/Barely-True -> 0 (Fake)
    def map_labels(example):
        # 0: pants-fire, 1: false, 2: barely-true, 3: half-true, 4: mostly-true, 5: true
        label = example['label']
        binary_label = 1 if label >= 3 else 0
        example['label'] = binary_label
        # Map narrative to 'text' for tokenizer
        example['text'] = example['statement']
        return example

    dataset = dataset.map(map_labels)

    print("Loading DistilBERT Tokenizer...")
    model_name = "distilbert-base-uncased"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize_function(examples):
        return tokenizer(examples['text'], padding="max_length", truncation=True, max_length=128)

    tokenized_datasets = dataset.map(tokenize_function, batched=True)
    
    # Optional: select a smaller subset if training takes too long
    train_dataset = tokenized_datasets["train"].shuffle(seed=42)
    eval_dataset = tokenized_datasets["validation"].shuffle(seed=42)

    print("Loading Model...")
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=2)
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    model.to(device)

    metric = evaluate.load("accuracy")
    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        return metric.compute(predictions=predictions, references=labels)

    print("Configuring Training Arguments...")
    training_args = TrainingArguments(
        output_dir="./results",
        evaluation_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=3,
        weight_decay=0.01,
        save_strategy="epoch",
        load_best_model_at_end=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    print("Starting Training...")
    trainer.train()

    print("Evaluating Model...")
    results = trainer.evaluate(tokenized_datasets["test"])
    print(results)

    print("Saving Fine-tuned Model and Tokenizer...")
    save_path = "./fakenews_distilbert_weights"
    model.save_pretrained(save_path)
    tokenizer.save_pretrained(save_path)
    
    print(f"Done! Models saved to {save_path}.")
    print("Download this folder and place it in your local 'ml-service/model_weights/distilbert' directory.")

if __name__ == "__main__":
    run_training()
