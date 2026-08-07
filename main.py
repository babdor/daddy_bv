import asyncio
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

from src.config import SERIAL_PORT, logger
from src.state import bot_state
from src.mesh import on_receive, on_connection
from src.worker import process_queue


async def main():
    bot_state.main_loop = asyncio.get_running_loop()

    # Start background consumer worker
    asyncio.create_task(process_queue())

    # Subscribe to PyPubSub events
    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_connection, "meshtastic.connection.established")

    logger.info(f"Connecting to serial interface at {SERIAL_PORT}...")
    interface = meshtastic.serial_interface.SerialInterface(devPath=SERIAL_PORT)

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nShutting down cleanly...")
        if bot_state.interface_instance:
            bot_state.interface_instance.close()
    except Exception as e:
        logger.critical(f"Fatal application error: {e}", exc_info=True)