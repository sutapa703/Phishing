# Phishing classifier: technical change and deployment report

Date: 24 September 2026  
Production URL: https://phishing-classifier-beryl.vercel.app  
Project root: the inner `phishing-classifier-main` directory containing `app.py`.

## 1. Scope and outcome

The downloaded project contained a Flask UI, ML training pipeline, legacy serialized model, unlabeled feature CSV, and deployment scaffolding. It could not start reliably or run inference independently of the original author's cloud setup. Work first restored local operation, then adapted inference for Vercel while preserving the existing classifier.

The application accepts 30 encoded website features, validates and reorders them, imputes missing values, and returns a CSV with a `Result` column. It does not scan raw URLs. The original classifier was not retrained during deployment preparation. Its decisions were checked against a portable export before release.

There was no Git repository or remote in this downloaded working copy. This report records defects observed during inspection and the resulting implementation, rather than a commit-by-commit diff. Deployment used the authenticated Vercel CLI.

## 2. Original defects, changes, and technical reasons

| Area / files | Original problem | Implemented change and reason |
|---|---|---|
| Startup: `src/components/data_validation.py` | Imported `Path` from `env.Lib.pathlib`. | Removed the environment-specific import. Virtual environment directories are not application packages; this prevented startup. |
| Dependency installation | Many unused historical dependencies; essential ML versions were not fully pinned; default system Python was 3.14. | Created an isolated Python 3.11 training environment matching sklearn 1.3.2 and XGBoost 1.6.2. Serialized objects depend on library-specific internal state. |
| Prediction model access | Downloaded `model.pkl` from hard-coded S3 bucket `sensorpw` on every request. | Used the included local artifact, then a portable export for hosting. Prediction no longer needs another account's bucket, AWS credentials, or a network download. |
| CSV schema: `src/schema.py` | Passed data directly to the model without checking feature names, order, or values. | Enforced the 30-feature contract; reordered columns; rejected invalid values and missing, unexpected, or duplicate names. Correct shape alone does not guarantee correct positional features. |
| Missing values | Training and inference cleaning were inconsistent. | Normalize whitespace, blanks, `?`, and `na`; preserve the model's learned imputation values. Both paths must transform equivalent inputs consistently. |
| Upload/output paths | Used the uploaded filename as a server path and one shared prediction output filename. | Removed upload persistence and ultimately switched result generation to memory. This prevents filename traversal and cross-request output collisions. |
| Error handling: `app.py` | Re-raised input errors as server failures. | Added explanatory 400 responses, 413 for oversized requests, 503 for absent model files, and logged 500 responses for unexpected failures. Werkzeug HTTP exceptions are preserved rather than accidentally converted to 500. |
| UI | Home returned a JSON string; upload page referenced external assets and a missing script. | Added a usable home page, local CSS, sample CSV, schema help, and visible errors. The main workflow is accessible from `/`. |
| Output labels | Used misspelled `phising`. | Standardized downloaded labels to `phishing` and `safe`; internal classes remain 0 and 1. |
| Training ingestion | Required MongoDB and an extra database wrapper. | Added CSV/file-directory ingestion; retained optional direct PyMongo with a five-second server-selection timeout. Infrastructure used only for training no longer blocks inference. |
| Batch validation | Relied on brittle filename syntax and column count. | Validate actual schema, values, class labels, and minimum class counts. Validate all batches before saving validated outputs. Filename conventions cannot prove dataset correctness. |
| Data splitting | Oversampled before a random, unseeded train/test split. | Removed pre-split oversampling and used a seeded stratified 80/20 split. Oversampling before splitting can duplicate rows across partitions and inflate measured performance. |
| Model selection | Inconsistent method arguments, test-based candidate selection, oversized searches, and mismatched threshold messages. | Search three classifiers with training-set cross-validation, then evaluate the selected model once on held-out data. Use one consistent 0.5 acceptance threshold. |
| Model publication | Automatically uploaded trained model to S3. | Save local model and metrics, then atomically replace the local training artifact after acceptance. Local success no longer depends on AWS, and replacement cannot expose partial writes. |
| Training endpoint | A GET request could trigger model training. | Added `train.py`; removed web training. Visiting a URL must not launch a long-running state-changing job. |
| Logging/exception formatting | Created a directory named like a log file; assumed a traceback always existed. | Corrected formatting and switched production logging to stderr. Error reporting and import-time logging must not create additional failures. |
| CI, container, documentation | CI only echoed placeholders; Docker used Python 3.8 and required `.env`; almost no documentation. | Added executable tests, environment-specific CI jobs, Python 3.12 inference container setup, secret exclusions, and setup/training instructions. |

## 3. Production architecture

### 3.1 Separate training and prediction environments

Vercel currently documents Python 3.12, 3.13, and 3.14 support. The original pickle requires the recovered Python 3.11/sklearn 1.3.2/XGBoost 1.6.2 environment. During repair, loading it under a different XGBoost release produced a missing-attribute failure. A pickle is a snapshot of internal objects, not a stable cross-version model interchange format.

`requirements-training.txt` retains the legacy environment for training and export. Production `requirements.txt` contains Flask, NumPy, pandas, SciPy, dotenv, XGBoost 2.1.4, and Waitress for local serving. Linux installs `xgboost-cpu`, avoiding GPU libraries. sklearn, MongoDB, boto3, and training utilities are absent from the hosted inference dependency set. `.python-version` selects 3.12; use an explicit Python 3.11 environment for training.

### 3.2 Portable export and model equivalence

`scripts/export_model.py` loads the trusted original pickle in its compatible environment and calls XGBoost's `save_model` API. It writes:

- `models/model.json`: native XGBoost trees and objective.
- `models/metadata.json`: feature order, learned most-frequent imputation values, iteration range, labels, and SHA-256 checksums.
- `models/export_validation.json`: export verification counts and hashes.

`src/inference.py` verifies model integrity and schema, checks the imputation vector, and loads a native Booster. It fills missing numeric values with the saved per-column statistics. The preserved iteration range and `probability > 0.5` rule reproduce the original classifier's decisions. A process-local cache avoids repeated model loading; file modification time invalidates it during local artifact replacement. One CPU thread per Booster avoids oversubscription under concurrent requests.

All **11,055** supplied feature rows produced identical classes before and after export. Another **100** all-missing-feature rows matched in the exporter check. A fixture stores the original expected class for every supplied row; Python 3.12 and remote deployment checks use that fixture. This proves agreement on tested inputs, not accuracy against ground-truth labels.

Source pickle SHA-256: `97df6c92cfed4c42478bffddb38a5d8d09a8cce240c74ecbb0140843ce04f267`.

Portable model SHA-256: `c712059aae62e8be449982e1cf7b4a9f2422a49d9bb208b2935c4df62c15e9c9`.

### 3.3 Stateless serverless requests

The local repair initially used unique temporary output files. Production now serializes CSV results into a per-request `BytesIO` buffer and returns it with Flask `send_file`. Application code does not persist uploads or prediction results. This avoids read-only deployment filesystem errors and collisions between simultaneous users. The multipart framework may internally spool uploads into temporary storage; that is distinct from application-managed durable storage.

Logging uses stderr, which the platform captures. Models and schemas are read-only deployment artifacts. Training stays outside the web runtime.

### 3.4 Resource limits

The local 10 MB limit was reduced because Vercel documents a 4.5 MB function request/response limit. The application caps requests and generated results at **4,000,000 bytes** and each batch at **30,000 rows**. Appending labels can enlarge output beyond upload size, so both directions are checked. Row/result limits return an explanatory 400 response; request limits return 413. Requests over the platform ceiling may be rejected before Flask renders an error.

`vercel.json` limits a function invocation to 60 seconds. This bounds execution; it does not guarantee latency under every workload.

### 3.5 Packaging and browser headers

Vercel detects the top-level Flask `app` in `app.py`. CSS lives under `public/static/css` for CDN delivery, with matching local Flask configuration. `.vercelignore` excludes environments, secrets, notebooks, raw datasets, pickle files, logs, tests, and artifacts. Function exclusions remove training modules.

Verification caught an ignore-pattern collision: `static/` also excluded `public/static`, causing a deployed stylesheet 404. The broad rule was removed. An earlier configuration validation rejected an exclusion expression over 256 characters; shortening it resolved that build-input error.

Responses include `nosniff`, frame denial, referrer policy, and a content security policy restricting resources/form submission to this app. Prediction responses use `Cache-Control: no-store`. These controls do not substitute for authentication, quotas, or model-quality evaluation.

## 4. Verification

| Check | Result |
|---|---|
| Initial local repair | 19 tests passed. |
| Final Python 3.11 training environment | 24 tests passed, including synthetic training/save/reload/web prediction. Legacy dependency deprecation warnings remain. |
| Python 3.12 production environment | 22 tests passed; 2 explicitly training-only tests skipped because sklearn/PyMongo are intentionally absent. |
| Export parity | 11,055/11,055 original classes matched; 100 all-missing-feature rows also matched. |
| Concurrent requests | Four requests using the same filename returned their own expected row counts. |
| Filesystem constraint | Prediction passed with directory creation forced to fail. |
| Input errors | Missing/malformed/empty upload, wrong columns/types/values, upload limit, and row limit covered. |
| Remote model parity | Vercel returned HTTP 200 and 11,055 matching classes. |
| Public endpoint/asset checks | See `production-verification.json`. |
| Deployment and runtime log evidence | See `DEPLOYMENT_STATUS.md`. |

The training test uses synthetic labels to verify plumbing, not real phishing accuracy. Docker execution was not verified because the local Docker engine was unavailable. GitHub Actions was configured but not executed remotely: no Git remote is connected.

## 5. Release, retraining, and rollback

1. Train locally with Python 3.11 and genuine labels: -1 for phishing, 1 for safe.
2. Inspect held-out metrics. The 0.5 acceptance threshold is only a basic software guard.
3. Export and verify an XGBoost winner. The exporter rejects other estimator types or unsupported preprocessing. GaussianNB/LogisticRegression need separate portable exporters before hosting.
4. Run both environment-specific test suites.
5. Deploy a candidate using `--prod --skip-domain`, verify with `vercel curl`, then promote the tested deployment.
6. Check the public production hostname, CSS, sample download, prediction output, and runtime error logs.
7. For a future rollback, choose a previous verified compatible deployment and use Vercel's rollback operation. Model and metadata must be released together.

Existing deployment protection was retained. Protected deployment/team URLs are tested with `vercel curl`; the production alias is the user-facing URL. No application database or AWS credentials are needed for inference. The project is CLI-managed until connected to a Git repository.

## 6. Remaining limitations

- **Model quality:** the supplied feature CSV has no ground-truth labels. No claims can be made here about real-world precision, recall, calibration, or current phishing coverage.
- **Feature extraction:** the app accepts encoded features, not raw URLs; it does not crawl websites or query DNS.
- **Training evaluation:** the imputer is fitted on the outer training partition before inner cross-validation. Held-out test data remains isolated, but preprocessing is shared across inner folds. A future refinement should put preprocessing inside each cross-validation estimator pipeline. Random splits also do not establish domain/time independence; group-aware or temporal validation may be needed.
- **Public-service controls:** input/execution bounds exist, but no application login, per-user quota, or custom rate limiter was added. Sustained-load and abuse testing were not performed.
- **Observability:** runtime logs are available; no external error tracker, log drain, scheduled uptime check, or long-term alerting integration was configured. A clean log sample is not continuous monitoring.
- **Release automation:** Git push deployment is not connected. The CI workflow becomes usable after the folder is committed to a repository.
- **Export scope:** the portable exporter supports the bundled XGBoost classifier with most-frequent imputation. Unsupported estimator changes fail explicitly.

## 7. References

- [Vercel Flask deployment and static assets](https://vercel.com/docs/frameworks/backend/flask)
- [Vercel Python runtime, versions, and packaging](https://vercel.com/docs/functions/runtimes/python)
- [Vercel function payload and execution limits](https://vercel.com/docs/functions/limitations)
- [XGBoost serialization and compatibility](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html)

References were checked during deployment. Current documentation and actual build/runtime results took precedence where local skill examples differed.
