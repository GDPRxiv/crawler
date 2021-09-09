from pygdpr import GDPR
from google.cloud import translate_v2 as translate
service_account_json_path = 'INSERT_SERVICE_ACCOUNT_JSON_PATH'
translate_client = translate.Client.from_service_account_json(service_account_json_path)
gdpr = GDPR()
dpa = gdpr.get_dpa('GB')
dpa.set_translate_client(translate_client)
# added_docs = dpa.get_docs()
# print(dpa.extract_metadata(docs=["2c0e5fd0d8b43e9b08410e8defd6fdbb"]))
translated_docs = dpa.translate_docs(
    docs=["2c0e5fd0d8b43e9b08410e8defd6fdbb"],
    target_languages=['en']
)
print('translated-docs:', translated_docs)
