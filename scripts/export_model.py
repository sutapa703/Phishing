"""Run with the Python 3.11 training environment before deploying an XGBoost model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from src.utils.main_utils import MainUtils
from src.constant import PROJECT_ROOT
from src.schema import FEATURE_COLUMNS, validate_dataframe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=PROJECT_ROOT / 'model.pkl')
    parser.add_argument('--data', type=Path, default=PROJECT_ROOT / 'prediction_artifacts' / 'phisingtest.csv')
    parser.add_argument('--output', type=Path, default=PROJECT_ROOT / 'models')
    args = parser.parse_args()
    model = MainUtils.load_object(str(args.model))
    estimator = model.trained_model_object
    if type(estimator).__name__ != 'XGBClassifier':
        raise ValueError('This exporter supports XGBClassifier only; other selected estimators need a separate exporter.')
    preprocessor = model.preprocessing_object
    if preprocessor.strategy != 'most_frequent' or preprocessor.add_indicator:
        raise ValueError('Unsupported preprocessing configuration.')
    features = list(preprocessor.feature_names_in_)
    if features != FEATURE_COLUMNS:
        raise ValueError('Training feature order differs from the application schema.')
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / 'model.json'
    estimator.get_booster().save_model(str(target))
    metadata = {'format_version': 1, 'features': features,
                'imputation_values': preprocessor.statistics_.tolist(),
                'iteration_end': int(estimator.best_iteration + 1),
                'model_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'source_pickle_sha256': hashlib.sha256(args.model.read_bytes()).hexdigest(),
                'labels': {'0': 'phishing', '1': 'safe'}}
    (args.output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    from src.inference import PortableModel
    frame = validate_dataframe(pd.read_csv(args.data))
    portable = PortableModel(target)
    expected = model.predict(frame)
    actual = portable.predict(frame)
    assert np.array_equal(expected, actual), 'Export changed predictions'
    # Verify all missing-value columns in addition to supplied complete rows.
    missing = frame.head(100).astype(float).copy()
    missing.iloc[:, :] = np.nan
    assert np.array_equal(model.predict(missing), portable.predict(missing))
    report = {'rows': len(frame), 'matching_predictions': int((expected == actual).sum()),
              'missing_value_rows': len(missing), 'source_model_sha256': metadata['source_pickle_sha256'],
              'portable_model_sha256': metadata['model_sha256']}
    (args.output / 'export_validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
