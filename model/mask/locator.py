import cv2
import numpy as np


def _landmarks(face):
    """Return a (N,2) float32 landmark array if available, else None."""
    for attr in ("landmark_2d_106", "landmark"):
        lm = getattr(face, attr, None)
        if lm is not None and len(lm):
            arr = np.asarray(lm, dtype=np.float32)
            if arr.ndim == 2 and arr.shape[1] == 2:
                return arr
    return None


def get_mask_polygon(face, img_shape):
    """Build the polygon covering the lower face (surgical-mask area).

    Uses the 5-point kps for the eye line and the 106-landmark face outline
    (indices 0..32) traced down to the chin, closed across the nose bridge.
    """
    h, w = img_shape[:2]
    kps = np.asarray(face.kps, dtype=np.float32)
    bbox = [float(v) for v in face.bbox]
    x1, y1, x2, y2 = bbox
    fw, fh = x2 - x1, y2 - y1

    eyes_y = float((kps[0][1] + kps[1][1]) / 2.0)
    top_y = eyes_y + 0.40 * fh  # below the eyes, at the nose bridge

    pts = _landmarks(face)
    if pts is not None and pts.shape[0] >= 33:
        contour = pts[0:33]
        cx = (x1 + x2) / 2.0
        left = sorted(
            [(float(p[0]), float(p[1])) for p in contour if p[0] <= cx and p[1] >= top_y],
            key=lambda q: q[1],
        )
        right = sorted(
            [(float(p[0]), float(p[1])) for p in contour if p[0] > cx and p[1] >= top_y],
            key=lambda q: q[1],
        )
        bottom = [
            (float(p[0]), float(p[1]))
            for p in contour
            if p[1] >= y2 - 0.25 * fh
        ]
        bottom_sorted = sorted(bottom, key=lambda q: q[0])
        poly = left + bottom_sorted + list(reversed(right))
    else:
        poly = [
            (x1 + 0.12 * fw, top_y),
            (x2 - 0.12 * fw, top_y),
            (x2 - 0.15 * fw, y2 - 0.04 * fh),
            (x1 + 0.15 * fw, y2 - 0.04 * fh),
        ]

    poly = np.asarray(poly, dtype=np.float32)
    poly = np.clip(poly, [0, 0], [w - 1, h - 1])
    return poly


def create_mask_image(img_shape, polygon, feather=31):
    """Return a uint8 0/255 mask image (255 = mask region), feathered edges."""
    mask = np.zeros(img_shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [polygon.astype(np.int32)], 255)
    if feather and feather > 1:
        mask = cv2.GaussianBlur(mask, (feather, feather), 0)
    return mask


def apply_synthetic_mask(img_bgr, polygon, color=(85, 88, 105)):
    """Return a copy of the image with a dark surgical-mask overlay on the
    lower face (used to synthesise masked training samples)."""
    out = img_bgr.copy()
    cv2.fillPoly(out, [polygon.astype(np.int32)], color)
    return out
