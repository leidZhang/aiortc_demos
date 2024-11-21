import cv2
import fractions
import numpy as np
from av import VideoFrame
import matplotlib.pyplot as plt
from aiortc.jitterbuffer import JitterFrame
from aiortc.codecs.h264 import H264Decoder, H264Encoder, h264_depayload

WEIGHTS: np.ndarray = np.array([100, 10, 1])
VIDEO_TIME_BASE = fractions.Fraction(1, 90000)


def semantic_to_rgb(semantic: np.ndarray) -> np.ndarray:
    rgb: np.ndarray = np.repeat(semantic, 3, axis=-1)
    rgb[:, :, 2] = rgb[:, :, 2] % 10
    rgb[:, :, 1] = (rgb[:, :, 1] // 10) % 10
    rgb[:, :, 0] = rgb[:, :, 0] // 100
    rgb = (rgb * 20).astype(np.uint8)
    return rgb


def decode_to_semantic(rgb: np.ndarray) -> np.ndarray:
    decoded_rgb: np.ndarray = rgb.astype(np.float32) / 20
    decoded_rgb = np.round(decoded_rgb)
    decoded_rgb = np.dot(decoded_rgb, WEIGHTS).reshape(decoded_rgb.shape[0], decoded_rgb.shape[1], 1)
    return decoded_rgb.astype(np.int32)


def create_video_frames(data, time_base=VIDEO_TIME_BASE):
    frames = []
    for i in range(100):
        semantic: np.ndarray = data["semantic"][i % len(data["semantic"])]
        rgb: np.ndarray = semantic_to_rgb(semantic)
        rgb = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        frame: VideoFrame = VideoFrame.from_ndarray(rgb, format="rgb24")
        frame.pts, frame.time_base = int(i / time_base / 30), time_base
        frame.reformat(format="yuv420p")
        frames.append(frame)
    return frames


if __name__ == '__main__':
    npz_data = np.load("transmit_depth/test_data.npz", allow_pickle=True)
    frames = create_video_frames(npz_data)
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

    fig, axs = plt.subplots(1, 2, figsize=(10, 5))
    semantic0 = np.zeros((480, 640, 1), dtype=np.int32) # data['semantic'][0]
    im0 = axs[0].imshow(semantic0, cmap='jet', vmin=0, vmax=800)
    axs[0].set_title('Semantic Original')
    fig.colorbar(im0, ax=axs[0])

    semantic1 = np.zeros((480, 640, 1), dtype=np.int32) # data['semantic'][0]
    im1 = axs[1].imshow(semantic1, cmap='jet', vmin=0, vmax=800)
    axs[1].set_title('Semantic Decoded')
    fig.colorbar(im1, ax=axs[1])

    # for i, frame in enumerate(decoded_frames):
    for i in range(len(npz_data['semantic'])):
        semantic0: np.ndarray = npz_data["semantic"][i % len(npz_data["semantic"])]
        frame = decoded_frames[i]
        decoded_rgb: np.ndarray = frame.to_ndarray(format='bgr24')
        print("RGB Shape", decoded_rgb.shape)
        semantic1 = decode_to_semantic(decoded_rgb)
        print("Original", semantic0, semantic0.shape)
        print("Decoded", semantic1, semantic1.shape)
        im0.set_data(semantic0)
        im1.set_data(semantic1)
        plt.pause(0.1)

    plt.ioff()
    plt.show()
