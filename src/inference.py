"""Portable XGBoost inference, independent of training-time sklearn objects."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import numpy as np
import xgboost as xgb
from src.schema import FEATURE_COLUMNS


class PortableModel:
    def __init__(self, path):
        path = Path(path)
        metadata = json.loads(path.with_name('metadata.json').read_text(encoding='utf-8'))
        if metadata['features'] != FEATURE_COLUMNS:
            raise RuntimeError('The exported model schema does not match the application.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['model_sha256']:
            raise RuntimeError('The exported model checksum does not match its metadata.')
        self.statistics = np.asarray(metadata['imputation_values'], dtype=float)
        if self.statistics.shape != (len(FEATURE_COLUMNS),) or not np.isfinite(self.statistics).all():
            raise RuntimeError('The exported imputation values are invalid.')
        self.booster = xgb.Booster(params={'nthread': 1})
        self.booster.load_model(str(path))
        self.booster.set_param({'nthread': 1})
        self.iteration_end = metadata['iteration_end']

    def predict(self, frame):
        values = frame.to_numpy(dtype=float, copy=True)
        values = np.where(np.isnan(values), self.statistics, values)
        probabilities = self.booster.inplace_predict(values, iteration_range=(0, self.iteration_end))
        return (probabilities > 0.5).astype(int)


@lru_cache(maxsize=2)
def load_portable_model(path, modified_ns):
    # Timestamp invalidates a local cache after an artifact replacement.
    return PortableModel(path)
