import joblib
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)

# 1. Load dataset
df = pd.read_csv("Crop_recommendation.csv")

# 2. Define features and target
FEATURES = [
    "N", "P", "K", "temperature",
    "humidity", "ph", "rainfall"
]

X = df[FEATURES]
y = df["label"]

# 3. Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

# 4. Load trained model
model = joblib.load("crop_model.joblib")

# 5. Predict on test data
y_pred = model.predict(X_test)

# 6. Print accuracy
print("Model Accuracy:",
      round(accuracy_score(y_test, y_pred) * 100, 2), "%")

# 7. Classification report
print("\nClassification Report:\n")
print(classification_report(
    y_test,
    y_pred,
    zero_division=0
))

# 8. Generate confusion matrix
labels = sorted(y.unique())

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=labels
)

# 9. Plot confusion matrix
plt.figure(figsize=(16, 12))

sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    xticklabels=labels,
    yticklabels=labels
)

plt.title("AgriGuru AI - Crop Classification Confusion Matrix")
plt.xlabel("Predicted Crop")
plt.ylabel("Actual Crop")
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()

# Save image for your project report
plt.savefig("confusion_matrix.png", dpi=300, bbox_inches="tight")

plt.show()

print("\nConfusion matrix saved as confusion_matrix.png")