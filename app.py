import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

from werkzeug.exceptions import HTTPException
from flask import Flask, jsonify, render_template, request, send_file
from src.constant import PROJECT_ROOT
from src.pipeline.predict_pipeline import PredictionPipeline
from src.schema import FEATURE_COLUMNS

app = Flask(__name__, static_folder='public/static', static_url_path='/static')
app.config['MAX_CONTENT_LENGTH'] = 4_000_000


@app.get('/')
@app.get('/predict')
def home():
    return render_template('prediction.html', features=FEATURE_COLUMNS)


@app.get('/health')
def health():
    return jsonify(status='ok')


@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    if request.path == '/predict':
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.get('/sample')
def sample():
    return send_file(PROJECT_ROOT / 'examples' / 'prediction_sample.csv', as_attachment=True)


@app.post('/predict')
def predict():
    try:
        result = PredictionPipeline(request).run_pipeline()
        return send_file(result.content, download_name=result.prediction_file_name,
                         mimetype='text/csv', as_attachment=True)
    except HTTPException:
        raise
    except ValueError as error:
        return render_template('prediction.html', error=str(error), features=FEATURE_COLUMNS), 400
    except FileNotFoundError as error:
        return render_template('prediction.html', error=str(error), features=FEATURE_COLUMNS), 503
    except Exception:
        app.logger.exception('Prediction failed')
        return render_template('prediction.html', error='Prediction failed. Check the server logs and model installation.', features=FEATURE_COLUMNS), 500


@app.errorhandler(413)
def upload_too_large(error):
    return render_template('prediction.html', error='The maximum upload size is 4 MB.', features=FEATURE_COLUMNS), 413


if __name__ == '__main__':
    from waitress import serve
    serve(app, host=os.getenv('HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8080')))
