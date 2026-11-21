"""Fit candidates using training-only cross-validation, then evaluate once."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
from uuid import uuid4
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from xgboost import XGBClassifier
from src.constant import artifact_folder, PROJECT_ROOT, MODEL_PATH
from src.utils.main_utils import MainUtils


@dataclass
class ModelTrainerConfig:
    trained_model_path: str = str(Path(artifact_folder) / 'model_trainer' / 'model.pkl')
    model_config_file_path: str = str(PROJECT_ROOT / 'config' / 'model.yaml')
    expected_accuracy: float = 0.5


class VisibilityModel:
    # Keep this import path stable: the supplied pickle references it.
    def __init__(self, preprocessing_object, trained_model_object):
        self.preprocessing_object = preprocessing_object
        self.trained_model_object = trained_model_object

    def predict(self, X):
        return self.trained_model_object.predict(self.preprocessing_object.transform(X))


class ModelTrainer:
    def __init__(self):
        self.model_trainer_config = ModelTrainerConfig()
        self.utils = MainUtils()
        self.models = {
            'GaussianNB': GaussianNB(),
            'XGBClassifier': XGBClassifier(objective='binary:logistic', random_state=42, n_jobs=1),
            'LogisticRegression': LogisticRegression(max_iter=1000, random_state=42),
        }

    def initiate_model_trainer(self, x_train, y_train, x_test, y_test, preprocessor_path):
        config = self.utils.read_yaml_file(self.model_trainer_config.model_config_file_path)
        folds = min(5, int(np.unique(y_train, return_counts=True)[1].min()))
        if folds < 2:
            raise ValueError('Not enough training examples for cross-validation.')
        cv = StratifiedKFold(n_splits=folds, shuffle=True, random_state=42)
        candidates = []
        for name, estimator in self.models.items():
            params = config['model_selection']['model'][name]['search_param_grid']
            search = GridSearchCV(estimator, params, scoring='accuracy', cv=cv, n_jobs=1, error_score='raise')
            search.fit(x_train, y_train)
            candidates.append((float(search.best_score_), name, search.best_estimator_))
        cv_score, name, best_model = max(candidates, key=lambda item: item[0])
        predictions = best_model.predict(x_test)
        accuracy = float(accuracy_score(y_test, predictions))
        if accuracy < self.model_trainer_config.expected_accuracy:
            raise ValueError(f'Accuracy {accuracy:.3f} is below the required {self.model_trainer_config.expected_accuracy:.3f}.')
        model = VisibilityModel(self.utils.load_object(preprocessor_path), best_model)
        artifact = Path(self.model_trainer_config.trained_model_path)
        self.utils.save_object(str(artifact), model)
        metrics = {'model': name, 'accuracy': accuracy, 'cross_validation_accuracy': cv_score,
                   'test_rows': len(y_test), 'classification_report': classification_report(y_test, predictions, output_dict=True, zero_division=0)}
        artifact.with_suffix('.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = MODEL_PATH.with_name(f'.model-{uuid4().hex}.tmp')
        try:
            self.utils.save_object(str(temporary), model)
            os.replace(temporary, MODEL_PATH)
        finally:
            temporary.unlink(missing_ok=True)
        return accuracy
