# Crop recommendation model - simple version
# Run from the project root:  python training/train_simple.py
# Needs: pip install pandas scikit-learn joblib
# Needs Crop_recommendation.csv in the root folder.

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib

# 1. Load the data
data = pd.read_csv("Crop_recommendation.csv")
print(data.head())
print("Rows and columns:", data.shape)
print("Missing values:", data.isnull().sum().sum())
print("Crops:", data["label"].nunique())

# 2. Separate inputs (X) and the answer (y)
X = data[["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]]
y = data["label"]

# 3. Split: 80% for learning, 20% kept hidden for the final test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. Train two models and compare them
tree = DecisionTreeClassifier(random_state=42)
tree.fit(X_train, y_train)
tree_accuracy = accuracy_score(y_test, tree.predict(X_test))
print("Decision Tree accuracy:", tree_accuracy)

forest = RandomForestClassifier(n_estimators=100, random_state=42)
forest.fit(X_train, y_train)
forest_accuracy = accuracy_score(y_test, forest.predict(X_test))
print("Random Forest accuracy:", forest_accuracy)

# 5. Keep the better model
if forest_accuracy >= tree_accuracy:
    best_model = forest
else:
    best_model = tree

# 6. Which crops get mixed up?
predictions = best_model.predict(X_test)
print(confusion_matrix(y_test, predictions))

# 7. Try one example: N, P, K, temperature, humidity, ph, rainfall
example = pd.DataFrame([[90, 42, 43, 21, 82, 6.5, 200]], columns=X.columns)
print("Recommended crop:", best_model.predict(example)[0])

# 8. Save the model so the app can use it later
joblib.dump(best_model, "crop_model.joblib")
print("Model saved as crop_model.joblib")