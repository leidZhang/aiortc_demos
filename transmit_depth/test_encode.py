import cv2
import fractions
import numpy as np
from av import VideoFrame
from aiortc.jitterbuffer import JitterFrame
from aiortc.codecs.vpx import Vp8Decoder, Vp8Encoder, vp8_depayload
from aiortc.codecs.h264 import H264Decoder, H264Encoder, h264_depayload


VIDEO_TIME_BASE = fractions.Fraction(1, 90000)


def encode_to_rgba(image: np.ndarray) -> np.ndarray:
    height, width, channel = image.shape
    return image.view(np.uint8).reshape(height, width, 4)

def decode_to_depth(image: np.ndarray) -> np.ndarray: # a -> high 1, b -> high 2, g -> low 2, r -> low 1
    # Since we dropped the r channel, we need to add it back
    empty_channel: np.ndarray = np.zeros((image.shape[0], image.shape[1], 1), dtype=np.uint8)
    decoded_rgba: np.ndarray = np.concatenate((empty_channel, image), axis=-1)
    return decoded_rgba.view(np.float32).reshape(image.shape[0], image.shape[1], 1)


def create_video_frames(time_base=VIDEO_TIME_BASE):
    data = np.load("transmit_depth/test_data.npz", allow_pickle=True)

    frames = []
    for i in range(100):
        depth: np.ndarray = data["depth"][i % len(data["depth"])]
        uint_depth: np.ndarray = (depth * 255).astype(np.uint8)
        uint_depth = np.repeat(uint_depth, 3, axis=-1)

        uint_depth = cv2.cvtColor(uint_depth, cv2.COLOR_RGB2BGR)
        frame: VideoFrame = VideoFrame.from_ndarray(uint_depth, format="rgb24")
        frame.pts, frame.time_base = int(i / time_base / 30), time_base
        frame.reformat(format="yuv420p")
        frames.append(frame)
    return frames


if __name__ == "__main__":
    frames = create_video_frames()
    # encoder, decoder = Vp8Encoder(), Vp8Decoder()
    encoder, decoder = H264Encoder(), H264Decoder()

    decoded_frames = []
    for i, frame in enumerate(frames):
        packages, timestamp = encoder.encode(frame)

        data = b""
        for package in packages:
            # data += vp8_depayload(package)
            data += h264_depayload(package)

        frames = decoder.decode(JitterFrame(data=data, timestamp=timestamp))
        decoded_frames.append(frames[0])

    for i, frame in enumerate(decoded_frames):
        decoded_rgb: np.ndarray = frame.to_ndarray(format='bgr24')
        decoded_rgb = np.mean(decoded_rgb, axis=2).astype(np.uint8)
        decoded_float_arr: np.ndarray = decoded_rgb.astype(np.float32) / 255.0
        cv2.imshow("Decoded", decoded_float_arr)
        cv2.waitKey(100)
