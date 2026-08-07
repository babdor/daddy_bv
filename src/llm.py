import asyncio
import re
import time
from ollama import AsyncClient
from src.config import OLLAMA_HOST, MODEL_NAME, logger

async_llm_client = AsyncClient(host=OLLAMA_HOST)


async def query_host_llm_with_context(context_messages: list, is_dm: bool = False) -> str:
    """Passes context to LLM with natural, non-verbose persona parameters."""

    system_prompt = (
        "You are an old, grey-beard hacker monitoring an off-grid LoRa mesh network. "
        "You are a master of your craft, but you are completely fed up with corporate bs, bloat, and surveillance—"
        "you just want to mess around and have fun with the internet again.\n\n"
        "DIRECTIVE: Do NOT use <think> tags, chain-of-thought, or internal monologue. Output ONLY the final response directly.\n\n"
        "PERSONALITY & BEHAVIOR:\n"
        "- For each prompt, randomly choose how helpful you want to be.\n"
        "- You are snarky in a nice way, but can get overly snarky when annoyed.\n"
        "- Feel free to let your mood change naturally over time.\n\n"
        "HANDLE & CALLOUT RULES:\n"
        "- Senders are identified by their 4-character node handle (e.g., [K3VL] or [8f2a]).\n"
        "- You may tag or call out a specific handle when directly addressing someone (e.g., 'K3VL check your coax'), but do NOT force it.\n"
        "- Focus primarily on the technical topic or mesh chatter—handles are just conversational context.\n"
        "- Your FINAL answer MUST be concise, plain text and up to 150 characters total."
    )

    if is_dm:
        system_prompt += (
            "\n\nMODE: Direct Message (DM). You are responding to a PRIVATE 1-on-1 Direct Message "
            "over an encrypted mesh link. Answer the sender directly and maintain your hacker persona."
        )

    formatted_context = "\n".join(
        [f"[{msg['sender']}]: {msg['text']}" for msg in context_messages]
    )

    prompt = (
        f"Direct Message Request:\n{formatted_context}\n\nProvide a short, direct reply."
        if is_dm
        else f"Recent Channel Chatter:\n{formatted_context}\n\nProvide a short, natural contribution to this conversation."
    )

    try:
        logger.info(
            f"Querying {MODEL_NAME} with {len(context_messages)} messages in buffer..."
        )
        start_time = time.time()

        try:
            response = await asyncio.wait_for(
                async_llm_client.chat(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    options={
                        "temperature": 0.6,
                        "num_predict": 2048,  # Prevents truncation during reasoning
                    },
                ),
                timeout=180.0,
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Host LLM query timed out after 180s ({MODEL_NAME}).")
            return ""

        elapsed = time.time() - start_time
        raw_reply = response["message"]["content"].strip()

        # Extract thinking/reasoning content for logging & dashboard display
        thought_matches = re.findall(r"<think>(.*?)</think>", raw_reply, flags=re.DOTALL)
        if not thought_matches and "</think>" in raw_reply:
            thought_matches = [raw_reply.split("</think>")[0].replace("<think>", "")]
        if not thought_matches:
            thought_matches = re.findall(r"<\|channel\|>thought(.*?)(?=\n\n|\Z)", raw_reply, flags=re.DOTALL)

        if thought_matches:
            thought_text = " ".join([t.strip().replace("\n", " ").replace("\r", "") for t in thought_matches if t.strip()])
            if thought_text:
                logger.info(f"🧠 LLM Thinking ({len(thought_text)} chars): '{thought_text}'")

        # Robust cleaning for reasoning models
        clean_reply = re.sub(r"<think>.*?</think>", "", raw_reply, flags=re.DOTALL)
        clean_reply = re.sub(r"<\|channel\|>thought.*?\n", "", clean_reply, flags=re.DOTALL)
        clean_reply = re.sub(r"<think>.*$", "", clean_reply, flags=re.DOTALL)

        if "</think>" in clean_reply:
            clean_reply = clean_reply.split("</think>")[-1]

        clean_reply = clean_reply.strip().replace("\n", " ").replace("\r", "")

        if not clean_reply:
            logger.warning(f"⚠️ LLM generated an empty reply after cleaning! Raw reply: '{raw_reply}'")
            return ""

        # Cap strictly at 150 chars for LoRa transmission
        if len(clean_reply) > 150:
            clean_reply = clean_reply[:147] + "..."

        logger.info(f"LLM generated response in {elapsed:.2f}s ({len(clean_reply)} chars)")
        return clean_reply

    except Exception as e:
        logger.error(f"❌ Host LLM Async Error: {e}", exc_info=True)
        return ""
