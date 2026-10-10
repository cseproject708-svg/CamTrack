import os

import cv2
import numpy as np
import onnxruntime as ort

from config import LIVENESS_MODEL_PATH
from model.onnx_providers import get_providers


class LivenessDetector:
    """CNN anti-spoof detector (MiniFASNetV2, ONNX).

    Input:  1x3x80x80 float32 BGR crop (scale 2.7 around the face center).
    Output: softmax over [print-attack, live, replay-attack].
    """

    def __init__(self, model_path=LIVENESS_MODEL_PATH, conf_threshold=0.5,
                 blur_threshold=12.0, force_cpu=False):
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Liveness model not found: {model_path}\n"
                "Download MiniFASNetV2.onnx into the liveness model folder first."
            )
        self.session = ort.InferenceSession(
            model_path, providers=get_providers(force_cpu)
        )
        self.input_name = self.session.get_inputs()[0].name
        self.conf_threshold = conf_threshold
        self.blur_threshold = blur_threshold
        self.classes = ["print", "live", "replay"]
        self.live_index = 1
        self._history = []

    @staticmethod
    def _transform(img_bgr, bbox):
        h, w = img_bgr.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        side = max(x2 - x1, y2 - y1)
        scale = 2.7
        crop_side = side * scale

        cx0 = int(cx - crop_side / 2)
        cy0 = int(cy - crop_side / 2)
        x1c, y1c = max(cx0, 0), max(cy0, 0)
        x2c, y2c = min(cx0 + int(crop_side), w), min(cy0 + int(crop_side), h)

        crop = img_bgr[y1c:y2c, x1c:x2c]

        # Pad missing area when the 2.7x crop extends beyond image borders.
        # cx0/cy0 can be negative -> that many pixels are missing on top/left.
        pad_top = max(-cy0, 0)
        pad_left = max(-cx0, 0)
        pad_bottom = max(int(crop_side) - (y2c - y1c) - pad_top, 0)
        pad_right = max(int(crop_side) - (x2c - x1c) - pad_left, 0)
        crop = cv2.copyMakeBorder(
            crop,
            pad_top, pad_bottom, pad_left, pad_right,
            cv2.BORDER_REPLICATE,
        )

        crop = cv2.resize(crop, (80, 80), interpolation=cv2.INTER_AREA)
        crop = crop.astype(np.float32)
        crop = crop.transpose(2, 0, 1)[None]  # 1,3,80,80
        return crop

    @staticmethod
    def _softmax(x):
        x = np.asarray(x, dtype=np.float32)
        x = x - x.max()
        e = np.exp(x)
        return e / e.sum()

    def _run_single(self, img_bgr, bbox):
        inp = self._transform(img_bgr, bbox)
        out = self.session.run(None, {self.input_name: inp})[0]
        probs = self._softmax(out[0])

        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1c, y1c = max(0, x1), max(0, y1)
        x2c, y2c = min(img_bgr.shape[1], x2), min(img_bgr.shape[0], y2)
        face_crop = img_bgr[y1c:y2c, x1c:x2c]
        if face_crop.size == 0:
            return bool(int(np.argmax(probs)) == self.live_index), probs

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        # Fixed 112x112 size so the metric is comparable whether the face
        # is 100px (far camera) or 400px (gate close-up). The old code
        # measured at native size, so the same blur scored 444 on a 128px
        # test image but ~6 on a 640x480 webcam frame.
        gray_fixed = cv2.resize(gray, (112, 112), interpolation=cv2.INTER_AREA)
        laplacian_var = cv2.Laplacian(gray_fixed, cv2.CV_64F).var()

        model_live = int(np.argmax(probs)) == self.live_index
        model_conf = float(probs[self.live_index])

        is_live = model_live and model_conf >= self.conf_threshold

        # Blur veto: only for clearly out-of-focus faces with marginal
        # model confidence — never override a confident live prediction.
        if laplacian_var < self.blur_threshold and model_conf < 0.85:
            is_live = False

        return bool(is_live), probs

    def reset(self):
        """Clear temporal history (call when camera/face changes)."""
        self._history.clear()

    def predict(self, img_bgr, bbox, smooth=True):
        """Return (is_live, probs).

        Args:
            smooth: if True, apply 3-frame temporal smoothing (for video
                streams of the SAME face). If False, return the single-frame
                result (for stateless REST APIs where each request may be a
                different person/camera).
        """
        is_live, probs = self._run_single(img_bgr, bbox)

        if not smooth:
            return bool(is_live), probs

        self._history.append(is_live)
        if len(self._history) > 3:
            self._history.pop(0)

        live_count = sum(self._history)
        final_is_live = live_count >= 2

        return bool(final_is_live), probs
