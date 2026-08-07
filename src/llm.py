import re
import time
from ollama import AsyncClient
from src.config import OLLAMA_HOST, MODEL_NAME, logger

async_llm_client = AsyncClient(host=OLLAMA_HOST)


async def query_host_llm_with_context(context_messages: list) -> str:
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

    formatted_context = "\n".join(
        [f"[{msg['sender']}]: {msg['text']}" for msg in context_messages]
    )

    prompt = (
        f"Recent Channel Chatter:\n{formatted_context}\n\n"
        "Provide a short, natural contribution to this conversation."
    )

    try:
        logger.info(
            f"Querying {MODEL_NAME} with {len(context_messages)} messages in buffer..."
        )
        start_time = time.time()

        response = await async_llm_client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": 0.6,
                "num_predict": 2048,  # Prevents truncation during reasoning
            },
        )

        elapsed = time.time() - start_time
        raw_reply = response["message"]["content"].strip()

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
