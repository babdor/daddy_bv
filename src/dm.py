import asyncio
from src.config import logger
from src.llm import query_host_llm_with_context
from src.mesh import send_mesh_message


async def handle_direct_message(sender_handle: str, from_id: str, msg_text: str):
    """Processes incoming 1-on-1 Direct Messages (DMs) bypassing channel thresholds."""
    logger.info(
        f"💬 [DIRECT MESSAGE] From [{sender_handle}] ({from_id}): '{msg_text}'"
    )

    # Format 1-on-1 context payload
    dm_context = [{"sender": sender_handle, "text": msg_text}]

    # Query LLM with DM directive
    ai_reply = await query_host_llm_with_context(dm_context, is_dm=True)

    if ai_reply:
        target = from_id if from_id else sender_handle
        logger.info(
            f"📢 Transmitting DM Reply to [{sender_handle}] ({target}): '{ai_reply}'"
        )
        send_mesh_message(ai_reply, destination_id=target)
    else:
        logger.warning(
            f"⚠️ DM LLM reply was empty for [{sender_handle}]. Skipping transmission."
        )
