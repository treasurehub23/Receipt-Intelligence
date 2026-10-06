from pathlib import Path
import joblib

path = Path(__file__).resolve().parent / "models" / "logistic_regression_model.pkl"

def load_model():
    if not path.exists():
        raise FileNotFoundError(f"Model file not found at {path}")
    return joblib.load(path)

d