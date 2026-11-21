# Setup, GitHub, and production release guide

Repository: https://github.com/ayushbasak101/phishing-classifier (private).  
Production: https://phishing-classifier-beryl.vercel.app.

## What -1, 0, and 1 mean

These are encoded categories, not percentages or probabilities. For many feature columns, -1 is a phishing-like signal, 0 is an intermediate/suspicious signal where defined, and 1 is a legitimate-like signal. Many features are binary and do not use 0. The `Redirect` column is an exception: the released dataset uses 0/1 while the source document describes three risk bands, so its precise raw-condition mapping is not confirmed. `Request_URL` and `port` also have source inconsistencies documented in the workbook.

Keep the three contexts separate:

| Context | -1 | 0 | 1 |
|---|---|---|---|
| Input features | Usually phishing-like feature | Intermediate where defined; exceptions apply | Usually legitimate-like feature |
| Original training `Result` | Phishing | Not a valid training target | Safe/legitimate |
| Internal model prediction | Not emitted | Phishing | Safe |

The downloaded CSV writes the words `phishing` or `safe`. Blank fields and `?` mean missing inputs; zero is a real category and must not be treated as missing. No single feature decides the final class.

The feature names and every feature row in the supplied CSV exactly match the UCI 327 release. The workbook uses the UCI feature document and ARFF value domains, while preserving any contradictions rather than inventing an extraction rule. Source: https://archive.ics.uci.edu/dataset/327/phishing.

## How setup changed and why

| File or setting | Change | Technical reason |
|---|---|---|
| `setup.py` package name | `src` became `phishing-classifier` | Makes installed project metadata identifiable. The Python import package remains `src`. |
| `setup.py` Python constraint | `>=3.11,<3.12` | This legacy package entry describes the training/export environment. It is excluded from Vercel deployment, which uses requirements and `.python-version`. |
| `setup.py` dependencies | Still empty intentionally | Dependencies are explicitly installed from the correct requirements file. `pip install -e .` alone is insufficient. It is optional when running from the repository root. |
| `.python-version` | Python 3.12 | Selects the supported production runtime on Vercel. Use explicit Python 3.11 for legacy training. |
| `requirements-training.txt` | Original-compatible sklearn 1.3.2 / XGBoost 1.6.2 | Required to load the supplied pickle and train/export locally. |
| `requirements.txt` | Production XGBoost 2.1.4, CPU-only on Linux; no sklearn/MongoDB/boto3 | Smaller hosted inference runtime and compatibility with portable JSON models. |
| Model loading | Native model JSON plus imputation metadata | Removes pickle's library-version coupling from production. |
| Filesystem/logging | Results in memory, logs to stderr | Serverless deployments cannot rely on mutable project files or persistent local storage. |
| `public/static` | CSS served as deployment assets | Makes local and Vercel styles available at the same URL. |
| `vercel.json` | Flask entrypoint, exclusions, 60-second duration | Explicit runtime packaging and bounded requests. |
| `.gitignore` / `.vercelignore` | Exclude secrets, environments, and obsolete notebooks | Avoid publishing credentials and unnecessary local artifacts. |

The original author metadata in `setup.py` was retained. No ownership claim or new license for the inherited source code was invented.

## Fresh local setup

Run from the cloned repository root, where `app.py` lives. The repository root is the inner folder from the original downloaded archive.

```powershell
gh repo clone ayushbasak101/phishing-classifier
cd phishing-classifier
python -m pip install uv

# Production-like web environment
python -m uv venv --python 3.12 .venv-production
python -m uv pip install --python .venv-production/Scripts/python.exe -r requirements.txt pytest==8.3.5
.\.venv-production\Scripts\python.exe -m pytest -q
.\.venv-production\Scripts\python.exe app.py
```

Open http://127.0.0.1:8080. On Linux/macOS use `.venv-production/bin/python`.

For training/export, create a separate environment:

```powershell
python -m uv venv --python 3.11 .venv
python -m uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Do not install both dependency sets in one environment. Existing installations do not need to recreate their environments on every code change.

## Push changes to GitHub

```powershell
git switch -c docs/my-change
# Edit the relevant files, then run the appropriate tests.
git status --short
git diff
git add README.md docs
git diff --cached --stat
git commit -m "Document feature encodings and release workflow"
git push -u origin docs/my-change
gh pr create --base main --fill
```

The file list above is an example: stage the files actually changed. Do not force-push the main branch. Keep `.env*`, `.vercel`, virtual environments, caches, logs, and legacy upload notebooks out of commits. The old upload notebook contained a database connection string and is deliberately excluded from the repository. Its local copy was not deleted.

## Push to production

GitHub push and production deployment are separate operations. The repository runs tests on pushes and pull requests. Vercel Git integration has not been enabled by these instructions; a Git push alone does not publish the application.

For application/UI changes, keep the existing verified model files. Retrain/export only when intentionally changing the classifier. Export currently supports XGBoost only.

```powershell
# From the repository root, after tests pass:
vercel whoami
vercel link --yes --project phishing-classifier --scope ayushxdev1s-projects
vercel deploy --prod --skip-domain --yes --scope ayushxdev1s-projects
```

Copy the candidate URL printed by the deployment command. Replace `<candidate-url>` below with that actual URL; do not type angle brackets literally.

```powershell
vercel curl /health --deployment <candidate-url> --scope ayushxdev1s-projects
vercel curl /static/css/style.css --deployment <candidate-url> --scope ayushxdev1s-projects -- --fail --silent
vercel curl /predict --deployment <candidate-url> --scope ayushxdev1s-projects -- --fail-with-body -F file=@examples/prediction_sample.csv -o candidate-results.csv
```

Inspect the downloaded result and confirm the candidate works. Only then promote it:

```powershell
vercel promote <candidate-url> --yes --scope ayushxdev1s-projects
```

Verify the public production home page, `/health`, stylesheet, sample download, and a prediction. Check runtime errors in the Vercel dashboard. If a command fails, stop and fix it before promotion. Protected candidate URLs should be checked with `vercel curl`; do not disable deployment protection.

For future rollback, use a previous fully verified deployment. Do not choose the first historical candidate that lacked CSS. Release the model and its metadata together.

## References and limitations

- Full rationale and historical repair details: `docs/TECHNICAL_CHANGE_REPORT.md`.
- Verified deployment: `docs/DEPLOYMENT_STATUS.md`.
- Per-feature meanings and exceptions: `docs/feature_dictionary.json` and the Excel workbook.
- [Vercel Flask deployment](https://vercel.com/docs/frameworks/backend/flask).
- [Vercel CLI deployment](https://vercel.com/docs/cli/deploy).
- [XGBoost model formats](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).

Legacy feature rules describe the historical dataset. They are not current security guarantees. Zero is not universally suspicious, and a value of 1 does not independently prove a website is safe.
