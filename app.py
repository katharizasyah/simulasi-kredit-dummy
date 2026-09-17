import hmac
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from calculator import simulate

load_dotenv(Path(__file__).with_name('.env'))

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(API_KEY=os.getenv('API_KEY', ''), MAX_CONTENT_LENGTH=16*1024)
    if test_config:
        app.config.update(test_config)
    if not app.config['API_KEY']:
        raise RuntimeError('Isi API_KEY di .env atau environment sebelum menjalankan API.')

    @app.before_request
    def authenticate():
        if request.path.startswith('/v1/'):
            supplied = request.headers.get('X-API-Key', '')
            if not hmac.compare_digest(supplied.encode(), app.config['API_KEY'].encode()):
                return jsonify(error={'code': 'unauthorized', 'message': 'API key tidak valid.'}), 401

    @app.errorhandler(ValueError)
    def validation_error(error):
        return jsonify(error={'code': 'validation_error', 'message': str(error)}), 422

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error={'code': error.name, 'message': error.description}), error.code

    @app.get('/health')
    def health():
        return jsonify(status='ok', is_dummy=True)

    @app.get('/openapi.json')
    def spec():
        return jsonify(openapi_spec())

    @app.post('/v1/simulations/credit')
    def credit():
        return jsonify(simulate(request.get_json(), 'kredit'))

    @app.post('/v1/simulations/budget')
    def budget():
        return jsonify(simulate(request.get_json(), 'budget'))
    return app

def openapi_spec():
    spec = json.loads(Path(__file__).with_name('openapi.json').read_text())
    url = os.getenv('PUBLIC_BASE_URL', 'https://YOUR-APP.azurewebsites.net').rstrip('/')
    parsed = urlparse(url)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError('PUBLIC_BASE_URL harus base URL HTTP(S) tanpa query atau fragment.')
    spec['servers'] = [{'url': url}]
    return spec

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--export-openapi', metavar='PATH')
    args = parser.parse_args()
    if args.export_openapi:
        Path(args.export_openapi).write_text(json.dumps(openapi_spec(), indent=2, ensure_ascii=False))
    else:
        from waitress import serve
        serve(create_app(), host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
