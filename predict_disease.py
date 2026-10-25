# Plant disease detection using a PRETRAINED model from Hugging Face
# No training needed.
#
# Install once:   pip install transformers torch pillow
# Run from the project root:   python scripts/predict_disease.py my_leaf.jpg

import sys
import csv
from transformers import pipeline
from PIL import Image

MODEL_NAME = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

# image_processor is borrowed from the base model (this fixes an earlier error)
classifier = pipeline("image-classification", model=MODEL_NAME,
                      image_processor="google/mobilenet_v2_1.0_224")

photo_path = sys.argv[1] if len(sys.argv) > 1 else "leaf.jpg"
image = Image.open(photo_path).convert("RGB")

results = classifier(image, top_k=3)
best = results[0]

print("\nPrediction for", photo_path)
if best["score"] < 0.60:
    print("Not sure. Please upload a clear, close photo of one leaf.")
    final_label = "NOT SURE"
else:
    print("Prediction:", best["label"], "-", round(best["score"] * 100, 1), "%")
    final_label = best["label"]

print("Other guesses:")
for r in results:
    print("  ", r["label"], "-", round(r["score"] * 100, 1), "%")

with open("results.csv", "a", newline="") as f:
    csv.writer(f).writerow([photo_path, final_label, round(best["score"] * 100, 1)])
print("Saved to results.csv")