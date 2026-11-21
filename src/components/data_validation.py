from pathlib import Path
from dataclasses import dataclass
import pandas as pd
from src.constant import artifact_folder
from src.schema import validate_dataframe


@dataclass
class DataValidationConfig:
    data_validation_dir: str = str(Path(artifact_folder) / 'data_validation')
    valid_data_dir: str = str(Path(data_validation_dir) / 'validated')
    invalid_data_dir: str = str(Path(data_validation_dir) / 'invalid')


class DataValidation:
    def __init__(self, raw_data_store_dir):
        self.raw_data_store_dir = Path(raw_data_store_dir)
        self.data_validation_config = DataValidationConfig()

    def initiate_data_validation(self):
        files = sorted(self.raw_data_store_dir.glob('*.csv'))
        if not files:
            raise ValueError('No training CSV files were found.')
        destination = Path(self.data_validation_config.valid_data_dir)
        destination.mkdir(parents=True, exist_ok=True)
        frames = []
        for path in files:
            # Check all files before saving any; do not silently train on a partial batch.
            frames.append((path.name, validate_dataframe(pd.read_csv(path), training=True)))
        for name, frame in frames:
            frame.to_csv(destination / name, index=False)
        return str(destination)
