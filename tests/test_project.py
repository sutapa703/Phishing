from io import BytesIO
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from app import app
from src.constant import PROJECT_ROOT
from src.schema import FEATURE_COLUMNS, validate_dataframe
import importlib.util


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def sample():
    return pd.read_csv(PROJECT_ROOT / 'examples' / 'prediction_sample.csv')


def upload(client, frame, filename='features.csv'):
    return client.post('/predict', data={'file': (BytesIO(frame.to_csv(index=False).encode()), filename)})


def test_home_health_sample(client):
    assert b'Classify and download' in client.get('/').data
    assert client.get('/predict').status_code == 200
    assert client.get('/health').json == {'status': 'ok'}
    assert client.get('/sample').status_code == 200
    assert client.get('/train').status_code == 404


def test_bundled_model_download_and_column_order(client, sample):
    result = upload(client, sample)
    assert result.status_code == 200
    output = pd.read_csv(BytesIO(result.data))
    assert len(output) == len(sample)
    assert set(output.Result) <= {'phishing', 'safe'}
    assert 'attachment' in result.headers['Content-Disposition']
    reordered = upload(client, sample[sample.columns[::-1]])
    assert reordered.data == result.data


@pytest.mark.parametrize('data,filename', [(b'', 'empty.csv'), (b'hello', 'bad.csv'), (b'a,b\n1,2', 'bad.txt'), (b'\xff', 'bad.csv')])
def test_bad_upload(client, data, filename):
    assert client.post('/predict', data={'file': (BytesIO(data), filename)}).status_code == 400


def test_missing_upload(client):
    assert client.post('/predict').status_code == 400


@pytest.mark.parametrize('value', ['abc', float('inf'), 20])
def test_invalid_feature_value(client, sample, value):
    sample = sample.astype(object)
    sample.iloc[0, 0] = value
    assert upload(client, sample).status_code == 400


def test_missing_extra_and_empty_columns(client, sample):
    assert upload(client, sample.drop(columns=sample.columns[0])).status_code == 400
    assert upload(client, sample.assign(Result=1)).status_code == 400
    assert upload(client, sample.iloc[:0]).status_code == 400


def test_missing_features_imputed(client, sample):
    sample = sample.astype(object)
    sample.iloc[0, 0] = '?'
    assert upload(client, sample).status_code == 200


def test_path_traversal_filename_is_not_saved(client, sample, tmp_path):
    target = tmp_path / 'escaped.csv'
    assert upload(client, sample, str(target)).status_code == 200
    assert not target.exists()


def test_prediction_output_cleanup(client, sample):
    before = set((PROJECT_ROOT / 'predictions').glob('*.csv'))
    upload(client, sample)
    assert set((PROJECT_ROOT / 'predictions').glob('*.csv')) == before


def test_upload_limit(client, monkeypatch):
    monkeypatch.setitem(app.config, 'MAX_CONTENT_LENGTH', 100)
    assert client.post('/predict', data={'file': (BytesIO(b'x' * 200), 'big.csv')}).status_code == 413


def test_missing_model(client, sample, monkeypatch, tmp_path):
    monkeypatch.setattr('src.pipeline.predict_pipeline.MODEL_PATH', tmp_path / 'missing.pkl')
    assert upload(client, sample).status_code == 503


def test_training_targets(sample):
    with pytest.raises(ValueError, match='-1 .* or 1'):
        validate_dataframe(pd.concat([sample] * 4).assign(Result=0), training=True)


@pytest.mark.skipif(importlib.util.find_spec('sklearn') is None, reason='Training environment only')
def test_train_save_reload_predict(tmp_path, monkeypatch):
    # Synthetic labeled features verify plumbing, not real-world model accuracy.
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(rng.choice([-1, 0, 1], size=(120, 30)), columns=FEATURE_COLUMNS)
    frame['Result'] = np.where(frame.iloc[:, 0] == -1, -1, 1)
    source = tmp_path / 'labeled.csv'
    frame.to_csv(source, index=False)
    target = tmp_path / 'trained.pkl'
    monkeypatch.setattr('src.components.model_trainer.MODEL_PATH', target)
    from src.pipeline.train_pipeline import TrainingPipeline
    pipeline = TrainingPipeline(source)
    pipeline.artifact_dir = tmp_path / 'artifacts'
    accuracy = pipeline.run_pipeline()
    assert accuracy >= 0.5
    from src.utils.main_utils import MainUtils
    model = MainUtils.load_object(str(target))
    assert set(model.predict(frame[FEATURE_COLUMNS])) <= {0, 1}
    report = json.loads((pipeline.artifact_dir / 'model.json').read_text())
    assert report['accuracy'] == accuracy
    assert report['test_rows'] == 24
    monkeypatch.setattr('src.pipeline.predict_pipeline.MODEL_PATH', target)
    assert upload(app.test_client(), frame[FEATURE_COLUMNS].head()).status_code == 200


@pytest.mark.skipif(importlib.util.find_spec('pymongo') is None, reason='Optional MongoDB training environment')
def test_mongodb_configuration_is_optional(monkeypatch):
    monkeypatch.delenv('MONGO_DB_URL', raising=False)
    from src.configuration.mongo_db_connection import MongoDBClient
    with pytest.raises(ValueError, match='--data'):
        MongoDBClient()
