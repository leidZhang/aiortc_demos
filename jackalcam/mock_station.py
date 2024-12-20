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

    def __setup_track_callbacks(self) -> None:
        @self.pc.on("track")
        async def on_track(track: VideoStreamTrack):
            print("Track received", track.kind)
            if track.kind == "video":
                while True:
                    frame: av.VideoFrame = await track.recv()
                    # Process the frame (e.g., display it using OpenCV)
                    image: np.ndarray = frame.to_ndarray(format="bgr24")
                    cv2.imshow("Received Video", image)
                    cv2.waitKey(1)

    def __setup_datachannel_callbacks(self) -> None:
        @self.pc.on("datachannel")
        async def on_datachannel(channel: RTCDataChannel) -> None:
            self.data_channel = channel

            @self.data_channel.on("open")
            async def on_open() -> None:
                while True:
                    await asyncio.sleep(0.03)
                    self.data_channel.send("Data channel opened by Jackal")

            @self.data_channel.on("message")
            def on_message(message: str) -> None:
                ...
                # print(f"Received message: {message} from Jackal")
                # self.data_channel.send("Hello from workstation")

            @self.data_channel.on("close")
            def on_close() -> None:
                print("Data channel closed by Jackal")

            # NOTE: I dont know why this is needed, but without it, on_open() is not called
            if self.data_channel.readyState == "open":
                await on_open()

    async def run(self) -> None:
        await super().run()
        self.__setup_track_callbacks()
        self.__setup_datachannel_callbacks()
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
