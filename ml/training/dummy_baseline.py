from sklearn.dummy import DummyClassifier
def build_dummy_majority():return DummyClassifier(strategy="most_frequent")
def build_dummy_prior():return DummyClassifier(strategy="prior")
