import os
import onnxruntime as ort


def _cuda_works():
    """Check if CUDA execution provider works for basic ops (no cuDNN needed)."""
    try:
        so = ort.SessionOptions()
        so.log_severity_level = 3
        import numpy as np
        import onnx.helper as helper
        X = helper.make_tensor_value_info("X", 1, [1, 1])
        Y = helper.make_tensor_value_info("Y", 1, [1, 1])
        node = helper.make_node("Identity", inputs=["X"], outputs=["Y"])
        graph = helper.make_graph([node], "test", [X], [Y])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        ort.InferenceSession(model.SerializeToString(), so, providers=["CUDAExecutionProvider"])
        return True
    except Exception:
        return False


def _cudnn_works():
    """Check if cuDNN is available for Conv ops (needed by liveness/LaMa models)."""
    try:
        so = ort.SessionOptions()
        so.log_severity_level = 3
        import numpy as np
        import onnx.helper as helper
        X = helper.make_tensor_value_info("X", 1, [1, 1, 3, 3])
        Y = helper.make_tensor_value_info("Y", 1, [1, 1, 3, 3])
        W = helper.make_tensor_value_info("W", 1, [1, 1, 1, 1])
        node = helper.make_node("Conv", inputs=["X", "W"], outputs=["Y"])
        graph = helper.make_graph([node], "test", [X, Y], [W])
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        sess = ort.InferenceSession(model.SerializeToString(), so, providers=["CUDAExecutionProvider"])
        x_val = np.random.randn(1, 1, 3, 3).astype(np.float32)
        w_val = np.ones((1, 1, 1, 1), dtype=np.float32)
        sess.run(None, {"X": x_val, "W": w_val})
        return True
    except Exception:
        return False


_cuda_checked = None
_cuda_available = False
_cudnn_checked = None
_cudnn_available = False


def _ensure_cuda_checked():
    global _cuda_checked, _cuda_available
    if _cuda_checked is None:
        _cuda_checked = True
        _cuda_available = "CUDAExecutionProvider" in set(ort.get_available_providers()) and _cuda_works()
        if not _cuda_available:
            os.environ["CUDA_VISIBLE_DEVICES"] = ""
    return _cuda_available


def _ensure_cudnn_checked():
    global _cudnn_checked, _cudnn_available
    if _cudnn_checked is None:
        _cudnn_checked = True
        _cudnn_available = _ensure_cuda_checked() and _cudnn_works()
    return _cudnn_available


def get_providers(force_cpu=False):
    """Best available ONNX providers for Conv-heavy models (liveness, LaMa).
    Requires cuDNN for CUDA. Falls back: CUDA+cuDNN -> DirectML -> CPU.
    """
    if force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
        return ["CPUExecutionProvider"]
    _ensure_cudnn_checked()
    available = set(ort.get_available_providers())
    providers = []
    if _cudnn_available:
        providers.append("CUDAExecutionProvider")
    for p in ("DmlExecutionProvider", "CPUExecutionProvider"):
        if p in available:
            providers.append(p)
    return providers or ["CPUExecutionProvider"]


def get_insightface_providers():
    """InsightFace detection (SCRFD) uses Conv ops, so CUDA requires cuDNN.
    Fall back to CPU when cuDNN is missing (common on Windows without
    cudnn64_9.dll), otherwise every _app.get() crashes with NOT_IMPLEMENTED.
    """
    _ensure_cudnn_checked()
    if _cudnn_available:
        return ["CUDAExecutionProvider"]
    return ["CPUExecutionProvider"]


def provider_name(providers):
    return providers[0] if providers else "CPUExecutionProvider"
