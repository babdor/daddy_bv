import asyncio
import collections
import random
import time
from src.config import (
    MAX_CONTEXT_MESSAGES,
    MIN_TRIGGER_THRESHOLD,
    MAX_TRIGGER_THRESHOLD,
    MIN_COOLDOWN_SECONDS,
    MAX_COOLDOWN_SECONDS,
    logger,
)


class BotState:
    """Encapsulates runtime state, buffers, node cache, and pacing logic."""

    def __init__(self):
        self.messages_since_last_reply = 0
        self.last_reply_timestamp = 0
        self.current_target_threshold = random.randint(
            MIN_TRIGGER_THRESHOLD, MAX_TRIGGER_THRESHOLD
        )
        self.current_cooldown_target = random.randint(
            MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS
        )

        self.message_buffer = collections.deque(maxlen=MAX_CONTEXT_MESSAGES)
        self.node_handle_cache = {}

        # Loop Prevention & Node Info
        self.my_node_num = None
        self.my_node_id = None
        self.last_sent_text = None

        # Threading / Async Interop Queue
        self.packet_queue = asyncio.Queue()
        self.main_loop = None
        self.interface_instance = None

    def reset_conversation_pace(self):
        """Resets message counters and rolls new randomized values for threshold and cooldown."""
        self.messages_since_last_reply = 0
        self.last_reply_timestamp = time.time()

        self.current_target_threshold = random.randint(
            MIN_TRIGGER_THRESHOLD, MAX_TRIGGER_THRESHOLD
        )
        self.current_cooldown_target = random.randint(
            MIN_COOLDOWN_SECONDS, MAX_COOLDOWN_SECONDS
        )

        logger.info(
            f"🎲 Pacing randomized -> Next Passive Threshold: {self.current_target_threshold} msgs | "
            f"Next Cooldown: {self.current_cooldown_target}s"
        )


# Global state singleton instance
bot_state = BotState()
