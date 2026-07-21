from sklearn.linear_model import LogisticRegression
def build_logistic(class_weight=None,seed=75):return LogisticRegression(C=1.0,class_weight=class_weight,max_iter=2000,random_state=seed)
