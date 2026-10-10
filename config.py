import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OTHER_MODELS_DIR = os.path.join(BASE_DIR, "Other Models")

# 3 separate model folders
FACE_MODEL_DIR = os.path.join(OTHER_MODELS_DIR, "face_recognition")
LIVENESS_MODEL_DIR = os.path.join(OTHER_MODELS_DIR, "liveness")
MASK_MODEL_DIR = os.path.join(OTHER_MODELS_DIR, "mask")

# face recognition models
INSIGHTFACE_ROOT = FACE_MODEL_DIR  # FaceAnalysis(name='buffalo_l', root=...)
INSIGHTFACE_NAME = "buffalo_l"
SVM_FULL_PATH = os.path.join(FACE_MODEL_DIR, "svm.pkl")
SVM_MASK_PATH = os.path.join(FACE_MODEL_DIR, "svm_mask.pkl")
LABELS_PATH = os.path.join(FACE_MODEL_DIR, "labels.json")
EMBED_META_PATH = os.path.join(FACE_MODEL_DIR, "embed_meta.json")

# liveness (anti-spoof) model
LIVENESS_MODEL_PATH = os.path.join(LIVENESS_MODEL_DIR, "MiniFASNetV2.onnx")

# mask reconstruction model
LAMA_MODEL_PATH = os.path.join(MASK_MODEL_DIR, "lama_fp32.onnx")

# data
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# runtime
CONFIDENCE_THRESHOLD = 0.45
ENTRY_CONFIDENCE_THRESHOLD = 0.60

# dynamic-environment robustness
DETECTION_RETRY_ENHANCED = True  # retry app.get() on illumination-normalized frame
LIVENESS_SOFT_FALLBACK = True    # log high-confidence faces even if liveness fails
LIVENESS_MIN_CONF_FOR_SOFT = 0.75  # min recognition conf to soft-pass a liveness failure
AUGMENT_VARIANTS_FULL = 2  # extra lighting variants per image for svm.pkl training
AUGMENT_VARIANTS_MASK = 1  # extra lighting variants per image for svm_mask.pkl training


def ensure_dirs():
    for d in (FACE_MODEL_DIR, LIVENESS_MODEL_DIR, MASK_MODEL_DIR, OUTPUT_DIR):
        os.makedirs(d, exist_ok=True)
