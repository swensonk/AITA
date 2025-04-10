import os
from glob import glob

import nltk.data
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
import contractions

from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from reddit_scrape import PostStore
import random
from collections import defaultdict
import numpy as np
import pandas as pd
import sys
from joblib import dump, load

nltk.data.path.append("nltk_data")
#Setting up data path
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# Load Reddit Data
def load_posts(folder):
    data = []
    data_path = resource_path('data/reddit_scraper_results')
    store = PostStore(data_path)
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
            oversampled = random.choices(bucket, k=max_size - len(bucket))
            bucket += oversampled
        balanced.extend(bucket)

    random.shuffle(balanced)
    return balanced

def classify_user_input(pipeline):
    print("\nEnter a Reddit AITA post (or type 'quit' to exit):\n")
    while True:
        user_input = input("Post: ")
        if user_input.lower() in {"quit", "exit"}:
            break
        cleaned_input = preprocess(user_input)
        prediction = pipeline.predict([cleaned_input])[0]
        confidence = np.max(pipeline.predict_proba([cleaned_input])[0])
        print(f"\nPredicted Flair: **{prediction}**")
        print(f"Confidence: {confidence:.3f}\n")


def main():
    # Create Model

    data_path = resource_path('data/reddit_scraper_results')
    raw_data = load_posts(data_path)
    raw_data = oversample_dataset(raw_data)
    texts = [preprocess(text) for text, flair in raw_data]
    labels = [flair for _, flair in raw_data]

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    # Create Pipeline
    clf_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),  # unigrams (1, 1) - unigrams & bigrams (1, 2)
        ('nb', MultinomialNB())
    ])
    skf = StratifiedKFold(n_splits=5)
    all_reports = []

    X_np = np.array(X_trainval)
    y_np = np.array(y_trainval)
    for train_idx, val_idx in skf.split(X_np, y_np):
        X_train, X_val = X_np[train_idx], X_np[val_idx]
        y_train, y_val = y_np[train_idx], y_np[val_idx]

        clf_pipeline.fit(X_train, y_train)
        y_pred = clf_pipeline.predict(X_val)

        report = classification_report(y_val, y_pred, output_dict=True)
        all_reports.append(report)

    df_reports = pd.DataFrame(all_reports)

    averages = {}

    for col in df_reports.columns:
        # Convert the list of dicts into a DataFrame
        metrics_df = pd.DataFrame(df_reports[col].tolist())
        # Calculate the mean for each metric
        averages[col] = metrics_df.mean()


    averages_df = pd.DataFrame(averages).T
    print(averages_df)
    dump(clf_pipeline, 'model_pipeline.joblib')
    classify_user_input(clf_pipeline)


if __name__ == "__main__":
    main()
