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
from aiortc.contrib.media import MediaBlackhole

from signaling_utils import WebRTCClient, initiate_signaling
from settings import *


class ColoredStreamTrack(VideoStreamTrack):
    def __init__(self) -> None:
        super().__init__()
        self.channel_num: int = 0

    async def recv(self) -> av.VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = np.ones((480, 640, 3), dtype=np.uint8) * self.channel_num // 2
        print(f"Colored frame {self.channel_num // 2} sent to the work station")
        self.channel_num = (self.channel_num + 1) % 256

        # Convert frame to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.ascontiguousarray(frame) # Make sure frame is contiguous in memory

        # Create VideoFrame
        video_frame: av.VideoFrame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts, video_frame.time_base = pts, time_base
        print("Colored frame sent to the work station")

        return video_frame


class JackalClient(WebRTCClient):
    def __init__(self, signaling_ip: str, signaling_port: int) -> None:
        super().__init__(signaling_ip, signaling_port)
        self.data_channel: RTCDataChannel = None

    def __setup_track_callbacks(self) -> None:
        colored_track: ColoredStreamTrack = ColoredStreamTrack()
        self.pc.addTrack(colored_track)

    async def run(self) -> None:
        await super().run()
        self.__setup_track_callbacks()
        await initiate_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_initiator() -> None:
    initiator: WebRTCClient = JackalClient(IP, PORT)
    await initiator.run()


if __name__ == "__main__":
    import tracemalloc

    tracemalloc.start()
    try:
        logging.basicConfig(level=logging.ERROR)
        asyncio.run(run_initiator())
    except KeyboardInterrupt:
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')

        print("[ Top 10 ]")
        for stat in top_stats[:10]:
            print(stat)