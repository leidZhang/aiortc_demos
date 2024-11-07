import json
import asyncio
import logging

import websockets

from settings import *

clients = set()

async def handler(websocket, path):
    # Register client
    clients.add(websocket)

    try:
        async for message in websocket:
            data = json.loads(message)
            # Broadcast the message to all connected clients except the sender
            for client in clients:
                if client != websocket:
                    await client.send(json.dumps(data))
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: {e}")
    except websockets.exceptions.ConnectionClosedOK:
        print("Connection closed normally")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Unregister client
        clients.remove(websocket)
        await websocket.close()


async def main():
    async with websockets.serve(handler, IP, PORT):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
