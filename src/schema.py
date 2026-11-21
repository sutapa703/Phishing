"""Shared validation for training and prediction CSV files."""
import json
import numpy as np
import pandas as pd
from src.constant import PROJECT_ROOT, TARGET_COLUMN

with (PROJECT_ROOT / 'config' / 'training_schema.json').open() as stream:
    FEATURE_COLUMNS = [name for name in json.load(stream)['ColName'] if name != TARGET_COLUMN]


def validate_dataframe(frame, training=False):
    frame = frame.copy()
    frame.columns = frame.columns.str.strip()
    expected = FEATURE_COLUMNS + ([TARGET_COLUMN] if training else [])
    if frame.empty:
        raise ValueError('The CSV must contain at least one data row.')
    if frame.columns.duplicated().any():
        raise ValueError('The CSV contains duplicate column names.')
    missing = sorted(set(expected) - set(frame.columns))
    extra = sorted(set(frame.columns) - set(expected))
    if missing or extra:
        raise ValueError(f'CSV columns do not match the schema. Missing: {missing}; unexpected: {extra}.')
    frame = frame[expected]
    for column in expected:
        values = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)
        values = values.replace({'?': np.nan, '': np.nan, 'na': np.nan})
        try:
            frame[column] = pd.to_numeric(values, errors='raise')
        except (TypeError, ValueError) as error:
            raise ValueError(f'Column {column} must contain numeric features, or ? for missing values.') from error
        if np.isinf(frame[column]).any():
            raise ValueError(f'Column {column} contains infinite values.')
        if not frame[column].dropna().isin([-1, 0, 1]).all():
            raise ValueError(f'Column {column} must use the encoded values -1, 0, or 1.')
        if training and frame[column].isna().all():
            raise ValueError(f'Column {column} has no usable values.')
    if training:
        target = frame[TARGET_COLUMN]
        if target.isna().any() or not target.isin([-1, 1]).all():
            raise ValueError('Training Result values must be -1 (phishing) or 1 (safe).')
        if target.nunique() != 2 or target.value_counts().min() < 5:
            raise ValueError('Training requires at least five examples of each class.')
    return frame
