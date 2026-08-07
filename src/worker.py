import random
import re
import time
from src.config import (
    BOT_HANDLE,
    DRY_HEAT_RESPONSES,
    MAX_CONTEXT_MESSAGES,
    logger,
)
from src.state import bot_state
from src.llm import query_host_llm_with_context
from src.mesh import send_mesh_message
from src.dm import handle_direct_message


async def process_queue():
    """Consumes mesh messages, tracks conversational pace, and enforces dynamic cooldowns."""
    while True:
        packet_data = await bot_state.packet_queue.get()
        sender_handle = packet_data["sender"]
        from_id = packet_data.get("from_id")
        msg_text = packet_data["text"]
        is_dm = packet_data.get("is_dm", False)

        # Prevent self-messages appended to history from executing worker logic
        if sender_handle == BOT_HANDLE:
            bot_state.packet_queue.task_done()
            continue

        # Route 1-on-1 Direct Messages to dedicated dm.py module
        if is_dm:
            await handle_direct_message(sender_handle, from_id, msg_text)
            bot_state.packet_queue.task_done()
            continue

        # 1. Append external message and increment pace counter
        bot_state.message_buffer.append({"sender": sender_handle, "text": msg_text})
        bot_state.messages_since_last_reply += 1

        logger.info(
            f"📥 Context [{len(bot_state.message_buffer)}/{MAX_CONTEXT_MESSAGES}] "
            f"Pace Counter: {bot_state.messages_since_last_reply}/{bot_state.current_target_threshold} "
            f"[{sender_handle}]: {msg_text}"
        )

        current_time = time.time()
        time_since_last = current_time - bot_state.last_reply_timestamp

        # 2. Check Triggers
        is_direct_mention = bool(
            re.search(rf"\b@?{BOT_HANDLE}\b", msg_text, re.IGNORECASE)
        )
        is_heat_trigger = bool(
            re.search(r"\b(heat|hot|sweltering|scorching|degrees)\b", msg_text, re.IGNORECASE)
        )

        if is_heat_trigger:
            dry_heat_reply = random.choice(DRY_HEAT_RESPONSES)
            logger.info(f"🔥 Heat keyword matched! Responding: '{dry_heat_reply}'")
            send_mesh_message(dry_heat_reply)
            bot_state.packet_queue.task_done()
            continue

        if is_direct_mention:
            logger.info("🚀 Direct mention trigger matched!")
            context_snapshot = list(bot_state.message_buffer)
            ai_reply = await query_host_llm_with_context(context_snapshot)
            if ai_reply:
                send_mesh_message(ai_reply)
            bot_state.packet_queue.task_done()
            continue

        if bot_state.messages_since_last_reply >= bot_state.current_target_threshold:
            if time_since_last < bot_state.current_cooldown_target:
                logger.debug(
                    f"⏳ Cooldown active ({int(bot_state.current_cooldown_target - time_since_last)}s remaining of {bot_state.current_cooldown_target}s target). "
                    "Skipping passive reply."
                )
            else:
                logger.info(
                    f"🚀 Passive pace threshold reached ({bot_state.messages_since_last_reply}/{bot_state.current_target_threshold} msgs)."
                )
                context_snapshot = list(bot_state.message_buffer)
                ai_reply = await query_host_llm_with_context(context_snapshot)
                if ai_reply:
                    logger.info(f"📢 Transmitting Grey Beard Reply: '{ai_reply}'")
                    send_mesh_message(ai_reply)
                else:
                    logger.warning(
                        "⚠️ LLM reply was empty or failed. Resetting pace counter to avoid rapid re-querying."
                    )
                    bot_state.reset_conversation_pace()

        bot_state.packet_queue.task_done()
