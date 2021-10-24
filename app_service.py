from azure.purview.catalog import PurviewCatalogClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
from pprint import *
import os
import json
import sys
import jmespath

class AppService:
    def __init__(self):
        self.CatalogClient = self.authenticate()
        
    def authenticate(self):
        account_endpoint = "https://{}.purview.azure.com".format(os.getenv('PURVIEW_NAME'))
        credential = DefaultAzureCredential()
        catalog_client = PurviewCatalogClient(endpoint=account_endpoint, credential=credential)
        return catalog_client

    def create_assets(self, json_payload):
        fullAsset = self.full_asset()  # Create a full asset

        # Creates assets from the JSON payload
        serverAsset = self.server_asset(json_payload["serverName"], json_payload["collectionId"])
        databaseAsset = self.database_asset(json_payload["serverName"], json_payload["collectionId"], json_payload["databaseName"])
        schemaAsset = self.schema_asset(json_payload["serverName"], json_payload["collectionId"], json_payload["databaseName"], json_payload["schemaName"])
        tableAsset = self.table_asset(json_payload["serverName"], json_payload["collectionId"], json_payload["databaseName"], json_payload["schemaName"], json_payload["table"]["name"])
        
        fullAsset["entities"] += [serverAsset, databaseAsset, schemaAsset, tableAsset]

        # Get list of terms for us to get the guids back
        terms = json.loads(self.get_default_glossary_terms(silent=True))

        # Append each column asset to the full asset
        for column in json_payload["table"]["columns"]:
            classificationGuid = jmespath.search("[?name=='{}']".format(column["classification"]), terms)[0]["guid"]
            columnAsset = self.column_asset(json_payload["serverName"], json_payload["collectionId"], json_payload["databaseName"], json_payload["schemaName"], json_payload["table"]["name"], column["name"], column["data_type"], column["classification"], classificationGuid)
            fullAsset["entities"] += [columnAsset]

        # Create the assets
        response = self.CatalogClient.entity.create_or_update_entities(entities=fullAsset)
        self.printer("Purview Response", response)
        return response

    def full_asset(self):
        asset = {
                    "entities": []
                }
        return asset

    def server_asset(self, serverName, collectionId):
        server = {
            "attributes": {
                "name": "{}.database.windows.net".format(serverName),
                "qualifiedName": "mssql://{}.database.windows.net".format(serverName)
            },
            "collectionId": collectionId,
            "status": "ACTIVE",
            "typeName": "azure_sql_server"
        }
        return server

    def database_asset(self, serverName, collectionId, databaseName):
        database = {
            "attributes": {
                "name": databaseName,
                "qualifiedName": "mssql://{}.database.windows.net/{}".format(serverName, databaseName)
            },
            "collectionId": collectionId,
            "status": "ACTIVE",
            "typeName": "azure_sql_db"
        }
        return database
    
    def schema_asset(self, serverName, collectionId, databaseName, schemaName):
        schema = {
            "attributes": {
                "name": schemaName,
                "qualifiedName": "mssql://{}.database.windows.net/{}/{}".format(serverName, databaseName, schemaName)
            },
            "collectionId": collectionId,
            "status": "ACTIVE",
            "typeName": "azure_sql_schema"
        }
        return schema
    
    def table_asset(self, serverName, collectionId, databaseName, schemaName, tableName):
        table = {
            "attributes": {
                "name": tableName,
                "objectType": "U ",
                "qualifiedName": "mssql://{}.database.windows.net/{}/dbo/{}".format(serverName, databaseName, tableName)
            },
            "collectionId": collectionId,
            "status": "ACTIVE",
            "typeName": "azure_sql_table"
        }
        return table

    def column_asset(self, serverName, collectionId, databaseName, schemaName, tableName, columnName, columnType, classificationName, classificationGuid):
        column = {
            "attributes": {
                "name": columnName,
                "data_type": columnType,
                "qualifiedName": "mssql://{}.database.windows.net/{}/{}/{}#{}".format(serverName, databaseName, schemaName, tableName, columnName)
            },
            "collectionId": collectionId,
            "status": "ACTIVE",
            "typeName": "azure_sql_column",
            "relationshipAttributes": {
                "meanings": [
                {
                    "displayText": classificationName,
                    "guid": classificationGuid
                }
            ]
            }
        }
        return column

    def run_scan(self, dataSourceName, scanName):
        # Call Purview CLI since the Python SDK can't call scans at the moment it seems
        cmd = "pv scan runScan --dataSourceName {} --scanName {}".format(dataSourceName, scanName)
        stream = os.popen(cmd)
        response = json.loads(stream.read())
        self.printer("Purview Response", response)
        return response

    def get_default_glossary_guid(self, silent = False):
        # Call Purview CLI since no payload file is involved
        cmd = "pv glossary read"
        stream = os.popen(cmd)
        response = json.loads(stream.read())
        guid = [x for x in response if x['qualifiedName'] == 'Glossary'][0].get('guid')
        
        if not silent:
            self.printer("Purview Response", guid)
        
        return guid

    def printer(self, RequestType, payload):
        print("\n" + "="*len(RequestType) + "\n" +
                "{}".format(RequestType) + "\n" +
                "="*len(RequestType) + "\n" +
                json.dumps(payload, indent=4, sort_keys=True) + "\n",
                file=sys.stderr)

    def create_glossary_terms(self, terms):
        guid = self.get_default_glossary_guid(silent=True)

        # Add in necessary fields to terms
        for term in terms:
            term['anchor'] = {'glossaryGuid': guid}
            term['status'] = "Approved"
        
        response = self.CatalogClient.glossary.create_glossary_terms(glossary_term=terms)
        self.printer("Purview Response", response)
        return json.dumps(response)

    def get_default_glossary_terms(self, silent = False):
        guid = self.get_default_glossary_guid(silent=True)
        response = self.CatalogClient.glossary.list_glossary_terms(glossary_guid=guid)
        if not silent:
            self.printer("Purview Response", response)
        return json.dumps(response)