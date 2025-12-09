from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import asyncio

app = FastAPI()

# Preset countdown definitions
PRESET_TIMERS = {
    "5m": 5 * 60,
    "1m": 60,
    "30s": 30,
    "10s": 10,
    "5s": 5,
}

async def sse_countdown_generator(total_seconds: int):
    """
    SSE generator that streams countdown values.
    Works with StreamingResponse.
    """
    for remaining in range(total_seconds, -1, -1):
        # SSE format:  data: <payload>\n\n
        yield f"data: {remaining}\n\n"
        await asyncio.sleep(1)


@app.get("/countdown/{preset}")
async def countdown(preset: str):
    """
    Countdown endpoint using only StreamingResponse.
    """
    if preset not in PRESET_TIMERS:
        raise HTTPException(
            400,
            f"Invalid preset. Valid options: {list(PRESET_TIMERS.keys())}"
        )

    seconds = PRESET_TIMERS[preset]

    return StreamingResponse(
        sse_countdown_generator(seconds),
        media_type="text/event-stream"
    )

