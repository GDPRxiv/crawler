from pygdpr.services.metadata_service import MetadataService
from bs4 import BeautifulSoup
import nltk
import json
from collections import Counter
import heapq

# algorithm source: https://stackabuse.com/text-summarization-with-nltk-in-python/
# except: I don't discriminate against sentences longer than n words. NOT doing so
# provides a better result in this case.

class SummaryMetaService(MetadataService):
    def __init__(self, n_sentences=2):
        self.n_sentences = n_sentences
    def for_text(self, text):
        sentence_list = nltk.sent_tokenize(text)
        stopwords = set(nltk.corpus.stopwords.words('english'))
        words = nltk.word_tokenize(text)
        # words = [w for w in words if w.isalpha()]
        words = [w for w in words if w not in stopwords]
        word_frequencies = dict(Counter(words))
        maximum_frequncy = max(word_frequencies.values())
        for word in word_frequencies.keys():
            word_frequencies[word] = (word_frequencies[word]/maximum_frequncy)
        sentence_scores = {}
        for sent in sentence_list:
            for word in nltk.word_tokenize(sent.lower()):
                if word in word_frequencies.keys():
                    if sent not in sentence_scores.keys():
                        sentence_scores[sent] = word_frequencies[word]
                    else:
                        sentence_scores[sent] += word_frequencies[word]
        summary_sentences = heapq.nlargest(self.n_sentences, sentence_scores, key=sentence_scores.get)
        summary = ' '.join(summary_sentences)
        return {
            'en': summary
        }
