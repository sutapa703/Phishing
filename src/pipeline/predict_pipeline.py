from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
import os
import pandas as pd
from src.constant import PROJECT_ROOT, TARGET_COLUMN
from src.schema import validate_dataframe
MODEL_PATH = Path(os.getenv("INFERENCE_MODEL_PATH", str(PROJECT_ROOT / "models" / "model.json")))


@dataclass
class PredictionFileDetail:
    content: BytesIO
    prediction_file_name: str = 'predicted_file.csv'


class PredictionPipeline:
    def __init__(self, request):
        self.request = request

    def predict(self, features):
        if not MODEL_PATH.is_file():
            raise FileNotFoundError('No trained model is available. Train a model first.')
        if MODEL_PATH.suffix == '.json':
            from src.inference import load_portable_model
            model = load_portable_model(str(MODEL_PATH), MODEL_PATH.stat().st_mtime_ns)
        else:
            if os.getenv('VERCEL'):
                raise RuntimeError('Production requires an exported JSON model.')
            from src.utils.main_utils import MainUtils
            model = MainUtils.load_object(str(MODEL_PATH))
        return model.predict(validate_dataframe(features))

    def run_pipeline(self):
        upload = self.request.files.get('file')
        if upload is None or not upload.filename:
            raise ValueError('Choose a CSV file to upload.')
        if Path(upload.filename).suffix.lower() != '.csv':
            raise ValueError('Only CSV files are supported.')
        try:
            frame = pd.read_csv(upload.stream)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
            raise ValueError('Upload a valid UTF-8 CSV with a header and data rows.') from error
        if len(frame) > 30000:
            raise ValueError('Upload at most 30,000 rows per request; split larger batches.')
        frame = validate_dataframe(frame)
        predictions = self.predict(frame)
        frame[TARGET_COLUMN] = pd.Series(predictions, index=frame.index).map({0: 'phishing', 1: 'safe'})
        if frame[TARGET_COLUMN].isna().any():
            raise RuntimeError('The model returned an unsupported class label.')
        content = frame.to_csv(index=False).encode('utf-8')
        if len(content) > 4_000_000:
            raise ValueError('The result exceeds 4 MB. Split the CSV into smaller batches.')
        return PredictionFileDetail(BytesIO(content))
