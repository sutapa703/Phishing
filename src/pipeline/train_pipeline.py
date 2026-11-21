from pathlib import Path
from uuid import uuid4
from src.constant import PROJECT_ROOT
from src.components.data_ingestion import DataIngestion
from src.components.data_validation import DataValidation
from src.components.data_transformation import DataTransformation
from src.components.model_trainer import ModelTrainer


class TrainingPipeline:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.artifact_dir = PROJECT_ROOT / 'artifacts' / uuid4().hex

    def run_pipeline(self):
        ingestion = DataIngestion(self.data_path)
        ingestion.data_ingestion_config.data_ingestion_dir = str(self.artifact_dir / 'raw')
        raw = ingestion.initiate_data_ingestion()
        validation = DataValidation(raw)
        validation.data_validation_config.valid_data_dir = str(self.artifact_dir / 'validated')
        validated = validation.initiate_data_validation()
        transformation = DataTransformation(validated)
        transformation.data_transformation_config.transformed_object_file_path = str(self.artifact_dir / 'preprocessor.pkl')
        transformed = transformation.initiate_data_transformation()
        trainer = ModelTrainer()
        trainer.model_trainer_config.trained_model_path = str(self.artifact_dir / 'model.pkl')
        return trainer.initiate_model_trainer(*transformed)
