"""
DEEPFAKE / AI-GENERATED IMAGE DETECTION SYSTEM
================================================
CNN-based binary classifier: REAL vs FAKE (AI-generated/deepfake) images.

Concepts used:
- Convolutional Neural Networks (CNN)
- Transfer Learning (ResNet18 backbone, pretrained on ImageNet)
- Computer Vision preprocessing (face-agnostic, works on general images too)
- Train/Validation split, data augmentation
- Frame extraction for video deepfake detection

HOW TO RUN
----------
1. Install dependencies:
   pip install torch torchvision pillow numpy scikit-learn opencv-python matplotlib

2. Organize your dataset like this:
   dataset/
       train/
           real/   <- real images (.jpg/.png)
           fake/   <- deepfake / AI-generated images
       val/
           real/
           fake/

   (Public datasets you can use: FaceForensics++, Kaggle "Deepfake Detection
   Challenge", "140k Real and Fake Faces" on Kaggle.)

3. Train:
   python deepfake_detector.py --mode train --data_dir dataset --epochs 10

4. Predict on a single image:
   python deepfake_detector.py --mode predict --image path/to/image.jpg

5. Predict on a video (samples frames and averages predictions):
   python deepfake_detector.py --mode predict_video --video path/to/video.mp4

NO DATASET YET?
----------------
Run in demo mode to verify the whole pipeline works end-to-end using
auto-generated synthetic images (no real data needed):
   python deepfake_detector.py --mode demo
"""

import argparse
import random
import re
from datetime import datetime
import numpy as np
from pathlib import Path

from PIL import Image

try:
    import torch  # type: ignore[reportMissingImports]
    import torch.nn as nn  # type: ignore[reportMissingImports]
    import torch.optim as optim  # type: ignore[reportMissingImports]
    from torch.utils.data import Dataset, DataLoader, random_split  # type: ignore[reportMissingImports]
    from torchvision import transforms, models  # type: ignore[reportMissingImports]
except ModuleNotFoundError:
    torch = None
    nn = None
    optim = None
    Dataset = object
    DataLoader = None
    random_split = None
    transforms = None
    models = None

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
DEVICE = torch.device("cuda" if torch and torch.cuda.is_available() else "cpu") if torch else "cpu"
IMG_SIZE = 224
BATCH_SIZE = 16
MODEL_PATH = "deepfake_model.pth"
CLASS_NAMES = ["real", "fake"]
NEWS_REPORT_PATH = "fake_news_report.txt"

if torch:
    torch.manual_seed(42)
random.seed(42)
np.random.seed(42)


def require_ml_dependencies():
    if torch is None or nn is None or transforms is None or models is None:
        raise RuntimeError(
            "Image/video deepfake detection needs extra packages. Install them with:\n"
            "pip install torch torchvision pillow numpy scikit-learn opencv-python matplotlib"
        )

# ----------------------------------------------------------------------------
# 1. DATASET
# ----------------------------------------------------------------------------
class ImageFolderDataset(Dataset):
    """Loads images from data_dir/real and data_dir/fake."""

    def __init__(self, data_dir, transform=None):
        self.samples = []
        self.transform = transform
        for label_name, label_idx in [("real", 0), ("fake", 1)]:
            folder = Path(data_dir) / label_name
            if not folder.exists():
                continue
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                for img_path in folder.glob(ext):
                    self.samples.append((str(img_path), label_idx))

        if len(self.samples) == 0:
            raise RuntimeError(
                f"No images found under {data_dir}/real or {data_dir}/fake. "
                f"Check your folder structure."
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


def get_transforms(train=True):
    require_ml_dependencies()
    if train:
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.RandomRotation(10),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])


# ----------------------------------------------------------------------------
# 2. MODEL — CNN via transfer learning (ResNet18) + a custom head
# ----------------------------------------------------------------------------
class DeepfakeCNN(nn.Module if nn else object):
    """
    Transfer-learning CNN: pretrained ResNet18 backbone (learns real-world
    visual features) + custom classification head trained on real/fake data.
    Also exposes a plain 'from-scratch' CNN option (see SimpleCNN below).
    """

    def __init__(self, freeze_backbone=True):
        require_ml_dependencies()
        super().__init__()
        backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
        num_features = backbone.fc.in_features

        if freeze_backbone:
            for param in backbone.parameters():
                param.requires_grad = False

        backbone.fc = nn.Sequential(
            nn.Linear(num_features, 256),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(256, 2)  # 2 classes: real, fake
        )
        self.model = backbone

    def forward(self, x):
        return self.model(x)


class SimpleCNN(nn.Module if nn else object):
    """A plain CNN built from scratch (no pretrained weights) — useful to
    show/understand the core CNN concept: conv -> relu -> pool stacks."""

    def __init__(self):
        require_ml_dependencies()
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),   # 224->112
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),  # 112->56
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2), # 56->28
            nn.Conv2d(128, 256, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),# 28->14
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(256 * 14 * 14, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 2),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)


# ----------------------------------------------------------------------------
# 3. TRAINING
# ----------------------------------------------------------------------------
def train_model(data_dir, epochs=10, use_transfer_learning=True):
    train_tf = get_transforms(train=True)
    val_tf = get_transforms(train=False)

    train_dir = Path(data_dir) / "train"
    val_dir = Path(data_dir) / "val"

    if train_dir.exists() and val_dir.exists():
        train_ds = ImageFolderDataset(train_dir, train_tf)
        val_ds = ImageFolderDataset(val_dir, val_tf)
    else:
        # fall back: single folder with real/fake -> auto split 80/20
        full_ds = ImageFolderDataset(data_dir, train_tf)
        n_val = int(0.2 * len(full_ds))
        n_train = len(full_ds) - n_val
        train_ds, val_ds = random_split(full_ds, [n_train, n_val])

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = DeepfakeCNN(freeze_backbone=True) if use_transfer_learning else SimpleCNN()
    model.to(DEVICE)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-3)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    best_val_acc = 0.0

    for epoch in range(epochs):
        # ---- train ----
        model.train()
        running_loss, correct, total = 0.0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)

        train_loss = running_loss / total
        train_acc = correct / total

        # ---- validate ----
        val_acc, val_loss = evaluate(model, val_loader, criterion)
        scheduler.step()

        print(f"Epoch {epoch+1}/{epochs} | "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), MODEL_PATH)
            print(f"  -> saved new best model (val_acc={val_acc:.4f})")

    print(f"\nTraining complete. Best val accuracy: {best_val_acc:.4f}")
    print(f"Model saved to: {MODEL_PATH}")


def evaluate(model, loader, criterion):
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(DEVICE), labels.to(DEVICE)
            outputs = model(images)
            loss = criterion(outputs, labels)
            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
    return correct / total, running_loss / total


# ----------------------------------------------------------------------------
# 4. INFERENCE — single image
# ----------------------------------------------------------------------------
def load_trained_model(model_path=MODEL_PATH, use_transfer_learning=True):
    model = DeepfakeCNN(freeze_backbone=True) if use_transfer_learning else SimpleCNN()
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.to(DEVICE)
    model.eval()
    return model


def predict_image(image_path, model=None):
    if model is None:
        model = load_trained_model()
    tf = get_transforms(train=False)
    image = Image.open(image_path).convert("RGB")
    tensor = tf(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)[0]
        pred_idx = torch.argmax(probs).item()

    label = CLASS_NAMES[pred_idx]
    confidence = probs[pred_idx].item()
    print(f"Image: {image_path}")
    print(f"Prediction: {label.upper()}  (confidence: {confidence*100:.2f}%)")
    print(f"  real: {probs[0]*100:.2f}%  |  fake: {probs[1]*100:.2f}%")
    return label, confidence


# ----------------------------------------------------------------------------
# 5. INFERENCE — video (samples N frames, averages predictions)
# ----------------------------------------------------------------------------
def predict_video(video_path, num_frames=16, model=None):
    import cv2  # imported here so image-only usage doesn't require opencv

    if model is None:
        model = load_trained_model()
    tf = get_transforms(train=False)

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        raise RuntimeError(f"Could not read frames from {video_path}")

    frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    fake_probs = []

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
        tensor = tf(image).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            outputs = model(tensor)
            probs = torch.softmax(outputs, dim=1)[0]
            fake_probs.append(probs[1].item())

    cap.release()

    avg_fake_prob = float(np.mean(fake_probs))
    label = "fake" if avg_fake_prob > 0.5 else "real"
    print(f"Video: {video_path}")
    print(f"Frames analyzed: {len(fake_probs)}")
    print(f"Average fake probability: {avg_fake_prob*100:.2f}%")
    print(f"Verdict: {label.upper()}")
    return label, avg_fake_prob


# ----------------------------------------------------------------------------
# 6. DEMO MODE — auto-generates synthetic data so you can test end-to-end
#    without downloading a real dataset first.
# ----------------------------------------------------------------------------
def make_demo_dataset(root="demo_dataset", n_per_class=60):
    root = Path(root)
    for split, n in [("train", n_per_class), ("val", max(10, n_per_class // 4))]:
        for cls in ["real", "fake"]:
            folder = root / split / cls
            folder.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                # "real": smoother gradient images; "fake": noisier images
                # (purely synthetic stand-in so the pipeline is runnable
                # without a real deepfake dataset)
                arr = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
                if cls == "real":
                    grad = np.linspace(0, 255, IMG_SIZE, dtype=np.uint8)
                    arr[:, :, 0] = grad
                    arr[:, :, 1] = grad[::-1]
                    arr[:, :, 2] = 128
                else:
                    arr = np.random.randint(0, 255, (IMG_SIZE, IMG_SIZE, 3), dtype=np.uint8)
                Image.fromarray(arr).save(folder / f"{cls}_{i}.png")
    print(f"Synthetic demo dataset created at: {root}/")
    return str(root)


# ----------------------------------------------------------------------------
# 7. FAKE NEWS TEXT DETECTION — lightweight rule-based checker + report
# ----------------------------------------------------------------------------
SUSPICIOUS_NEWS_WORDS = {
    "shocking", "secret", "exposed", "miracle", "guaranteed", "cure",
    "breaking", "viral", "banned", "they don't want you to know",
    "must read", "forward this", "unbelievable", "conspiracy", "hoax",
    "100%", "truth revealed", "hidden truth", "click here", "share now",
}

TRUST_CUES = {
    "according to", "reported by", "official statement", "press release",
    "court documents", "police said", "government data", "researchers found",
    "study published", "reuters", "associated press", "ap news", "bbc",
    "the hindu", "indian express", "times of india", "ndtv", "pti",
}


def detect_fake_news_text(news_text):
    """
    Lightweight fake-news detector for typed/pasted news.

    This is not a trained fact-checking model. It gives a risk score based on
    writing signals such as sensational wording, missing attribution, excessive
    punctuation, and the presence/absence of source cues.
    """
    text = news_text.strip()
    if not text:
        raise ValueError("Please enter some news text first.")

    lowered = text.lower()
    score = 0
    reasons = []

    suspicious_hits = [word for word in SUSPICIOUS_NEWS_WORDS if word in lowered]
    if suspicious_hits:
        points = min(30, len(suspicious_hits) * 8)
        score += points
        reasons.append(f"Sensational/clickbait terms found: {', '.join(suspicious_hits[:5])}")

    exclamation_count = text.count("!")
    if exclamation_count >= 2:
        score += min(20, exclamation_count * 4)
        reasons.append("Uses many exclamation marks, which is common in misleading posts.")

    words = re.findall(r"[A-Za-z]+", text)
    if words:
        all_caps_words = [word for word in words if len(word) > 3 and word.isupper()]
        caps_ratio = len(all_caps_words) / len(words)
        if caps_ratio > 0.12:
            score += 15
            reasons.append("Contains many all-caps words, which can signal sensational writing.")

    has_url = bool(re.search(r"https?://|www\.", lowered))
    has_date = bool(re.search(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b|\b20\d{2}\b", lowered))
    trust_hits = [cue for cue in TRUST_CUES if cue in lowered]

    if not trust_hits:
        score += 20
        reasons.append("No clear source or attribution was found.")
    else:
        score -= min(25, len(trust_hits) * 10)
        reasons.append(f"Credibility cues found: {', '.join(trust_hits[:4])}")

    if not has_date:
        score += 8
        reasons.append("No date/year was found, so the claim may be hard to verify.")

    if has_url:
        score -= 5
        reasons.append("Includes a link, which can help verification if the source is reliable.")

    if len(words) < 35:
        score += 10
        reasons.append("Text is very short, so there is limited evidence to judge reliability.")

    score = max(0, min(100, score))
    verdict = "likely false/misleading" if score >= 55 else "possibly reliable"
    confidence = score if score >= 55 else 100 - score

    return {
        "verdict": verdict,
        "risk_score": score,
        "confidence": confidence,
        "reasons": reasons,
    }


def build_news_report(news_text, result):
    lines = [
        "FAKE NEWS TEXT DETECTION REPORT",
        "=" * 36,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Verdict: {result['verdict'].upper()}",
        f"Risk score: {result['risk_score']} / 100",
        f"Confidence: {result['confidence']:.1f}%",
        "",
        "Reasons:",
    ]
    lines.extend(f"- {reason}" for reason in result["reasons"])
    lines.extend([
        "",
        "Important note:",
        "This is a writing-pattern checker, not a full fact-checking service.",
        "Always verify serious claims with trusted news sources or official data.",
        "",
        "Input text:",
        news_text.strip(),
        "",
    ])
    return "\n".join(lines)


def save_news_report(news_text, result, report_path=NEWS_REPORT_PATH):
    report = build_news_report(news_text, result)
    Path(report_path).write_text(report, encoding="utf-8")
    return report_path


def predict_news_text(news_text):
    result = detect_fake_news_text(news_text)
    save_news_report(news_text, result)
    print(f"Verdict: {result['verdict'].upper()}")
    print(f"Risk score: {result['risk_score']} / 100")
    print(f"Confidence: {result['confidence']:.1f}%")
    print("Reasons:")
    for reason in result["reasons"]:
        print(f"  - {reason}")
    print(f"Report saved to: {NEWS_REPORT_PATH}")
    return result


def open_news_dialog():
    import tkinter as tk
    from tkinter import messagebox, scrolledtext

    root = tk.Tk()
    root.title("Fake News Detector")
    root.geometry("760x560")

    tk.Label(root, text="Paste or type the news text below:").pack(anchor="w", padx=12, pady=(12, 4))

    input_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=13, font=("Segoe UI", 10))
    input_box.pack(fill=tk.BOTH, expand=True, padx=12)

    result_var = tk.StringVar(value="Verdict will appear here.")
    result_label = tk.Label(root, textvariable=result_var, justify="left", anchor="w", font=("Segoe UI", 10, "bold"))
    result_label.pack(fill=tk.X, padx=12, pady=10)

    report_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10, font=("Consolas", 9))
    report_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

    def run_detection():
        news_text = input_box.get("1.0", tk.END).strip()
        try:
            result = detect_fake_news_text(news_text)
            report = build_news_report(news_text, result)
            save_news_report(news_text, result)
        except ValueError as exc:
            messagebox.showwarning("Missing input", str(exc))
            return

        result_var.set(
            f"Verdict: {result['verdict'].upper()} | "
            f"Risk score: {result['risk_score']} / 100 | "
            f"Confidence: {result['confidence']:.1f}%"
        )
        report_box.delete("1.0", tk.END)
        report_box.insert(tk.END, report)
        messagebox.showinfo("Report saved", f"Report saved to {NEWS_REPORT_PATH}")

    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

    tk.Button(button_frame, text="Detect Fake News", command=run_detection).pack(side=tk.LEFT)
    tk.Button(button_frame, text="Clear", command=lambda: input_box.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=8)
    tk.Button(button_frame, text="Exit", command=root.destroy).pack(side=tk.RIGHT)

    root.mainloop()


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deepfake Image/Video and Fake News Text Detection System")
    parser.add_argument("--mode", choices=["train", "predict", "predict_video", "demo", "news", "news_gui"],
                         required=True)
    parser.add_argument("--data_dir", type=str, default="dataset")
    parser.add_argument("--image", type=str, help="Path to image for prediction")
    parser.add_argument("--video", type=str, help="Path to video for prediction")
    parser.add_argument("--text", type=str, help="News text for fake-news prediction")
    parser.add_argument("--text_file", type=str, help="Text file containing news for fake-news prediction")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--scratch_cnn", action="store_true",
                         help="Use from-scratch SimpleCNN instead of transfer learning")
    args = parser.parse_args()

    if args.mode == "demo":
        demo_dir = make_demo_dataset()
        train_model(demo_dir, epochs=3, use_transfer_learning=not args.scratch_cnn)
        # quick sanity check prediction on one of the generated images
        sample = list(Path(demo_dir, "val", "fake").glob("*.png"))[0]
        predict_image(str(sample))

    elif args.mode == "train":
        train_model(args.data_dir, epochs=args.epochs,
                    use_transfer_learning=not args.scratch_cnn)

    elif args.mode == "predict":
        if not args.image:
            raise ValueError("Please provide --image path/to/image.jpg")
        predict_image(args.image)

    elif args.mode == "predict_video":
        if not args.video:
            raise ValueError("Please provide --video path/to/video.mp4")
        predict_video(args.video)

    elif args.mode == "news":
        if args.text_file:
            news_text = Path(args.text_file).read_text(encoding="utf-8")
        elif args.text:
            news_text = args.text
        else:
            raise ValueError("Please provide --text \"news text\" or --text_file news.txt")
        predict_news_text(news_text)

    elif args.mode == "news_gui":
        open_news_dialog()
