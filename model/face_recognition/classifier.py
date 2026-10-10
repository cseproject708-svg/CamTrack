import json
import os
import pickle

import numpy as np
from insightface.app import FaceAnalysis

from config import (
    CONFIDENCE_THRESHOLD,
    INSIGHTFACE_NAME,
    INSIGHTFACE_ROOT,
    LABELS_PATH,
    SVM_FULL_PATH,
    SVM_MASK_PATH,
)
from model.onnx_providers import get_insightface_providers


def load_models(det_size=320, force_cpu=False):
    """Load the InsightFace app + both SVM classifiers + person names."""
    if force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        providers = ["CPUExecutionProvider"]
        ctx_id = -1
    else:
        providers = get_insightface_providers()
        # CUDA provider needs ctx_id >= 0, CPU needs ctx_id == -1
        ctx_id = 0 if providers and providers[0] == "CUDAExecutionProvider" else -1
    app = FaceAnalysis(name=INSIGHTFACE_NAME, root=INSIGHTFACE_ROOT,
                       providers=providers)
    app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))

    with open(SVM_FULL_PATH, "rb") as fh:
        svm_full = pickle.load(fh)
    with open(SVM_MASK_PATH, "rb") as fh:
        svm_mask = pickle.load(fh)
    with open(LABELS_PATH, "r") as fh:
        persons = json.load(fh)["persons"]
    return app, svm_full, svm_mask, persons


def classify_detailed(svm_full, svm_mask, persons, emb, threshold=CONFIDENCE_THRESHOLD):
    """Predict with both SVMs, return (name, confidence, winning_classifier)."""
    p1 = svm_full.predict_proba(emb.reshape(1, -1))[0]
    p2 = svm_mask.predict_proba(emb.reshape(1, -1))[0]
    i1, i2 = int(np.argmax(p1)), int(np.argmax(p2))
    if p1[i1] >= p2[i2]:
        name, conf, via = persons[i1], float(p1[i1]), "full"
    else:
        name, conf, via = persons[i2], float(p2[i2]), "mask"
    if conf < threshold:
        return "Unknown", conf, via
    return name, conf, via
