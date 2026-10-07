from pathlib import Path
import joblib


def load_model():
    path = Path(__file__).resolve().parent.parent / "models" / "logistic_regression_model.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Model file not found at {path}")
    return joblib.load(path)

def classify(text:str):
    if not isinstance(text, str):
        raise ValueError("Input text must be a string.")
    model = load_model()
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_
    best_class_index = probabilities.argmax()
    confidence = probabilities[best_class_index]
    best_class = classes[best_class_index] if confidence >=0.35 else "other"
    return best_class, probabilities[best_class_index]