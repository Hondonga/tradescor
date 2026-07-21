from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
def calibrate_prefit(model,x,y,method):
    if method=="none":return model
    calibrated=CalibratedClassifierCV(FrozenEstimator(model),method=method);calibrated.fit(x,y);return calibrated
