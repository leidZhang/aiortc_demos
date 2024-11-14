import logging
import asyncio

import av
import cv2
import numpy as np
from aiortc import RTCDataChannel, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaRelay

from signaling_utils import WebRTCClient, receive_signaling
from settings import *


class StationClient(WebRTCClient):
    def __init__(self, signaling_server_url: str, room_id: str) -> None:
        super().__init__(signaling_server_url, room_id)
        self.data_channel_event: asyncio.Event = asyncio.Event()
        self.data_channel: RTCDataChannel = None
        self.media_relay: MediaRelay = MediaRelay()
        self.track_counter: int = 0

    def __setup_track_callbacks(self) -> None:
        @self.pc.on("track")
        async def on_track(track: VideoStreamTrack):
            print("Track received", track.kind)
            if track.kind == "video":
                current: int = self.track_counter
                self.track_counter += 1
                while not self.done.is_set():
                    frame: av.VideoFrame = await track.recv()
                    # Process the frame (e.g., display it using OpenCV)
                    image: np.ndarray = frame.to_ndarray(format="bgr24")
                    if current == 0:
                        window_name: str = "Camera"
                        print("Demonstrating camera")
                        cv2.imshow(window_name, image)
                        cv2.waitKey(1)
                    elif current == 1:
                        window_name: str = "Colored"
                        print("Demonstrating colored")
                    else:
                        window_name: str = "Mosaic"
                        print("Demonstrating mosaic")

    async def run(self) -> None:
        await super().run()
        self.__setup_track_callbacks()
        await receive_signaling(self.pc, self.signaling)

        await self.done.wait()
        await self.pc.close()
        await self.signaling.close()


async def run_receiver() -> None:
    receiver: WebRTCClient = StationClient(IP, PORT)
    await receiver.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(run_receiver())
