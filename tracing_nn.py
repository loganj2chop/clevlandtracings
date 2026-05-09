import pandas as pd
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

import torch
import numpy as np
import pandas as pd
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report



tracingsdf = pd.read_csv("vudstracings1000_2.csv") #at 1000

tracingsdf = tracingsdf.drop_duplicates(subset=["study_id"], keep="first")

tracingsdf.iloc[:, :] = tracingsdf.iloc[:, :].ffill(axis=1) # Forward fill missing values
outcomesdf = pd.read_csv("clevlandmani3.csv")
outcomesdf['avg_rating'] = outcomesdf['review3']#Jacks
outcomesdf2 = outcomesdf[['Textfile','avg_rating']].copy() # Keep only relevant columns
df = outcomesdf2.merge(tracingsdf, left_on='Textfile', right_on='study_id', how='inner')
ids = df[['Textfile', 'study_id','avg_rating']].copy()
df = df.drop(columns=['Textfile', 'study_id'])



# ── Data prep ────────────────────────────────────────────────────────────────
X = df[value_cols].values.astype(np.float32)
y = df["avg_rating"].values

le = LabelEncoder()
y = le.fit_transform(y)

num_classes = len(np.unique(y))
device = "cuda" if torch.cuda.is_available() else "cpu"

# ── Dataset ──────────────────────────────────────────────────────────────────
class TracingDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.as_tensor(X, dtype=torch.float32)
        self.y = torch.as_tensor(y, dtype=torch.long)

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# ── Model ────────────────────────────────────────────────────────────────────
class CNN1D(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        self.conv1 = nn.Sequential(nn.Conv1d(1, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU())
        self.conv2 = nn.Sequential(nn.Conv1d(64, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU())
        self.conv3 = nn.Sequential(nn.Conv1d(64, 64, kernel_size=3, padding=1), nn.BatchNorm1d(64), nn.ReLU())
        self.gap = nn.AdaptiveAvgPool1d(1)
        self.fc  = nn.Linear(64, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)
        x = self.gap(x).squeeze(-1)
        return self.fc(x)

# ── Cross-validation ─────────────────────────────────────────────────────────
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=45)

# Arrays to collect predictions for every sample
oof_preds = np.zeros(len(y), dtype=int)   # out-of-fold predictions
oof_probs = np.zeros((len(y), num_classes), dtype=np.float32)  # probabilities

epochs = 20
fold_accs = []

for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
    print(f"\n{'='*40}")
    print(f"Fold {fold+1}/5")
    print(f"{'='*40}")

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    # Add channel dim for Conv1D: (N, 1, L)
    X_train_t = X_train[:, None, :]
    X_val_t   = X_val[:, None, :]

    # Class weights computed on this fold's training set
    classes = np.unique(y_train)
    class_weights =np.array([1.2, .7, 1.4])
    #class_weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    class_weights_t = torch.tensor(class_weights, dtype=torch.float32).to(device)

    # Loaders
    train_loader = DataLoader(TracingDataset(X_train_t, y_train), batch_size=32, shuffle=True)
    val_loader   = DataLoader(TracingDataset(X_val_t,   y_val),   batch_size=32, shuffle=False)

    # Fresh model + optimizer each fold
    model     = CNN1D(num_classes=num_classes).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights_t)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # Training loop
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0

        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(device), yb.to(device)
                correct += (model(xb).argmax(1) == yb).sum().item()
                total   += yb.size(0)

        print(f"  Epoch {epoch+1:02d} | Loss: {train_loss:.4f} | Val Acc: {correct/total:.3f}")

    # ── Collect OOF predictions for this fold ────────────────────────────
    model.eval()
    fold_preds = []
    fold_probs = []

    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(device)
            logits = model(xb)
            probs  = torch.softmax(logits, dim=1)
            preds  = logits.argmax(1)
            fold_preds.extend(preds.cpu().tolist())
            fold_probs.extend(probs.cpu().tolist())

    oof_preds[val_idx] = fold_preds
    oof_probs[val_idx] = fold_probs

    fold_acc = accuracy_score(y_val, fold_preds)
    fold_accs.append(fold_acc)
    print(f"  Fold {fold+1} Accuracy: {fold_acc:.3f}")

# ── Overall OOF metrics (predictions on entire dataset) ──────────────────────
print(f"\n{'='*40}")
print(f"Overall CV Accuracy: {np.mean(fold_accs):.3f} ± {np.std(fold_accs):.3f}")
print(f"OOF Accuracy (all samples): {accuracy_score(y, oof_preds):.3f}")
print(f"\nClassification Report:")
print(classification_report(y, oof_preds, target_names=le.classes_.astype(str)))
print(f"\nConfusion Matrix:")
print(confusion_matrix(y, oof_preds))

# ── oof_preds and oof_probs now contain predictions for every sample ──────────
# Attach back to original dataframe if needed
df["oof_pred"]  = le.inverse_transform(oof_preds)
df["oof_pred_encoded"] = oof_preds
for i, cls in enumerate(le.classes_):
    df[f"prob_{cls}"] = oof_probs[:, i]


# ── Attach OOF probs to ids dataframe ────────────────────────────────────────
ids = ids.reset_index(drop=True)   # ensure index alignment

ids["oof_pred"] = le.inverse_transform(oof_preds)
ids["oof_pred_encoded"] = oof_preds
for i, cls in enumerate(le.classes_):
    ids[f"prob_{cls}"] = oof_probs[:, i]    

ids.to_csv("ids_with_oof_predictions.csv", index=False)    