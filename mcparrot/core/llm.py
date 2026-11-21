import asyncio
import os

import anthropic
from dotenv import load_dotenv

from mcparrot.utils.logger import my_logger
from mcparrot.utils.prompts import MyPrompts

load_dotenv()

MODEL = os.getenv("MODEL")

class MyLLM:
    def __init__(self, api_key, base_url):
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=api_key, base_url=base_url
        )
        self.prompts = MyPrompts()
        self.logger = my_logger

    async def request(
        self,
        messages,
        tools,
        stage=None,
        name="LLM",
        temp=0.5,
        tokens=32768,
        system=None,
    ):
        """Stream a single assistant turn from the LLM.

        Yields dicts describing incremental events:
          {"type": "thinking_delta", "text": "..."}
          {"type": "text_delta", "text": "..."}
          {"type": "final_message", "content": [<content blocks>]}

        The `final_message` event always fires last and carries the fully
        assembled content blocks (including any tool_use blocks with their
        completed `input`), so callers can act on the turn once streaming
        text has finished being displayed.
        """
        if system is None:
            system = self.prompts.normal_system()

        try:
            self.logger.info(f"Calling {name}")

            async with self.anthropic_client.messages.stream(
                model=MODEL,
                messages=messages,
                tools=tools,
                system=system,
                temperature=temp,
                max_tokens=tokens,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            yield {"type": "text_delta", "text": delta.text}
                        elif delta.type == "thinking_delta":
                            yield {"type": "thinking_delta", "text": delta.thinking}

                # AWAIT the final message retrieval
                final_message = await stream.get_final_message()

            yield {"type": "final_message", "content": final_message.content}

        except asyncio.CancelledError:
            # Explicitly catch and re-raise to ensure clean propagation
            self.logger.info(f"LLM request for {name} was cancelled.")
            raise
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise
