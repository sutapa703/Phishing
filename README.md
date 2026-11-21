# Phishing classifier

**Production:** https://phishing-classifier-beryl.vercel.app



[Excel guide](outputs/01a0d231-c27f-7a63-ae8f-2e76b708f517/Phishing_Classifier_Guide.xlsx) | [Setup, GitHub, and production instructions](docs/SETUP_AND_RELEASE_GUIDE.md)

[Technical change report](docs/TECHNICAL_CHANGE_REPORT.md) | [Deployment verification](docs/DEPLOYMENT_STATUS.md)

A local Flask application that classifies rows of encoded website features as `phishing` or `safe` and returns a downloadable CSV. The supplied model works without AWS credentials or MongoDB. This application accepts feature data, not raw website URLs.

## Run on Windows

Local training and legacy pickle export require **Python 3.11**. Production inference uses **Python 3.12** and the portable JSON model. The included pickle was trained with scikit-learn 1.3.2 and XGBoost 1.6.2, so the requirements deliberately preserve those versions. Python 3.14 is not supported by this dependency set.

From this folder (`phishing-classifier-main`, the inner folder containing `app.py`):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe app.py
```

If Python 3.11 is not installed, you can use uv:

```powershell
python -m pip install uv
python -m uv venv --python 3.11 .venv
python -m uv pip install --python .venv/Scripts/python.exe -r requirements-training.txt
.\.venv\Scripts\python.exe app.py
```

The web app now reads `models/model.json` and `models/metadata.json`. An environment has already been installed in `.venv` in this working copy. Start it with `./start.ps1`, or use the final command above. Open **http://127.0.0.1:8080**. The app uses Waitress; debug mode is disabled.

On Linux/macOS, create a Python 3.11 environment and use `.venv/bin/python` instead.

## Make predictions

1. Download the sample from the home page, or use `examples/prediction_sample.csv`.
2. Upload a CSV with the 30 feature names in `config/training_schema.json`, excluding `Result`.
3. Download the returned `predicted_file.csv`. It preserves feature rows and adds a `Result` column with `phishing` or `safe`.

Feature columns can arrive in any order; they are reordered to the model schema. Values must be encoded as -1, 0, or 1 using the original feature definitions. Missing feature values may be blank or `?` and are imputed by the saved preprocessor. Invalid columns, nonnumeric values, empty files, and uploads over 4 MB produce a visible error. Upload filenames are never used as filesystem paths. Prediction CSVs are generated in memory; the application does not save uploaded data or prediction results. Each request is limited to 30,000 rows and the output is limited to 4 MB.

Endpoints: `GET /`, `GET /predict`, `POST /predict` (multipart field `file`), `GET /sample`, and `GET /health`.

## Train a model

Supply genuinely labeled data with the same 30 features plus `Result`: **-1 = phishing, 1 = safe**. Both classes need at least five rows. The included prediction data does not contain ground-truth labels and must not be treated as a labeled training set.

```powershell
.\.venv\Scripts\python.exe train.py --data C:/data/training.csv
# Or a directory containing labeled CSV batches:
.\.venv\Scripts\python.exe train.py --data C:/data/batches
```

Each run copies and validates its input into a unique `artifacts` directory, uses a reproducible stratified 80/20 split, fits the imputer on training data, and compares three classifiers using training-set cross-validation. The held-out test set is evaluated only after model selection. Hyperparameters are in `config/model.yaml`. Runs below 50% test accuracy fail without replacing the active model. Successful runs save metrics and an artifact model, then atomically replace the local training `model.pkl`. To update the web app, export the XGBoost model with `scripts/export_model.py`, verify equivalence, and redeploy. Export currently supports XGBoost only; a GaussianNB or LogisticRegression winner requires an additional exporter. The deployment keeps using the previous exported model until export and deployment succeed. Back up that file before retraining if you want to retain the bundled model. A 50% acceptance threshold is a software guard, not evidence of production suitability.

Training is a CLI operation so opening a web page cannot trigger a long-running training job.

### Optional MongoDB source

Copy `.env.example` to `.env`, configure `MONGO_DB_URL` and optionally `MONGO_DATABASE_NAME`, then run `train.py` without `--data`. Alternatively, set `TRAINING_DATA_PATH` in `.env`. Connection attempts time out after five seconds. MongoDB is never contacted for prediction.

Optional settings: `HOST` (default `127.0.0.1`), `PORT` (default `8080`), and `MODEL_PATH` (default the bundled model). Use an absolute model path. Only load trusted model pickle files.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover the web routes, bundled-model inference, column reordering, missing-value handling, malformed uploads, upload limits, filename handling, temporary-output cleanup, and a complete local training/save/reload/predict cycle. The training test uses synthetic labels to check the pipeline; its score does not measure real-world phishing detection quality. Legacy XGBoost emits dependency deprecation warnings, which do not prevent predictions. Its Windows wheel also carries an old internal platform tag, so `uv pip check` may flag that upstream packaging issue; `pip check` and the runtime tests verify the installed dependency set and actual execution.

## Docker

```sh
docker build -f DockerFile -t phishing-classifier .
docker run --rm -p 8080:8080 phishing-classifier
```

The image does not require or copy a `.env` file. GitHub Actions installs dependencies and runs the tests. Vercel production deployment is configured; see the section below.

## Vercel production

Run these commands from the inner project folder containing `app.py` and `vercel.json`:

```powershell
# Existing trusted pickle -> portable XGBoost model + saved imputation values
.\.venv\Scripts\python.exe scripts/export_model.py

# Verify the production dependency environment
python -m uv venv --python 3.12 .venv-production
python -m uv pip install --python .venv-production/Scripts/python.exe -r requirements.txt pytest==8.3.5
.\.venv-production\Scripts\python.exe -m pytest -q

# Build a production candidate, inspect it, then assign production domains
vercel deploy --prod --skip-domain --yes --scope ayushxdev1s-projects
vercel curl /health --deployment <candidate-url>
vercel promote <candidate-url> --yes --scope ayushxdev1s-projects
```

Vercel detects `app.py` as a Flask application. `.python-version` selects Python 3.12; `requirements.txt` contains prediction dependencies. Linux uses the smaller `xgboost-cpu` package. Training dependencies are isolated in `requirements-training.txt` for Python 3.11. Static CSS is served from `public/static`. `.vercelignore` excludes secrets, local environments, notebooks, training datasets, the legacy pickle, logs, and test artifacts. Server logs go to stderr.

No database, AWS, or application secrets are required for production inference. `INFERENCE_MODEL_PATH` can override the portable model path; it defaults to `models/model.json` and expects `metadata.json` beside it. Each function has a 60-second execution limit. Request/output limits are 4 MB and the row limit is 30,000. Very large HTTP requests can be rejected by Vercel before Flask can render a friendly error.

Retraining runs locally. Validate and export a new model before redeploying. The code is stored in the private GitHub repository linked above. Deployment remains CLI-managed: GitHub push runs tests but does not automatically publish to Vercel. Follow the setup and release guide to deploy a candidate, verify it, and promote it. Do not commit `.env.local` or `.vercel` authentication/linkage files.

The original `model.pkl` is retained locally and has not been retrained or replaced during deployment preparation. See [the technical change report](docs/TECHNICAL_CHANGE_REPORT.md) for the rationale, verification evidence, and remaining limitations.
