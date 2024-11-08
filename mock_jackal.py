import time
import json
import logging
import asyncio
import fractions
from typing import Tuple

import av
import cv2
import numpy as np
from aiortc import VideoStreamTrack, RTCDataChannel

from signaling_utils import WebRTCClient, initiate_signaling
from settings import *


# Copied from aiortc source code
VIDEO_PTIME = 1 / 30
VIDEO_CLOCK_RATE = 90000
VIDEO_TIME_BASE = fractions.Fraction(1, VIDEO_CLOCK_RATE)


class MockStateSender:
    _timestamp: int
    _start: float

    def __init__(self, data_channel: RTCDataChannel) -> None:
        self.data_channel: RTCDataChannel = data_channel

    # NOTE: This function is copied from aiortc source code
    async def next_timestamp(self) -> Tuple[int, fractions.Fraction]:
        if hasattr(self, "_timestamp"):
            self._timestamp += int(VIDEO_PTIME * VIDEO_CLOCK_RATE)
            wait = self._start + (self._timestamp / VIDEO_CLOCK_RATE) - time.time()
            await asyncio.sleep(wait)
        else:
            self._start = time.time()
            self._timestamp = 0
        return self._timestamp, VIDEO_TIME_BASE

    # NOTE: Use mock state data for the prototype
    async def send_state(self) -> None:
        pts, _ = await self.next_timestamp()
        data = {"timestamp": pts, "state": [1, 1, 1]}
        self.data_channel.send(json.dumps(data))


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

        return video_frame


class JackalClient(WebRTCClient):
    def __init__(self, signaling_ip: str, signaling_port: int) -> None:
        super().__init__(signaling_ip, signaling_port)
        self.data_channel: RTCDataChannel = None
        self.data_sender: MockStateSender = None

    def __setup_track_callbacks(self) -> None:
        camera_track: CameraStreamTrack = CameraStreamTrack()
        self.pc.addTrack(camera_track)

    def __setup_datachannel_callbacks(self) -> None:
        self.data_channel = self.pc.createDataChannel("datachannel")
        self.data_sender: MockStateSender = MockStateSender(self.data_channel)

        @self.data_channel.on("open")
        async def on_open() -> None:
            print("Data channel opened")
            while True:
                await self.data_sender.send_state()

        @self.data_channel.on("message")
        def on_message(message: str) -> None:
            print(f"Received message: {message}")

        @self.data_channel.on("close")
        def on_close() -> None:
            print("Data channel closed")


    async def run(self) -> None:
        await super().run()
        self.__setup_track_callbacks()
        self.__setup_datachannel_callbacks()
        await initiate_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_initiator() -> None:
    initiator: WebRTCClient = JackalClient(IP, PORT)
    await initiator.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(run_initiator())
