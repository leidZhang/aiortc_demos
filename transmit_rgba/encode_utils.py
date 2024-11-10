import numpy as np

RGBA_CHANNELS: int = 4
LABEL_MAP_CHANNELS: int = 1


class InvalidImageShapeError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class InvalidDataTypeError(Exception):
    def __init__(self, message: str) -> None:
        self.message: str = message


def encode_to_rgba(image: np.ndarray) -> np.ndarray:
    height, width, channel = image.shape
    if image.dtype not in [np.float32, np.int32]:
        raise InvalidDataTypeError("Image must be of type float32 or int32")
    if channel != 1:
        raise InvalidImageShapeError("Image must be single channel")

    return image.view(np.uint8).reshape(height, width, RGBA_CHANNELS)


def decode_from_rgba(rgba: np.ndarray, data_type: np.dtype) -> np.ndarray:
    if rgba.shape[2] != 4:
        raise InvalidImageShapeError("RGBA image must have 4 channels")
    if data_type not in [np.float32, np.int32]:
        raise InvalidDataTypeError("Data type must be float32 or int32")

    return rgba.view(data_type).reshape(rgba.shape[0], rgba.shape[1], LABEL_MAP_CHANNELS)


def rgb_to_rgba(rgb: np.ndarray, alpha: int = 255) -> np.ndarray:
    if alpha < 0 or alpha > 255:
        raise ValueError("Alpha channel must be between 0 and 255")
    if rgb.shape[-1] != 3:
        raise InvalidImageShapeError("RGB image must have 3 channels")

    alpha_channel: np.ndarray = np.ones((rgb.shape[0], rgb.shape[1], 1), dtype=np.uint8) * alpha
    return np.concatenate((rgb, alpha_channel), axis=-1)