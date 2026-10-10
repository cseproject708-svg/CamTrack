"""Photometric robustness for dynamic lighting / color conditions.

Covers: low light, overexposure, color casts (tube-light / daylight),
side shadows, and low contrast — without touching model weights.

- assess_frame()      -> lighting/contrast/cast/blur metrics + warnings
- normalize_illumination() -> gray-world white balance + adaptive gamma + CLAHE
- augment_photometric()    -> random lighting/color variants for SVM training
- enhance_for_detection()  -> retry path when the detector finds no face

Only depends on cv2 + numpy so it works on CPU-only installs.
"""

import cv2
import numpy as np

_rng = np.random.default_rng()


def assess_frame(img_bgr):
    """Return lighting quality metrics + human-readable warnings."""
    if img_bgr is None or img_bgr.size == 0:
        return {"brightness": 0.0, "contrast": 0.0, "color_cast": 0.0,
                "blur": 0.0, "warnings": ["no_frame"]}

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l_mean = float(np.mean(lab[:, :, 0]) * 100.0 / 255.0)  # 0..100

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    contrast = float(np.std(gray))

    mean_bgr = np.mean(img_bgr.reshape(-1, 3), axis=0)  # B,G,R
    color_cast = float(np.max(mean_bgr) - np.min(mean_bgr))

    # Fixed-size blur metric so it is comparable across resolutions.
    small = cv2.resize(gray, (320, 240), interpolation=cv2.INTER_AREA) \
        if max(gray.shape) > 320 else gray
    blur = float(cv2.Laplacian(small, cv2.CV_64F).var())

    warnings = []
    if l_mean < 20:
        warnings.append("too_dark")
    elif l_mean > 82:
        warnings.append("too_bright")
    if contrast < 25:
        warnings.append("low_contrast")
    if color_cast > 25:
        warnings.append("strong_color_cast")
    if blur < 12:
        warnings.append("blurry")

    return {"brightness": round(l_mean, 1), "contrast": round(contrast, 1),
            "color_cast": round(color_cast, 1), "blur": round(blur, 1),
            "warnings": warnings}


def _gray_world_white_balance(img_bgr):
    """Scale channels toward common gray (fixes tube-light yellow etc.)."""
    img = img_bgr.astype(np.float32)
    m = np.mean(img.reshape(-1, 3), axis=0) + 1e-6
    gray = float(np.mean(m))
    gains = np.clip(gray / m, 0.6, 1.6).astype(np.float32)
    out = np.clip(img * gains.reshape(1, 1, 3), 0, 255).astype(np.uint8)
    return out


def _adaptive_gamma(img_bgr, l_mean_100):
    # LUT exponent: <1 brightens shadows, >1 pulls back overexposure.
    if l_mean_100 < 30:
        gamma = 0.6
    elif l_mean_100 < 45:
        gamma = 0.75
    elif l_mean_100 > 85:
        gamma = 1.3  # pull back overexposure
    else:
        return img_bgr
    lut = np.array([((i / 255.0) ** gamma) * 255 for i in range(256)]).astype(np.uint8)
    return cv2.LUT(img_bgr, lut)


def normalize_illumination(img_bgr):
    """White-balance + adaptive gamma + CLAHE on L channel.

    Returns a uint8 BGR image of the same size. Safe to call on
    already-good frames (near no-op in the 60..80 brightness band
    with neutral color).
    """
    if img_bgr is None or img_bgr.size == 0:
        return img_bgr
    balanced = _gray_world_white_balance(img_bgr)

    lab = cv2.cvtColor(balanced, cv2.COLOR_BGR2LAB)
    l_mean = float(np.mean(lab[:, :, 0]) * 100.0 / 255.0)
    corrected = _adaptive_gamma(balanced, l_mean)

    lab = cv2.cvtColor(corrected, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def enhance_for_detection(img_bgr):
    """Retry-path enhancement when the detector finds no face."""
    return normalize_illumination(img_bgr)


def augment_photometric(img_bgr, rng=None):
    """Random lighting/color variant simulating dynamic environments.

    Applies: brightness 0.6-1.4x, contrast 0.7-1.3x, gamma 0.7-1.4,
    per-channel color shift ±25, 30% side-shadow gradient.
    Returns uint8 BGR of the same size.
    """
    if rng is None:
        rng = _rng
    img = img_bgr.astype(np.float32)

    # brightness + contrast around mid-gray
    b = float(rng.uniform(0.6, 1.4))
    c = float(rng.uniform(0.7, 1.3))
    img = ((img - 128.0) * c + 128.0) * b

    # gamma
    g = float(rng.uniform(0.7, 1.4))
    img = np.clip(img, 0, 255) / 255.0
    img = np.power(np.clip(img, 0, 1), g) * 255.0

    # color cast
    shift = rng.uniform(-25, 25, size=3).astype(np.float32)
    img = img + shift.reshape(1, 1, 3)

    # occasional side shadow (window light from one side)
    if float(rng.random()) < 0.3:
        h, w = img.shape[:2]
        x = np.linspace(1.0, float(rng.uniform(0.35, 0.6)), w, dtype=np.float32)
        if bool(rng.integers(0, 2)):
            x = x[::-1]
        img = img * x.reshape(1, w, 1)

    return np.clip(img, 0, 255).astype(np.uint8)
