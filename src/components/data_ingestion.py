from pathlib import Path
from dataclasses import dataclass
import os
import pandas as pd
from src.constant import artifact_folder, MONGO_DATABASE_NAME


@dataclass
class DataIngestionConfig:
    data_ingestion_dir: str = str(Path(artifact_folder) / 'data_ingestion')


class DataIngestion:
    def __init__(self, data_path=None):
        self.data_path = data_path or os.getenv('TRAINING_DATA_PATH')
        self.data_ingestion_config = DataIngestionConfig()

    def initiate_data_ingestion(self):
        destination = Path(self.data_ingestion_config.data_ingestion_dir)
        destination.mkdir(parents=True, exist_ok=True)
        if self.data_path:
            source = Path(self.data_path)
            files = sorted(source.glob('*.csv')) if source.is_dir() else [source]
            if not files or any(not path.is_file() for path in files):
                raise ValueError('The training data path must be a CSV file or directory containing CSV files.')
            for index, path in enumerate(files):
                pd.read_csv(path).to_csv(destination / f'batch_{index}.csv', index=False)
        else:
            from src.data_access.phising_data import PhisingData
            data = PhisingData(MONGO_DATABASE_NAME)
            for index, (_, frame) in enumerate(data.export_collections_as_dataframe()):
                frame.to_csv(destination / f'batch_{index}.csv', index=False)
        return str(destination)
