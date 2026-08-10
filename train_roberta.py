# ============================================================
#  AIVera — High-Accuracy Fake News Detection: Training Script
#  Target: ≥90% Accuracy / F1  |  Google Colab (T4 / A100 GPU)
#
#  WHY THE PREVIOUS LIAR TRAINING TOPPED OUT AT ~70%:
#  ─────────────────────────────────────────────────
#  The LIAR dataset contains only short political claim statements
#  (avg. 18 words) with noisy crowd-sourced labels. SOTA models
#  on LIAR max out at ~72-75% — not a code problem, a dataset
#  ceiling. To reliably hit 90%+ you need full news articles.
#
#  THIS SCRIPT TRAINS ON WELFake (72,134 labelled news articles):
#  ─────────────────────────────────────────────────────────────
#  • Real articles from Reuters, NYT, Guardian, AP, etc.
#  • Fake articles from PolitiFact, GossipCop, BuzzFeed, etc.
#  • Expected accuracy with RoBERTa: 96-98%
#  • Expected accuracy with DistilBERT: 93-95%
#
#  The trained weights are drop-in replacements for the existing
#  ml-service/model_weights/distilbert/ directory.
#
#  CELL LEGEND:
#  ▶ CELL N  — run this in a new Colab cell
# ============================================================


# ▶ CELL 1 — Install dependencies
# ─────────────────────────────────────────────────────────────
"""
!pip install -q transformers datasets evaluate scikit-learn \
             accelerate torch matplotlib seaborn kaggle gdown
"""


# ▶ CELL 2 — Imports & GPU check
# ─────────────────────────────────────────────────────────────
import os
import re
import json
import gzip
import requests
import zipfile
import numpy as np
import pandas as pd
import torch
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from io import BytesIO

from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    EarlyStoppingCallback,
)
import evaluate
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression

# ── GPU check ──
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device : {device}")
if device.type == "cuda":
    print(f"GPU    : {torch.cuda.get_device_name(0)}")
    print(f"VRAM   : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("WARNING: No GPU detected. Training will be very slow.")

# Mount Google Drive for persistent storage
from google.colab import drive
drive.mount("/content/drive")

DRIVE_SAVE_PATH = "/content/drive/MyDrive/aivera_model/distilbert"
os.makedirs(DRIVE_SAVE_PATH, exist_ok=True)
print(f"\nOutputs will be saved to: {DRIVE_SAVE_PATH}")


# ▶ CELL 3 — Download & prepare WELFake dataset
# ─────────────────────────────────────────────────────────────
# WELFake: 72 134 news articles (37 106 real + 35 028 fake)
# Compiled from Kaggle Fake-and-Real-News, McIntire, Reuters, BuzzFeed.
# Available on HuggingFace — no Kaggle API key needed.

print("\n" + "="*60)
print("DATASET: WELFake (72 134 news articles)")
print("="*60)

from datasets import load_dataset as hf_load_dataset

# WELFake on HuggingFace
raw = hf_load_dataset("ramielsayed/WELFake", trust_remote_code=True)

# Peek at structure
print("\nSchema:", raw["train"].features)
print("Example:", raw["train"][0])


# ▶ CELL 4 — Label inspection & text cleaning
# ─────────────────────────────────────────────────────────────
def inspect_labels(ds, name="train"):
    s = pd.Series(ds[name]["label"])
    print(f"\n{name.upper()} label distribution:")
    print(s.value_counts().sort_index().to_string())

inspect_labels(raw, "train")

# If the dataset has a single "train" split, create val/test splits
if "validation" not in raw:
    print("\nCreating 80/10/10 train/val/test split …")
    full = raw["train"].shuffle(seed=42)
    n = len(full)
    splits = full.train_test_split(test_size=0.2, seed=42)
    val_test = splits["test"].train_test_split(test_size=0.5, seed=42)
    raw = DatasetDict({
        "train":      splits["train"],
        "validation": val_test["train"],
        "test":       val_test["test"],
    })

# Verify label semantics (WELFake: 0=FAKE, 1=REAL — same as our inference code)
print(f"\nSplit sizes: train={len(raw['train']):,}  "
      f"val={len(raw['validation']):,}  test={len(raw['test']):,}")

LABEL_NAMES = {0: "FAKE", 1: "REAL"}

# Text cleaning — strip HTML leftover, excess whitespace, null bytes
_CLEAN_RE = re.compile(r"<[^>]+>|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

def clean_text(example):
    title = str(example.get("title", "") or "").strip()
    text  = str(example.get("text",  "") or "").strip()
    # Combine title + body; title provides strong signal
    combined = (title + " [SEP] " + text) if title else text
    combined = _CLEAN_RE.sub(" ", combined)
    combined = re.sub(r"\s+", " ", combined).strip()
    example["text"]  = combined[:2000]    # cap at 2000 chars before tokenisation
    example["label"] = int(example["label"])
    return example

raw = raw.map(clean_text, desc="Cleaning text")


# ▶ CELL 5 — Tokenisation
# ─────────────────────────────────────────────────────────────
# MODEL CHOICE — options ranked best-to-fastest:
#   "roberta-base"               → ~96-98% on WELFake  (recommended)
#   "distilbert-base-uncased"    → ~93-95% on WELFake  (2× faster)
#   "microsoft/deberta-v3-base"  → ~97-99% on WELFake  (needs more VRAM)

MODEL_NAME = "roberta-base"          # ← change to distilbert-base-uncased if VRAM is tight
MAX_LENGTH = 256                     # longer context = better accuracy on full articles

print(f"\nLoading tokenizer: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def tokenize(batch):
    return tokenizer(
        batch["text"],
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
    )

tokenized = raw.map(tokenize, batched=True, batch_size=512, desc="Tokenising")
tokenized = tokenized.rename_column("label", "labels")
tokenized.set_format(
    type="torch",
    columns=["input_ids", "attention_mask", "labels"],
)

train_ds = tokenized["train"]
val_ds   = tokenized["validation"]
test_ds  = tokenized["test"]

print(f"\nTokenised:  train={len(train_ds):,}  val={len(val_ds):,}  test={len(test_ds):,}")


# ▶ CELL 6 — Class-weighted loss (handles imbalance)
# ─────────────────────────────────────────────────────────────
# Count class frequency in training set to compute inverse-frequency weights.
train_labels = np.array(train_ds["labels"])
class_counts = np.bincount(train_labels)
class_weights = torch.tensor(
    len(train_labels) / (len(class_counts) * class_counts),
    dtype=torch.float,
).to(device)
print(f"\nClass weights (inverse freq):  FAKE={class_weights[0]:.4f}  REAL={class_weights[1]:.4f}")


# ▶ CELL 7 — Custom Trainer with weighted cross-entropy + label smoothing
# ─────────────────────────────────────────────────────────────
class WeightedTrainer(Trainer):
    """
    HuggingFace Trainer subclass that uses class-weighted cross-entropy
    loss and optional label smoothing to improve training on imbalanced data.
    """
    def __init__(self, *args, class_weights=None, label_smoothing=0.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights   = class_weights
        self.label_smoothing = label_smoothing

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits  = outputs.logits

        # Weighted cross-entropy
        loss_fct = torch.nn.CrossEntropyLoss(
            weight=self.class_weights,
            label_smoothing=self.label_smoothing,
        )
        loss = loss_fct(logits.view(-1, self.model.config.num_labels), labels.view(-1))

        return (loss, outputs) if return_outputs else loss


# ▶ CELL 8 — Model
# ─────────────────────────────────────────────────────────────
print(f"\nLoading model: {MODEL_NAME}  (num_labels=2)")
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=2,
    id2label={0: "FAKE", 1: "REAL"},
    label2id={"FAKE": 0, "REAL": 1},
)
model.to(device)
total_params = sum(p.numel() for p in model.parameters())
print(f"Parameters: {total_params:,}")


# ▶ CELL 9 — Metrics
# ─────────────────────────────────────────────────────────────
acc_metric = evaluate.load("accuracy")
f1_metric  = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    acc  = acc_metric.compute(predictions=preds, references=labels)["accuracy"]
    f1   = f1_metric.compute(predictions=preds, references=labels, average="weighted")["f1"]
    prec = precision_score(labels, preds, average="weighted", zero_division=0)
    rec  = recall_score(labels, preds, average="weighted", zero_division=0)
    return {
        "accuracy":  round(acc,  4),
        "f1":        round(f1,   4),
        "precision": round(prec, 4),
        "recall":    round(rec,  4),
    }


# ▶ CELL 10 — Training arguments (tuned for 90%+ on T4)
# ─────────────────────────────────────────────────────────────
# Batch 16 + grad accumulation 2 = effective batch 32.
# Use batch 32 directly if you have ≥16 GB VRAM.

EPOCHS             = 5
BATCH_SIZE         = 16
GRAD_ACCUM         = 2          # effective batch = 32
LR                 = 2e-5
LABEL_SMOOTHING    = 0.05       # slight smoothing reduces overconfidence
WARMUP_RATIO       = 0.06

training_args = TrainingArguments(
    output_dir="./results",

    # Evaluation & checkpointing
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,

    # Optimisation
    learning_rate=LR,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE * 2,
    gradient_accumulation_steps=GRAD_ACCUM,
    num_train_epochs=EPOCHS,
    weight_decay=0.01,
    warmup_ratio=WARMUP_RATIO,
    lr_scheduler_type="cosine",

    # Speed & stability
    fp16=torch.cuda.is_available(),
    dataloader_num_workers=2,
    group_by_length=True,        # batch similar lengths → faster training

    # Logging
    logging_dir="./logs",
    logging_steps=100,
    report_to="none",
)

trainer = WeightedTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    compute_metrics=compute_metrics,
    class_weights=class_weights,
    label_smoothing=LABEL_SMOOTHING,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)


# ▶ CELL 11 — Train
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"TRAINING  {MODEL_NAME}  on WELFake")
print(f"Effective batch size: {BATCH_SIZE * GRAD_ACCUM}")
print("="*60)
train_result = trainer.train()
print(f"\nTraining done. Steps: {train_result.global_step}")


# ▶ CELL 12 — Evaluation on held-out test set
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("FINAL METRICS — HELD-OUT TEST SET")
print("="*60)

test_results = trainer.evaluate(test_ds)
print(f"\n  Accuracy  : {test_results['eval_accuracy']:.4f}  ({test_results['eval_accuracy']*100:.2f}%)")
print(f"  F1        : {test_results['eval_f1']:.4f}")
print(f"  Precision : {test_results['eval_precision']:.4f}")
print(f"  Recall    : {test_results['eval_recall']:.4f}")

# Detailed per-class classification report
pred_output = trainer.predict(test_ds)
preds  = np.argmax(pred_output.predictions, axis=-1)
labels = pred_output.label_ids

print("\nPer-Class Classification Report:")
print(classification_report(labels, preds, target_names=["FAKE (0)", "REAL (1)"]))

# Confusion matrix
cm = confusion_matrix(labels, preds)
fig, ax = plt.subplots(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=["FAKE", "REAL"], yticklabels=["FAKE", "REAL"], ax=ax)
ax.set_title(f"Confusion Matrix — {MODEL_NAME} on WELFake")
ax.set_ylabel("True")
ax.set_xlabel("Predicted")
plt.tight_layout()
plt.savefig(f"{DRIVE_SAVE_PATH}/confusion_matrix.png", dpi=150)
plt.show()

# Save baseline metrics JSON (serves as documented benchmark)
baseline = {
    "model":           MODEL_NAME,
    "dataset":         "WELFake (ramielsayed/WELFake)",
    "max_length":      MAX_LENGTH,
    "epochs_run":      int(train_result.global_step / len(train_ds) * BATCH_SIZE * GRAD_ACCUM),
    "lr":              LR,
    "batch_size_eff":  BATCH_SIZE * GRAD_ACCUM,
    "label_smoothing": LABEL_SMOOTHING,
    "test_accuracy":   test_results["eval_accuracy"],
    "test_f1":         test_results["eval_f1"],
    "test_precision":  test_results["eval_precision"],
    "test_recall":     test_results["eval_recall"],
}
with open(f"{DRIVE_SAVE_PATH}/baseline_metrics.json", "w") as f:
    json.dump(baseline, f, indent=2)
print(f"\nBaseline metrics → {DRIVE_SAVE_PATH}/baseline_metrics.json")


# ▶ CELL 13 — Training loss curve
# ─────────────────────────────────────────────────────────────
history    = trainer.state.log_history
t_steps    = [x["step"] for x in history if "loss"      in x]
t_loss     = [x["loss"]      for x in history if "loss"      in x]
e_steps    = [x["step"] for x in history if "eval_loss" in x]
e_loss     = [x["eval_loss"] for x in history if "eval_loss" in x]
e_f1       = [x.get("eval_f1", None) for x in history if "eval_loss" in x]

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
axes[0].plot(t_steps, t_loss, label="Train Loss", alpha=0.8)
axes[0].plot(e_steps, e_loss, label="Val Loss",   marker="o")
axes[0].set(title="Loss Curve", xlabel="Step", ylabel="Loss")
axes[0].legend(); axes[0].grid(alpha=0.3)

if any(v is not None for v in e_f1):
    axes[1].plot(e_steps, e_f1, marker="o", color="green", label="Val F1")
    axes[1].axhline(0.90, color="red", linestyle="--", label="90% target")
    axes[1].set(title="Validation F1 per Epoch", xlabel="Step", ylabel="F1")
    axes[1].legend(); axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f"{DRIVE_SAVE_PATH}/training_curves.png", dpi=150)
plt.show()


# ▶ CELL 14 — Platt scaling calibration
# ─────────────────────────────────────────────────────────────
# Fits a logistic regression on top of raw softmax probabilities
# (validation set) to produce calibrated confidence scores.
# The resulting A/B values replace the defaults in calibration.py.

print("\n" + "="*60)
print("CONFIDENCE CALIBRATION (Platt Scaling)")
print("="*60)

val_out   = trainer.predict(val_ds)
raw_logits = val_out.predictions        # (N, 2)
val_labels = val_out.label_ids

def _softmax(x):
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)

raw_probs = _softmax(raw_logits)[:, 1].reshape(-1, 1)

platt = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000)
platt.fit(raw_probs, val_labels)

# Convention: p = 1 / (1 + exp(A*f + B))
#  LogisticRegression: p = 1 / (1 + exp(-(coef*f + intercept)))
#  so A = -coef,  B = -intercept
platt_A = float(-platt.coef_[0][0])
platt_B = float(-platt.intercept_[0])

print(f"\nPlatt A = {platt_A:.6f}")
print(f"Platt B = {platt_B:.6f}")
print("\n→ Open  ml-service/services/calibration.py  and update:")
print(f"    _A: float = {platt_A:.6f}")
print(f"    _B: float = {platt_B:.6f}")

with open(f"{DRIVE_SAVE_PATH}/calibration_params.json", "w") as f:
    json.dump({"platt_A": platt_A, "platt_B": platt_B}, f, indent=2)


# ▶ CELL 15 — Save model & tokenizer to Google Drive
# ─────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SAVING MODEL + TOKENIZER")
print("="*60)

model.save_pretrained(DRIVE_SAVE_PATH)
tokenizer.save_pretrained(DRIVE_SAVE_PATH)

readme_content = f"""# AIVera — {MODEL_NAME} on WELFake

## Training Details
| Parameter      | Value |
|---------------|-------|
| Base model    | {MODEL_NAME} |
| Dataset       | WELFake (72 134 news articles) |
| Max token len | {MAX_LENGTH} |
| Batch size    | {BATCH_SIZE * GRAD_ACCUM} (effective) |
| Learning rate | {LR} |
| Label smooth  | {LABEL_SMOOTHING} |
| Class weights | {'Yes (inverse freq)' } |

## Baseline Metrics — Test Set
| Metric    | Score |
|-----------|-------|
| Accuracy  | {test_results['eval_accuracy']:.4f} ({test_results['eval_accuracy']*100:.2f}%) |
| F1        | {test_results['eval_f1']:.4f} |
| Precision | {test_results['eval_precision']:.4f} |
| Recall    | {test_results['eval_recall']:.4f} |

## Confidence Calibration (Platt Scaling)
```python
# ml-service/services/calibration.py
_A: float = {platt_A:.6f}
_B: float = {platt_B:.6f}
```

## Deployment
1. Download this folder from Google Drive.
2. Place it at:  `ml-service/model_weights/distilbert/`
3. Update `_A` and `_B` in `ml-service/services/calibration.py`.
4. Restart the ML service.

## Notes
- Binary label: **FAKE = 0**, **REAL = 1**
- WELFake achieves 93-98% accuracy with BERT-class models vs ~70% for LIAR.
- LIAR is not suitable for 90%+ targets due to noisy short-text labels.
"""
with open(f"{DRIVE_SAVE_PATH}/MODEL_README.md", "w") as f:
    f.write(readme_content)

# Summary
print("\n✅ All files saved to Drive:")
for p in sorted(Path(DRIVE_SAVE_PATH).iterdir()):
    size_mb = p.stat().st_size / 1e6
    print(f"  {p.name:<40} {size_mb:6.1f} MB")

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  NEXT STEPS                                                  ║
╠══════════════════════════════════════════════════════════════╣
║  1. Download  {DRIVE_SAVE_PATH}
║  2. Place the folder at:
║       ml-service/model_weights/distilbert/
║  3. Open  ml-service/services/calibration.py  and set:
║       _A = {platt_A:<10.6f}
║       _B = {platt_B:<10.6f}
║  4. Restart the ML service.
╚══════════════════════════════════════════════════════════════╝
""")


# ▶ CELL 16 — (Optional) If WELFake HF link is unavailable: manual CSV upload
# ─────────────────────────────────────────────────────────────
# If you can't access the HuggingFace dataset, download WELFake CSV manually:
#
#   Kaggle:  https://www.kaggle.com/datasets/saurabhshahane/fake-news-classification
#   Direct:  https://zenodo.org/record/4561253/files/WELFake_Dataset.csv.gz
#
# Then in Colab:
#
#   from google.colab import files
#   uploaded = files.upload()  # upload WELFake_Dataset.csv
#   df = pd.read_csv("WELFake_Dataset.csv")
#   df = df.dropna(subset=["text", "label"])
#   df["label"] = df["label"].astype(int)
#   # Then create a Dataset from the DataFrame and skip CELL 3 load:
#   from datasets import Dataset
#   full_ds = Dataset.from_pandas(df[["title", "text", "label"]])
#   # Continue from CELL 4 clean_text mapping …
