from datetime import datetime
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AWS_S3_BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME', '')
MONGO_DATABASE_NAME = os.getenv('MONGO_DATABASE_NAME', 'phising')
TARGET_COLUMN = 'Result'
MODEL_FILE_NAME = 'model'
MODEL_FILE_EXTENSION = '.pkl'
MODEL_PATH = Path(os.getenv('MODEL_PATH', str(PROJECT_ROOT / 'model.pkl'))).resolve()
artifact_folder = str(PROJECT_ROOT / 'artifacts' / datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
