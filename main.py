import asyncio
import logging
import sys
from pathlib import Path

# Add the current directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).parent))

from engine.pulse import SystemPulse
from engine.api_server import app
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ALMS_Main")

async def run_pulse():
    vault_path = "./knowledge"
    pulse = SystemPulse(vault_path)
    logger.info("Starting ALMS Pulse Daemon...")
    await pulse.start()

def run_api():
    logger.info("Starting ALMS API Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

async def main():
    # Start the Pulse in the background
    pulse_task = asyncio.create_task(run_pulse())
    
    # Start the API Server (blocking)
    # Note: In a production environment, you might use a process manager
    # but for this standalone project, we'll run them together.
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_api)
    
    await pulse_task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("ALMS Intelligence Engine shutting down...")
