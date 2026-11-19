"""Stops oversized requests before the app reads them.

Checks the Content-Length header first (cheap), and also counts the bytes as they
arrive, so a sender cannot dodge the limit by leaving the header out.
"""
import json


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await self._reject(send)
            return

        received = 0
        started = False   # has the app already begun its own response?
        rejected = False  # have we already sent the 413 ourselves?

        async def limited_receive():
            nonlocal received, rejected
            message = await receive()
            if message["type"] == "http.request" and not rejected:
                received += len(message.get("body", b""))
                if received > self.max_bytes and not started:
                    # Too big: answer 413 right now and tell the app the sender is gone,
                    # so it stops reading. (FastAPI would otherwise turn an error here into a 400.)
                    rejected = True
                    await self._reject(send)
                    return {"type": "http.disconnect"}
            return message

        async def tracking_send(message):
            nonlocal started
            if rejected:
                return  # our 413 is already sent; drop whatever the app tries to say after it
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        await self.app(scope, limited_receive, tracking_send)

    async def _reject(self, send):
        body = json.dumps({"detail": "Request body too large"}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
