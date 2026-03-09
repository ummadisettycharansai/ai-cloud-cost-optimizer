"""
ML Model Registry
Handles serialization (save/load) of trained ML models to disk using joblib.
Models are stored in the 'model_store/' directory relative to the backend root.
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    import joblib  # pyre-ignore[21]
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    logger.warning("joblib not installed. Model persistence disabled.")

MODEL_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "model_store")


class ModelRegistry:
    """
    Filesystem-backed model registry.
    In production this would be replaced by MLflow or AWS SageMaker Model Registry.
    """

    def __init__(self, store_dir: str = None):
        self.store_dir = store_dir or MODEL_STORE_DIR
        os.makedirs(self.store_dir, exist_ok=True)

    def _model_path(self, name: str) -> str:
        return os.path.join(self.store_dir, f"{name}.joblib")

    def save(self, name: str, model) -> bool:
        """Serialize a trained model to disk."""
        if not JOBLIB_AVAILABLE:
            logger.warning(f"Cannot save model '{name}': joblib not installed.")
            return False
        try:
            path = self._model_path(name)
            joblib.dump(model, path)
            logger.info(f"Model '{name}' saved to {path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to save model '{name}': {exc}")
            return False

    def load(self, name: str):
        """Deserialize a model from disk. Returns None if not found."""
        if not JOBLIB_AVAILABLE:
            return None
        path = self._model_path(name)
        if not os.path.exists(path):
            logger.warning(f"Model '{name}' not found at {path}.")
            return None
        try:
            model = joblib.load(path)
            logger.info(f"Model '{name}' loaded from {path}")
            return model
        except Exception as exc:
            logger.error(f"Failed to load model '{name}': {exc}")
            return None

    def list_models(self) -> list:
        """List all registered model names."""
        if not os.path.isdir(self.store_dir):
            return []
        return [
            f.replace(".joblib", "")
            for f in os.listdir(self.store_dir)
            if f.endswith(".joblib")
        ]

    def delete(self, name: str) -> bool:
        """Remove a model from the registry."""
        path = self._model_path(name)
        if os.path.exists(path):
            os.remove(path)
            logger.info(f"Model '{name}' deleted.")
            return True
        return False
