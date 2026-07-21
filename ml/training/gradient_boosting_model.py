from sklearn.ensemble import HistGradientBoostingClassifier
def build_gradient_boosting(config,seed=75):return HistGradientBoostingClassifier(max_iter=config.get("max_iter",160),learning_rate=config.get("learning_rate",.05),max_leaf_nodes=config.get("max_leaf_nodes",15),l2_regularization=config.get("l2_regularization",1.0),early_stopping=True,random_state=seed)
