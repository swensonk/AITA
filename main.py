import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split, StratifiedKFold

from naive_bayes import resource_path, load_posts, preprocess, classify_user_input


def main():
    data_path = resource_path('data/reddit_scraper_results')
    raw_data = load_posts(data_path)
    texts = [preprocess(text) for text, flair in raw_data]
    labels = [flair for _, flair in raw_data]


    X_trainval, X_test, y_trainval, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=42
    )
    skf = StratifiedKFold(n_splits=5)
    all_reports = []

    X_np = np.array(X_trainval)
    y_np = np.array(y_trainval)
    clf_pipeline = joblib.load("model_pipeline.joblib")
    for train_idx, val_idx in skf.split(X_np, y_np):
        X_train, X_val = X_np[train_idx], X_np[val_idx]
        y_train, y_val = y_np[train_idx], y_np[val_idx]
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

    classify_user_input(clf_pipeline)

if __name__ == '__main__':
    main()
