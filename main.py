import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split, StratifiedKFold

from naive_bayes import resource_path, load_posts, preprocess, classify_user_input


def main():
    clf_pipeline = joblib.load(resource_path("model_pipeline.joblib"))

    classify_user_input(clf_pipeline)

if __name__ == '__main__':
    main()
