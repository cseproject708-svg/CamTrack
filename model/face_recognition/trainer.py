"""
trainer.py - Face Recognition SVM Training

Trains two SVM classifiers for face recognition:
  1. svm_full  - trained on unmasked face embeddings
  2. svm_mask  - trained on synthetically masked face embeddings

Both use InsightFace buffalo_l for 512-d embeddings and RBF SVM for classification.
The dual-classifier approach ensures recognition works with or without face masks.

Outputs (saved to Other Models/face_recognition/):
  - svm.pkl          full-face classifier
  - svm_mask.pkl     mask-robust classifier
  - labels.json      person names + model metadata
  - embed_meta.json  training summary and accuracy metrics
"""

import json
import os
import pickle

import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score

from config import (
    DATASET_DIR,
    FACE_MODEL_DIR,
    INSIGHTFACE_NAME,
    INSIGHTFACE_ROOT,
    SVM_FULL_PATH,
    SVM_MASK_PATH,
    LABELS_PATH,
    EMBED_META_PATH,
    AUGMENT_VARIANTS_FULL,
    AUGMENT_VARIANTS_MASK,
    ensure_dirs,
)
from model.onnx_providers import get_insightface_providers
from model.mask.locator import get_mask_polygon, apply_synthetic_mask
from model.preprocessing import augment_photometric

# Cache files for incremental training — reuse previously computed embeddings
EMBED_CACHE_PATH = os.path.join(FACE_MODEL_DIR, "embeddings_cache.pkl")
MASK_CACHE_PATH = os.path.join(FACE_MODEL_DIR, "embeddings_mask_cache.pkl")


# ---------------------------------------------------------------------------
#  Helper functions
# ---------------------------------------------------------------------------

def _pad_image(img, margin=0.5):
    """Add border padding so faces near image edges get detected."""
    padding = int(max(img.shape[:2]) * margin)
    return cv2.copyMakeBorder(img, padding, padding, padding, padding,
                              cv2.BORDER_REPLICATE)


def _largest_face(faces):
    """Return the face with the largest bounding box area."""
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def _embed_image(app, img_bgr):
    """Embedding for the largest face in an in-memory BGR image."""
    if img_bgr is None or img_bgr.size == 0:
        return None
    padded = _pad_image(img_bgr)
    faces = app.get(padded)
    if not faces:
        return None
    return np.asarray(_largest_face(faces).normed_embedding, dtype=np.float32)


def _embed(app, image_path):
    """Compute a 512-d normed embedding for the largest face in an image.

    Returns None if the image can't be read or no face is found.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    return _embed_image(app, img)


def _embed_augmented(app, image_path, rng, masked=False):
    """Lighting/color-jittered variant embedding (dynamic-env robustness).

    Simulates what the gate camera sees under different lighting, white
    balance and shadows. Not cached — regenerated each retrain.
    Returns None if no face is found in the augmented image.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    aug = augment_photometric(img, rng=rng)
    if not masked:
        return _embed_image(app, aug)
    padded = _pad_image(aug)
    faces = app.get(padded)
    if not faces:
        return None
    face = _largest_face(faces)
    mask_polygon = get_mask_polygon(face, padded.shape)
    masked_image = apply_synthetic_mask(padded, mask_polygon)
    masked_faces = app.get(masked_image)
    if not masked_faces:
        return None
    return np.asarray(_largest_face(masked_faces).normed_embedding, dtype=np.float32)


def _embed_masked(app, image_path):
    """Synthesize a masked face variant, then compute its embedding.

    Simulates what the camera sees when a student wears a face mask.
    The lower half of the face is covered with a synthetic mask polygon,
    then the model extracts an embedding from the masked image.
    """
    img = cv2.imread(image_path)
    if img is None:
        return None

    padded = _pad_image(img)
    faces = app.get(padded)
    if not faces:
        return None

    face = _largest_face(faces)
    mask_polygon = get_mask_polygon(face, padded.shape)
    masked_image = apply_synthetic_mask(padded, mask_polygon)

    masked_faces = app.get(masked_image)
    if not masked_faces:
        return None

    return np.asarray(_largest_face(masked_faces).normed_embedding, dtype=np.float32)


# ---------------------------------------------------------------------------
#  Embedding cache (for incremental training)
# ---------------------------------------------------------------------------

def _load_cache(cache_path):
    """Load previously computed embeddings from disk."""
    if os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)
    return {"paths": [], "embeddings": [], "labels": []}


def _save_cache(cache, cache_path):
    """Save computed embeddings to disk for faster retraining."""
    with open(cache_path, "wb") as f:
        pickle.dump(cache, f)


def _collect_samples(persons):
    """Build a list of (image_path, label_index) tuples for all training images."""
    label_map = {name: idx for idx, name in enumerate(persons)}
    samples = []

    for person in persons:
        person_dir = os.path.join(DATASET_DIR, person)
        for filename in sorted(os.listdir(person_dir)):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                full_path = os.path.join(person_dir, filename)
                samples.append((full_path, label_map[person]))

    return samples


def _compute_new_embeddings(app, samples, cache, compute_fn):
    """Only compute embeddings for images not already in the cache.

    Returns (new_paths, new_embeddings, new_labels, skipped_count).
    """
    already_cached = set(cache["paths"])
    new_embeddings = []
    new_labels = []
    new_paths = []
    skipped = 0

    for path, label in samples:
        if path in already_cached:
            continue

        embedding = compute_fn(app, path)
        if embedding is None:
            skipped += 1
            continue

        new_embeddings.append(embedding)
        new_labels.append(label)
        new_paths.append(path)

    return new_paths, new_embeddings, new_labels, skipped


def _merge_with_cache(cache, new_paths, new_embeddings, new_labels):
    """Merge newly computed embeddings with cached ones."""
    all_paths = cache["paths"] + new_paths
    all_labels = cache["labels"] + new_labels

    old_embeddings = cache["embeddings"]
    if len(old_embeddings) > 0 and new_embeddings:
        all_embeddings = np.vstack([old_embeddings, np.vstack(new_embeddings)])
    elif new_embeddings:
        all_embeddings = np.vstack(new_embeddings)
    else:
        all_embeddings = old_embeddings

    return all_paths, all_embeddings, np.array(all_labels)


# ---------------------------------------------------------------------------
#  Main training pipeline
# ---------------------------------------------------------------------------

def train_all(det_size=640, force_cpu=True, incremental=True):
    """Train both SVM classifiers.

    Args:
        det_size: InsightFace detection size (larger = more accurate, slower).
        force_cpu: Force CPU inference instead of GPU.
        incremental: If True, reuse cached embeddings and only compute new ones.

    Returns:
        Summary dict with training results and accuracy metrics.

    Raises:
        ValueError: If fewer than 2 persons or 20 images are found.
    """
    ensure_dirs()

    # -- Discover persons and collect image paths --
    persons = sorted([
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ])
    if len(persons) < 2:
        raise ValueError(f"Need at least 2 persons in {DATASET_DIR}, found {len(persons)}")

    samples = _collect_samples(persons)
    if len(samples) < 20:
        raise ValueError(f"Need at least 20 total images, found {len(samples)}")

    # -- Load InsightFace model --
    providers = get_insightface_providers()
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name=INSIGHTFACE_NAME, root=INSIGHTFACE_ROOT, providers=providers)
    ctx_id = 0 if providers and providers[0] == "CUDAExecutionProvider" else -1
    app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))

    # -- Load or initialize embedding caches --
    if incremental:
        full_cache = _load_cache(EMBED_CACHE_PATH)
        mask_cache = _load_cache(MASK_CACHE_PATH)
    else:
        full_cache = {"paths": [], "embeddings": [], "labels": []}
        mask_cache = {"paths": [], "embeddings": [], "labels": []}

    # -- Compute full-face embeddings (only new images) --
    new_paths, new_embs, new_labels, skipped_full = _compute_new_embeddings(
        app, samples, full_cache, _embed
    )
    all_paths, all_embs, all_labels = _merge_with_cache(
        full_cache, new_paths, new_embs, new_labels
    )

    # -- Compute masked-face embeddings (only new images) --
    new_mpaths, new_mems, new_mlabels, skipped_mask = _compute_new_embeddings(
        app, samples, mask_cache, _embed_masked
    )
    all_mpaths, all_mems, all_mlabels = _merge_with_cache(
        mask_cache, new_mpaths, new_mems, new_mlabels
    )

    if len(all_embs) < 20:
        raise ValueError(f"Need at least 20 embeddings, got {len(all_embs)}")

    # -- Photometric augmentation (dynamic lighting/color robustness) --
    # Augmented variants are computed fresh each retrain (not cached) and
    # concatenated for SVM fitting only. InsightFace embeddings are already
    # fairly lighting-invariant, but this covers dark / overexposed /
    # color-cast / side-shadow cases the dataset doesn't contain.
    aug_rng = np.random.default_rng(42)
    aug_embs, aug_labels = [], []
    if AUGMENT_VARIANTS_FULL > 0:
        for path, label in samples:
            for _ in range(AUGMENT_VARIANTS_FULL):
                e = _embed_augmented(app, path, aug_rng, masked=False)
                if e is not None:
                    aug_embs.append(e)
                    aug_labels.append(label)
    aug_mems, aug_mlabels = [], []
    if AUGMENT_VARIANTS_MASK > 0:
        for path, label in samples:
            for _ in range(AUGMENT_VARIANTS_MASK):
                e = _embed_augmented(app, path, aug_rng, masked=True)
                if e is not None:
                    aug_mems.append(e)
                    aug_mlabels.append(label)
    if aug_embs:
        all_embs = np.vstack([all_embs, np.vstack(aug_embs)])
        all_labels = np.concatenate([all_labels, np.array(aug_labels)])
    if aug_mems:
        all_mems = np.vstack([all_mems, np.vstack(aug_mems)])
        all_mlabels = np.concatenate([all_mlabels, np.array(aug_mlabels)])

    # -- Train full-face SVM --
    min_per_class = min(np.bincount(all_labels, minlength=len(persons)))
    test_size = min(0.2, (min_per_class - 1) / max(len(all_labels), 1))
    test_size = max(test_size, 0.05)

    X_train, X_test, y_train, y_test = train_test_split(
        all_embs, all_labels, test_size=test_size,
        stratify=all_labels, random_state=42,
    )

    svm_full = SVC(C=10.0, kernel="rbf", gamma="scale", probability=True, random_state=42)
    svm_full.fit(X_train, y_train)
    accuracy_full = float(accuracy_score(y_test, svm_full.predict(X_test)))

    # -- Train mask-robust SVM --
    min_per_class_m = min(np.bincount(all_mlabels, minlength=len(persons)))
    test_size_m = min(0.2, (min_per_class_m - 1) / max(len(all_mlabels), 1))
    test_size_m = max(test_size_m, 0.05)

    Xm_train, Xm_test, ym_train, ym_test = train_test_split(
        all_mems, all_mlabels, test_size=test_size_m,
        stratify=all_mlabels, random_state=42,
    )

    svm_mask = SVC(C=10.0, kernel="rbf", gamma="scale", probability=True, random_state=42)
    svm_mask.fit(Xm_train, ym_train)
    accuracy_mask = float(accuracy_score(ym_test, svm_mask.predict(Xm_test)))

    # -- Save trained models --
    with open(SVM_FULL_PATH, "wb") as fh:
        pickle.dump(svm_full, fh)
    with open(SVM_MASK_PATH, "wb") as fh:
        pickle.dump(svm_mask, fh)

    with open(LABELS_PATH, "w") as fh:
        json.dump({
            "persons": persons,
            "model": "insightface-buffalo_l",
            "img_size": 112,
        }, fh, indent=2)

    # -- Save embedding caches for future incremental training --
    _save_cache({"paths": all_paths, "embeddings": all_embs, "labels": all_labels},
                EMBED_CACHE_PATH)
    _save_cache({"paths": all_mpaths, "embeddings": all_mems, "labels": all_mlabels},
                MASK_CACHE_PATH)

    # -- Save training metadata --
    meta = {
        "embedding_dim": int(all_embs.shape[1]),
        "n_persons": len(persons),
        "n_samples_full": int(len(all_embs)),
        "n_samples_masked": int(len(all_mems)),
        "n_new_computed": len(new_paths),
        "n_cached": len(all_paths) - len(new_paths),
        "n_augmented_full": int(len(aug_embs)),
        "n_augmented_masked": int(len(aug_mems)),
        "n_skipped": skipped_full,
        "accuracy_full": accuracy_full,
        "accuracy_mask": accuracy_mask,
        "persons": persons,
    }
    with open(EMBED_META_PATH, "w") as fh:
        json.dump(meta, fh, indent=2)

    return meta


def reset_cache():
    """Clear all cached embeddings.

    The next train_all() call will recompute everything from scratch.
    Useful when you've changed the dataset or want a clean retrain.
    """
    for cache_path in (EMBED_CACHE_PATH, MASK_CACHE_PATH):
        if os.path.exists(cache_path):
            os.remove(cache_path)
