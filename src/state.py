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


class TxRecord:
    """Track lifecycle of outbound transmissions."""

    def __init__(self, packet_id: str, text: str, destination: str):
        self.packet_id = str(packet_id)
        self.text = text
        self.destination = destination
        self.timestamp = time.time()
        self.status = "HARDWARE_ACCEPTED"  # HARDWARE_ACCEPTED, VERIFIED_RF, ACKNOWLEDGED, FAILED
        self.verified_at = None
        self.error_reason = None


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

        # Transmission Verification Ledger
        self.tx_ledger = {}

        # Threading / Async Interop Queue
        self.packet_queue = asyncio.Queue()
        self.main_loop = None
        self.interface_instance = None

    def register_tx(self, packet_id: str, text: str, destination: str = "^all"):
        """Registers a new outbound packet in the verification ledger."""
        record = TxRecord(packet_id, text, destination)
        self.tx_ledger[str(packet_id)] = record
        if len(self.tx_ledger) > 50:
            oldest_key = next(iter(self.tx_ledger))
            del self.tx_ledger[oldest_key]
        return record

    def mark_tx_verified(self, packet_id: str, status: str = "VERIFIED_RF"):
        """Marks a pending transmission as verified over RF hardware or ACKed."""
        pid = str(packet_id)
        if pid in self.tx_ledger:
            record = self.tx_ledger[pid]
            record.status = status
            record.verified_at = time.time()
            return record
        return None

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
