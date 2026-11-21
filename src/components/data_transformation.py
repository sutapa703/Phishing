from pathlib import Path
from dataclasses import dataclass
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from src.constant import artifact_folder, TARGET_COLUMN
from src.schema import validate_dataframe
from src.utils.main_utils import MainUtils


@dataclass
class DataTransformationConfig:
    data_transformation_dir: str = str(Path(artifact_folder) / 'data_transformation')
    transformed_object_file_path: str = str(Path(data_transformation_dir) / 'preprocessing.pkl')


class DataTransformation:
    def __init__(self, valid_data_dir):
        self.valid_data_dir = valid_data_dir
        self.data_transformation_config = DataTransformationConfig()
        self.utils = MainUtils()

    @staticmethod
    def get_merged_batch_data(valid_data_dir):
        frames = [pd.read_csv(path) for path in sorted(Path(valid_data_dir).glob('*.csv'))]
        if not frames:
            raise ValueError('No validated training files were found.')
        return pd.concat(frames, ignore_index=True)

    def initiate_data_transformation(self):
        frame = validate_dataframe(self.get_merged_batch_data(self.valid_data_dir), training=True)
        X = frame.drop(columns=TARGET_COLUMN)
        y = (frame[TARGET_COLUMN] == 1).astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y)
        preprocessor = SimpleImputer(strategy='most_frequent', keep_empty_features=True)
        train = preprocessor.fit_transform(X_train)
        test = preprocessor.transform(X_test)
        path = self.data_transformation_config.transformed_object_file_path
        self.utils.save_object(path, preprocessor)
        return train, y_train, test, y_test, path
