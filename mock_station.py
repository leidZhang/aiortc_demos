import logging
import asyncio

import av
import cv2
import numpy as np
from aiortc import RTCDataChannel, VideoStreamTrack

from signaling_utils import WebRTCClient, receive_signaling


class VideoFrameProcessor(VideoStreamTrack):
    def __init__(self, track) -> None:
        super().__init__()
        self.track = track

    async def recv(self) -> av.VideoFrame:
        frame: av.VideoFrame = await self.track.recv()
        image: np.ndarray = frame.to_ndarray(format="bgr24")

        cv2.imshow("Video", image)
        cv2.waitKey(1)
        return frame


class StationClient(WebRTCClient):
    def __init__(self, signaling_server_url: str, room_id: str) -> None:
        super().__init__(signaling_server_url, room_id)
        self.data_channel_event: asyncio.Event = asyncio.Event()
        self.data_channel: RTCDataChannel = None

    def _setup_callbacks(self) -> None:
        @self.pc.on("track")
        def on_track(track):
            if track.kind == "video":
                self.__handle_video_track(track)

    def __handle_video_track(self, track) -> None:
        processor: VideoFrameProcessor = VideoFrameProcessor(track)
        self.pc.addTrack(processor)

    async def run(self) -> None:
        await super().run()
        self._setup_callbacks()
        await receive_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_receiver() -> None:
    receiver: WebRTCClient = StationClient("localhost", 1234)
    await receiver.run()


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    asyncio.run(run_receiver())
