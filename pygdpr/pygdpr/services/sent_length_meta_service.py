from pygdpr.services.metadata_service import MetadataService
import nltk

class SentLengthMetaService(MetadataService):
    def for_text(self, text):
        return len(nltk.sent_tokenize(text))
