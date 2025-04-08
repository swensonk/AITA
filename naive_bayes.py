import os
from glob import glob
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
import contractions

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from reddit_scrape import PostStore
import random
from collections import defaultdict

# Load Reddit Data
def load_posts(folder):
    data = []
    store = PostStore('../reddit_scraper_results')
    for id in store.keys():
        flair, contents = store.get(id)
        if flair in {"Not the A-hole", "Asshole", "Everyone Sucks", "No A-holes here"}:
            data.append((contents, flair))
    return data

# Processing (Expanding Contractions -> Tokenizing -> Lemmatizing)
lemmatizer = WordNetLemmatizer()
tokenizer = RegexpTokenizer(r"[a-zA-Z0-9]+")

def preprocess(text):
    text = contractions.fix(text)
    tokens = tokenizer.tokenize(text.lower())
    lemmatized = [lemmatizer.lemmatize(token) for token in tokens]
    return " ".join(lemmatized)

# Oversample
def oversample_dataset(data):
    label_buckets = defaultdict(list)
    for post, label in data:
        label_buckets[label].append((post, label))

    max_size = max(len(bucket) for bucket in label_buckets.values())
    
    balanced = []
    for label, bucket in label_buckets.items():
        if len(bucket) < max_size:
            # Duplicate samples to match max_size
            oversampled = random.choices(bucket, k=max_size - len(bucket))
            bucket += oversampled
        balanced.extend(bucket)

    random.shuffle(balanced)
    return balanced

def main():
    # Create Model
    data_folder = '../reddit_scraper_results'
    raw_data = load_posts(data_folder)
    raw_data = oversample_dataset(raw_data)
    texts = [preprocess(text) for text, flair in raw_data]
    labels = [flair for _, flair in raw_data]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    # Create Pipeline
    clf_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),  # unigrams (1, 1) - unigrams & bigrams (1, 2)
        ('nb', MultinomialNB())
    ])

    # Train Model
    clf_pipeline.fit(X_train, y_train)

    # Evaluate Model
    y_pred = clf_pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

if __name__ == "__main__":
    main()
