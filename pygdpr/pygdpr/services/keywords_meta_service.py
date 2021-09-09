import re
import nltk
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
from nltk.tokenize import RegexpTokenizer
#nltk.download('wordnet')
from nltk.stem.wordnet import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from pygdpr.services.metadata_service import MetadataService

class KeywordsMetaService(MetadataService):
    def __init__(self, n_keywords=20, custom_stopwords=[]):
        self.n_keywords = n_keywords
        self.stopwords = set(stopwords.words("english")).union(custom_stopwords)
    def for_text(self, text, preprocess=True):
        if preprocess:
            text = re.sub('[^a-zA-Z]', ' ', text)
            #Convert to lowercase
            text = text.lower()
            #remove tags
            text = re.sub("&lt;/?.*?&gt;"," &lt;&gt; ", text)
            # remove special characters and digits
            text = re.sub("(\\d|\\W)+", " ", text)
            # Convert to list from string
            text = text.split()
            # Lemmatisation
            lem = WordNetLemmatizer()
            text = [lem.lemmatize(word) for word in text if not word in self.stopwords]
            tags = nltk.pos_tag(text)
            # print(tags)
            text = [word for word, pos in tags if (pos != 'RB')]
        try:
            corpus = text
            vec = CountVectorizer(analyzer='word', ngram_range=(1,3)).fit(corpus)
            bag_of_words = vec.transform(corpus)
            sum_words = bag_of_words.sum(axis=0)
            words_freq = [(word, sum_words[0, idx]) for word, idx in
                           vec.vocabulary_.items()]
            words_freq = sorted(words_freq, key = lambda x: x[1],
                               reverse=True)
            return {
                'en': [w for w, freq in words_freq[:self.n_keywords]]
            }
        except:
            return None
