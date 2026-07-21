from __future__ import annotations
import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score,balanced_accuracy_score,precision_score,recall_score,f1_score,matthews_corrcoef,confusion_matrix,log_loss,brier_score_loss

def expected_calibration_error(y,p,bins=10):
    edges=np.linspace(0,1,bins+1);total=0.0
    for low,high in zip(edges[:-1],edges[1:]):
        mask=(p>=low)&(p<(high if high<1 else high+1e-9))
        if mask.any():total+=mask.mean()*abs(y[mask].mean()-p[mask].mean())
    return float(total)
def classification_metrics(y,p,threshold=.5):
    y=np.asarray(y);p=np.asarray(p);pred=(p>=threshold).astype(int);tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {"pr_auc":float(average_precision_score(y,p)),"roc_auc":float(roc_auc_score(y,p)),"balanced_accuracy":float(balanced_accuracy_score(y,pred)),"precision":float(precision_score(y,pred,zero_division=0)),"recall":float(recall_score(y,pred,zero_division=0)),"f1":float(f1_score(y,pred,zero_division=0)),"specificity":float(tn/max(tn+fp,1)),"mcc":float(matthews_corrcoef(y,pred)),"confusion_matrix":[[int(tn),int(fp)],[int(fn),int(tp)]],"log_loss":float(log_loss(y,p,labels=[0,1])),"brier_score":float(brier_score_loss(y,p)),"ece":expected_calibration_error(y,p)}
