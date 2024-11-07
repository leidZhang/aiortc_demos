import logging
import asyncio

import av
import cv2
import numpy as np
from aiortc import RTCDataChannel, VideoStreamTrack

from signaling_utils import WebRTCClient, initiate_signaling
from settings import *


class CameraStreamTrack(VideoStreamTrack):
    def __init__(self, camera_id: int = 0) -> None:
        super().__init__()
        self.cap: cv2.VideoCapture = cv2.VideoCapture(camera_id)

    async def recv(self) -> av.VideoFrame:
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            return None

        # Convert frame to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.ascontiguousarray(frame) # Make sure frame is contiguous in memory

        # Create VideoFrame
        video_frame: av.VideoFrame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = pts, time_base
        print(f"Received frame at {pts}")
        return video_frame


class JackalClient(WebRTCClient):
    def __init__(self, signaling_ip: str, signaling_port: int) -> None:
        super().__init__(signaling_ip, signaling_port)
        # self.data_channel: RTCDataChannel = None

    def _setup_callbacks(self) -> None:
        camera_track: CameraStreamTrack = CameraStreamTrack()
        self.pc.addTrack(camera_track)

    async def run(self) -> None:
        await super().run()
        self._setup_callbacks()
        await initiate_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_initiator() -> None:
    initiator: WebRTCClient = JackalClient(IP, PORT)
    await initiator.run()


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(run_initiator())
