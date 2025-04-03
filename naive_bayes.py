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

# Step 1: Load Reddit Data
def load_posts(folder): #TODO: Handle blank flairs
    data = []
    for txt_file in glob(os.path.join(folder, "post_*.txt")):
        with open(txt_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
            if len(lines) >= 2:
                flair = lines[0]
                print("")
                post = " ".join(lines[1:])
                data.append((post, flair))
    return data

# Step 2: Processing (Expanding Contractions -> Tokenizing -> Lemmatizing)
lemmatizer = WordNetLemmatizer()
tokenizer = RegexpTokenizer(r"[a-zA-Z0-9]+")

def preprocess(text):
    text = contractions.fix(text)
    tokens = tokenizer.tokenize(text.lower())
    lemmatized = [lemmatizer.lemmatize(token) for token in tokens]
    return " ".join(lemmatized)


def main():
    # Step 3: Create Model
    data_folder = '../reddit_scraper_results'
    raw_data = load_posts(data_folder)
    texts = [preprocess(text) for text, flair in raw_data]
    labels = [flair for _, flair in raw_data]

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )

    # Step 4: Create Pipeline
    clf_pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),  # unigrams & bigrams
        ('nb', MultinomialNB())
    ])

    # Step 5: Train Model
    clf_pipeline.fit(X_train, y_train)

    # Step 6: Evaluate Model
    y_pred = clf_pipeline.predict(X_test)
    print(classification_report(y_test, y_pred))

if __name__ == "__main__":
    main()
