from flask import Flask, request
from app_service import AppService
from pprint import *

app = Flask(__name__)
appService = AppService();


@app.route('/')
def home():
    return "Service is running."

@app.route('/api/glossary/terms', methods=['POST'])
def create_glossary_terms():
    request_data = request.get_json()
    appService.printer("Client Request", request_data)
    return appService.create_glossary_terms(request_data)

@app.route('/api/glossary/terms', methods=['GET'])
def get_default_glossary_terms():
    return appService.get_default_glossary_terms()

@app.route('/api/assets', methods=['POST'])
def create_assets():
    request_data = request.get_json()
    appService.printer("Client Request", request_data)
    return appService.create_assets(request_data)

@app.route('/api/assets', methods=['DELETE'])
def delete_assets():
    request_data = request.get_json()
    appService.printer("Client Request", request_data)
    return appService.delete_assets(request_data)

@app.route('/api/scan', methods=['POST'])
def run_scan():
    request_data = request.get_json()
    appService.printer("Client Request", request_data)
    return appService.run_scan(request_data["dataSourceName"], request_data["scanName"])