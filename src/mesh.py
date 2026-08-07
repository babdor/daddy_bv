import asyncio
from pubsub import pub
from src.config import TARGET_CHANNEL_INDEX, BOT_HANDLE, SERIAL_PORT, logger
from src.state import bot_state


def get_node_handle(from_id, interface):
    """Resolves a node ID to its 4-character short name or last 4 of hex ID."""
    if not from_id:
        return "UNK"

    if from_id in bot_state.node_handle_cache:
        return bot_state.node_handle_cache[from_id]

    handle = None
    try:
        if interface and hasattr(interface, "nodes") and interface.nodes:
            node_info = interface.nodes.get(from_id)
            if node_info and "user" in node_info:
                handle = node_info["user"].get("shortName")
    except Exception as e:
        logger.debug(f"Could not resolve short handle for {from_id}: {e}")

    if not handle:
        handle = from_id[-4:] if len(from_id) >= 4 else from_id

    bot_state.node_handle_cache[from_id] = handle
    return handle


def send_mesh_message(text: str):
    """Sends a message, records local state, and randomizes pace parameters."""
    if not bot_state.interface_instance:
        logger.warning("⚠️ Cannot send message: Serial interface instance not connected.")
        return

    try:
        pkt = bot_state.interface_instance.sendText(
            text,
            destinationId="^all",
            channelIndex=TARGET_CHANNEL_INDEX,
        )
        pkt_id = getattr(pkt, "id", None) if not isinstance(pkt, dict) else pkt.get("id")
        pkt_str = f" [Packet ID: {pkt_id}]" if pkt_id else ""
        logger.info(f"📤 Sent mesh message ({len(text)} chars){pkt_str}: '{text}'")

        # Reset counters & select new random triggers
        bot_state.reset_conversation_pace()

        # Store local output in history buffer
        bot_state.message_buffer.append({"sender": BOT_HANDLE, "text": text})

    except Exception as e:
        logger.error(f"❌ Failed to transmit message over serial interface: {e}", exc_info=True)


def setup_public_channel(node):
    """Ensures operating parameters on Primary Channel Index 0."""
    try:
        ch0_settings = node.channels[0].settings
        ch0_name = ch0_settings.name if ch0_settings.name else "DEFCONnect"
        logger.info(f"⚙️ Operating on Primary Channel (Index 0): '{ch0_name}'")
    except Exception as e:
        logger.error(f"❌ Error during channel setup: {e}", exc_info=True)


def on_receive(packet, interface=None, **kwargs):
    """Bridge callback: receives PyPubSub events, filters echoes, and extracts handle."""
    try:
        if "decoded" in packet:
            portnum = packet["decoded"].get("portnum")
            if portnum not in ("TEXT_MESSAGE_APP", 1, "1"):
                return

            channel_index = packet.get("channel", 0)
            if channel_index != TARGET_CHANNEL_INDEX:
                return

            # Check 1: Ignore messages sent by local node
            from_num = packet.get("from")
            from_id = packet.get("fromId")

            if (bot_state.my_node_num and from_num == bot_state.my_node_num) or (
                bot_state.my_node_id and from_id == bot_state.my_node_id
            ):
                logger.debug("🛑 Dropping self-originated node packet.")
                return

            msg = packet["decoded"].get("text", "").strip()
            if not msg:
                return

            # Check 2: Prevent loopback echoes of last sent message
            if bot_state.last_sent_text and msg == bot_state.last_sent_text:
                logger.debug("🛑 Dropping loopback echo of last sent message.")
                return

            sender_handle = get_node_handle(from_id, interface)

            if bot_state.main_loop and bot_state.main_loop.is_running():
                bot_state.main_loop.call_soon_threadsafe(
                    bot_state.packet_queue.put_nowait,
                    {"sender": sender_handle, "text": msg},
                )

    except Exception as e:
        logger.error(f"Error bridging packet to async queue: {e}", exc_info=True)


def on_connection(interface=None, topic=pub.AUTO_TOPIC, **kwargs):
    """Triggered upon successful serial link initialization."""
    bot_state.interface_instance = interface

    try:
        bot_state.my_node_num = interface.myInfo.my_node_num
        bot_state.my_node_id = interface.myInfo.my_node_id
        logger.info(
            f"🆔 Local Node Initialized: {bot_state.my_node_id} ({bot_state.my_node_num})"
        )
    except Exception as e:
        logger.warning(f"⚠️ Could not extract local node info: {e}")

    logger.info(f"✅ Connected to serial radio hardware on {SERIAL_PORT}!")
    setup_public_channel(interface.localNode)

    # Initialize random target bounds for first run
    bot_state.reset_conversation_pace()

    logger.info("🚀 Bot monitoring channel. Operating in dynamic passive mode...")
