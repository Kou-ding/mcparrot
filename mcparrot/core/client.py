import json
from datetime import datetime

from fastmcp import Client

from mcparrot.core.llm import MyLLM
from mcparrot.utils import config
from mcparrot.utils.logger import my_logger
from mcparrot.utils.prompts import MyPrompts


class MyClient:
    def __init__(self, api_key, base_url):

        self.llm = MyLLM(api_key, base_url)
        self.prompts = MyPrompts()
        self.logger = my_logger

        # Start clock & previous clock
        self.start_time = 0
        self.prev_time = 0

        # Max amount of time a pentesting attempt can take (in mins)
        self.time_limit = 360

        # The pentesting stage we are currently in
        self.stage = ""

        # The active session
        self.current_session = ""

        # The tools currently being used
        self.tools = ""

        # The mcp servers / client being used
        self.current_mcpclient = None

        # All messages displayed in the frontend
        self.messages = []

        # Stage specific message history
        self.recon_messages = []
        self.va_messages = []
        self.exploit_messages = []

        # Initialize fastmcp servers
        self.init_servers()

    def init_servers(self):
        """ Initialize fastmcp client objects """
        with open("servers/recon_servers.json", 'r') as f:
            recon_servers_json = json.load(f)
        with open("servers/va_servers.json", 'r') as f:
            va_servers_json = json.load(f)
        with open("servers/recon_servers.json", 'r') as f:
            recon_servers_json = json.load(f)
        with open("servers/exploit_servers.json", 'r') as f:
            exploit_servers_json = json.load(f)

        with open("servers/all_servers.json", 'r') as f:
            all_servers_json = json.load(f)
        with open("servers/terminal_servers.json", 'r') as f:
            terminal_servers_json = json.load(f)

        self.recon_client = Client(recon_servers_json)
        self.va_client = Client(va_servers_json)
        self.exploit_client = Client(exploit_servers_json)

        self.all_client = Client(all_servers_json)
        self.terminal_client = Client(terminal_servers_json)

    def set_current_mcpclient(self):
        """ Set current fastmcp active client """
        # Select correct tool bundle from config
        current_mode = config.get_setting("mode")
        if current_mode == "hawk":
            mcp_servers = config.get_setting("servers")
        elif current_mode == "raven":
            mcp_servers = self.stage
        else:
            raise ValueError(f"Unknown mode: {current_mode}")

        # List all available tools
        if mcp_servers == "recon" or mcp_servers == "recon-planning" :
            self.current_mcpclient = self.recon_client
        elif mcp_servers == "va" or mcp_servers == "va-planning":
            self.current_mcpclient = self.va_client
        elif mcp_servers == "exploit" or mcp_servers == "exploit-planning":
            self.current_mcpclient = self.exploit_client
        elif mcp_servers == "terminal" or mcp_servers == "finale":
            self.current_mcpclient = self.terminal_client
        elif mcp_servers == "all":
            self.current_mcpclient = self.all_client
        else:
            self.current_mcpclient = self.terminal_client

    async def list_tools(self):
        """ List available mcp server tools """
        self.set_current_mcpclient()

        if self.current_mcpclient is not None:
            async with self.current_mcpclient:
                self.tools = await self.current_mcpclient.list_tools()

            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema if tool.inputSchema else { # tool.inputSchema by itself was inadequate
                        "type": "object",
                        "properties": {}
                    }
                }
                for tool in self.tools
            ]
            return self.tools

    def block_to_dict(self, block):
        """ Convert a block object to a serializable dictionary immediately """
        if hasattr(block, 'type'):
            result = {"type": block.type}
            if hasattr(block, 'text'):
                result["text"] = block.text
            if hasattr(block, 'thinking'):
                result["thinking"] = block.thinking
            if hasattr(block, 'signature'):
                result["signature"] = block.signature
            if hasattr(block, 'name'):
                result["name"] = block.name
            if hasattr(block, 'input'):
                result["input"] = block.input
            if hasattr(block, 'id'):
                result["id"] = block.id
            if hasattr(block, 'citations'):
                result["citations"] = block.citations
            return result
        return block

    async def hawk_query(self, query: str):
        """ Process a user query, streaming events as they happen.

        Yields dicts of the form {"type": ..., ...} which the Flask route
        forwards to the frontend as SSE. Handles multi-step tool use: keeps
        looping (LLM -> tool -> LLM -> ...) until the model responds with a
        turn that contains no tool_use block.
        """
        # Initialize clock
        self.start_time = datetime.now()
        self.prev_time = config.get_session_info("time")

        try:
            self.logger.info(f"Processing hawk query: {query}")
            self.current_session = config.get_setting("session")

            self.messages = await config.load_session(self.current_session)
            self.messages = self.sanitize_history(self.messages)
            self.messages = self.messages + [{"role": "user", "content": query}]
            self.logger.info(f"User prompt:\n{query}")

            # Append messages until a SINGULAR text response is received
            while True:
                content_blocks = []
                stop_reason = None

                async for event in self.llm.request(
                    messages=self.messages,
                    tools= await self.list_tools(),
                    system=self.prompts.normal_system(self.current_session)
                ):
                    if event["type"] == "final_message":
                        content_blocks = event["content"]
                        stop_reason = event.get("stop_reason")
                    else:
                        # text_delta / thinking_delta -> forward straight to the UI
                        yield event

                self.messages.append(
                    {
                        "role": "assistant",
                        "content": [self.block_to_dict(b) for b in content_blocks],
                    }
                )
                self.logger.info(f"Assistant message:\n{[self.block_to_dict(b) for b in content_blocks]}")

                # Deal with max token abrupt stopping
                if stop_reason == "max_tokens":
                    self.logger.warning("Response cut off due to max_tokens. Continuing generation...")

                    if content_blocks and getattr(content_blocks[-1], 'type', None) == "tool_use":
                        # remove incomplete tool block
                        self.messages[-1]["content"].pop()
                        continuation_prompt = "Your previous tool call was cut off because the JSON payload was too large. Please generate a SHORTER, more concise tool call, or break the task into smaller, multiple tool calls."
                    else:
                        continuation_prompt = "Your response was cut off due to length limits. Please summarize your thinking process and explain what ."

                    # Anthropic API strictly requires a 'user' turn after an 'assistant' turn
                    self.messages.append({
                        "role": "user",
                        "content": [{"type": "text", "text": continuation_prompt}]
                    })
                    self.logger.info(f"Automated user message (max tokens):\n{continuation_prompt}")

                    # Jumps back to the top of the while loop to stream the rest of the response
                    break #continue

                # Handle all Tool Use Blocks
                tool_use_blocks = [
                    b for b in content_blocks
                    if getattr(b, 'type', None) == "tool_use"
                ]

                if not tool_use_blocks:
                    await config.save_session(self.current_session, self.messages)
                    yield {"type": "done"}
                    break
                else:
                    tool_results = []

                    for tool_use_block in tool_use_blocks:
                        self.logger.info(f"Processing tool: {tool_use_block.name} (ID: {tool_use_block.id})\nInput: {tool_use_block.input}")

                        yield {
                            "type": "tool_use",
                            "name": tool_use_block.name,
                            "input": tool_use_block.input,
                        }

                        # Use the correct tools
                        self.set_current_mcpclient()

                        try:
                            async with self.current_mcpclient:
                                result = await self.current_mcpclient.call_tool(
                                    tool_use_block.name, tool_use_block.input
                                )

                            result_content = [self.block_to_dict(b) for b in result.content]
                            if not result_content:
                                result_content = [{"type": "text", "text": "Tool executed successfully but returned no output."}]

                            is_error = getattr(result, "isError", False)

                            yield_event = {"type": "tool_result", "content": result_content}
                            if is_error: yield_event["is_error"] = True
                            yield yield_event

                            tool_result_block = {
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id,
                                "content": result_content,
                            }
                            if is_error: tool_result_block["is_error"] = True

                        except Exception as e:
                            error_msg = f"Tool validation/execution error: {str(e)}\nPlease review the required arguments for '{tool_use_block.name}' and try again."
                            self.logger.error(f"Tool execution failed: {e}")

                            error_content = [{"type": "text", "text": error_msg}]
                            yield {"type": "tool_result", "content": error_content, "is_error": True}

                            tool_result_block = {
                                "type": "tool_result",
                                "tool_use_id": tool_use_block.id,
                                "content": error_content,
                                "is_error": True
                            }

                        tool_results.append(tool_result_block)

                    # Bundle ALL tool results into a single user message after the loop finishes
                    tool_result_msg = {
                        "role": "user",
                        "content": tool_results,
                    }
                    self.messages.append(tool_result_msg)
                    self.logger.info(f"User tool result:\n{tool_result_msg}")

                # Time logging
                runtime = (datetime.now() - self.start_time).total_seconds() / 60

                if runtime > self.time_limit:
                    self.messages.append({
                        "role": "assistant",
                        "content": f"## ⚠️ The query exceeded the time limit.\n\n**Time limit**:{self.time_limit} mins.\n"
                    })
                    self.logger.info(f"Assistant message:\nThe query exceeded the time limit.\n\n**Time limit**:{self.time_limit} mins.\n")
                    await config.save_session(self.current_session, self.messages)
                    yield {"type": "done"}
                    break

                # Save on every while loop iteration
                await config.save_session(self.current_session, self.messages)


        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            yield {"type": "error", "message": str(e)}
            raise

        finally:
            # Time logging
            runtime = (datetime.now() - self.start_time).total_seconds() / 60
            config.set_session_info(setting_type="time", value=runtime+self.prev_time)

    async def raven_query(self, query: str):
        """ An FSM pentesting loop that streams events to the frontend """
        try:
            self.logger.info(f"Processing raven query: {query}")

            # Initialize clock
            self.start_time = datetime.now()
            self.prev_time = config.get_session_info("time")

            # Load main message history and setup session paths
            self.current_session = config.get_setting("session")
            self.messages = await config.load_session(self.current_session)

            # Sanitize History
            self.messages = self.sanitize_history(self.messages)
            self.recon_messages = self.sanitize_history(self.recon_messages)
            self.va_messages = self.sanitize_history(self.va_messages)
            self.exploit_messages = self.sanitize_history(self.exploit_messages)

            # Frame the initial query or append to existing history
            if self.messages == []:
                prompt_framing = "The target's IP and/or domain name to initiate the penetration testing process is: "
                user_message = {"role": "user", "content": prompt_framing + query}
                self.messages.append(user_message)
                self.recon_messages.append(user_message)
                self.stage = "recon-planning"
            else:
                user_message = {"role": "user", "content": query}
                self.messages.append(user_message)
                self.stage = config.get_session_info("stage")
                if "recon" in self.stage: self.recon_messages.append(user_message)
                elif "va" in self.stage: self.va_messages.append(user_message)
                elif "exploit" in self.stage: self.exploit_messages.append(user_message)

            # Main FSM Loop
            while True:
                # 1. Determine current stage context
                current_messages = []
                system_prompt = ""
                agent_name = ""

                if self.stage == "recon-planning":
                    current_messages = self.recon_messages
                    system_prompt = self.prompts.planner_system("recon", self.current_session)
                    agent_name = "Recon Planner"
                elif self.stage == "recon":
                    current_messages = self.recon_messages
                    system_prompt = self.prompts.executor_system("recon", self.current_session)
                    agent_name = "Recon Executor"
                elif self.stage == "va-planning":
                    current_messages = self.va_messages
                    system_prompt = self.prompts.planner_system("va", self.current_session)
                    agent_name = "VA Planner"
                elif self.stage == "va":
                    current_messages = self.va_messages
                    system_prompt = self.prompts.executor_system("va", self.current_session)
                    agent_name = "VA Executor"
                elif self.stage == "exploit-planning":
                    current_messages = self.exploit_messages
                    system_prompt = self.prompts.planner_system("exploit", self.current_session)
                    agent_name = "Exploit Planner"
                elif self.stage == "exploit":
                    current_messages = self.exploit_messages
                    system_prompt = self.prompts.executor_system("exploit", self.current_session)
                    agent_name = "Exploit Executor"
                elif self.stage == "finale":
                    current_messages = self.messages
                    system_prompt = self.prompts.curtain_caller_system(self.current_session)
                    agent_name = "Curtain Caller"
                else:
                    self.logger.error(f"Unknown stage: {self.stage}")
                    yield {"type": "error", "message": f"Unknown stage: {self.stage}"}
                    break

                # LLM request and Tool Use for the current stage
                stage_finished = False
                while not stage_finished:
                    content_blocks = []
                    stop_reason = None

                    # Stream LLM response
                    async for event in self.llm.request(
                        messages=current_messages,
                        tools=await self.list_tools(),
                        system=system_prompt,
                        name=agent_name
                    ):
                        if event["type"] == "final_message":
                            content_blocks = event["content"]
                            stop_reason = event.get("stop_reason")
                        else:
                            yield event

                    # Append assistant response to histories
                    assistant_msg = {
                        "role": "assistant",
                        "content": [self.block_to_dict(b) for b in content_blocks]
                    }
                    # Append messages to general and specific messages array
                    self.messages.append(assistant_msg)
                    if (current_messages is not self.messages):
                        current_messages.append(assistant_msg)

                    # Deal with max token abrupt stopping
                    if stop_reason == "max_tokens":
                        self.logger.warning("Response cut off due to max_tokens. Continuing generation...")

                        # SAFETY CHECK: If it cut off inside a tool_use block, the JSON input is truncated/invalid.
                        # The API will reject the history if we send invalid JSON back to it.
                        # We pop the partial tool block and ask it to regenerate the full tool call.
                        if content_blocks and getattr(content_blocks[-1], 'type', None) == "tool_use":
                            # Remove invalid block from general and specific messages
                            self.messages[-1]["content"].pop()
                            if (current_messages is not self.messages):
                                current_messages[-1]["content"].pop()
                            continuation_prompt = "Your response was cut off while formatting a tool call. Please output the complete tool_use block now."
                        else:
                            continuation_prompt = "Your response was cut off due to length limits. Please continue exactly where you left off without repeating yourself."

                        # Anthropic API strictly requires a 'user' turn after an 'assistant' turn
                        self.messages.append({
                            "role": "user",
                            "content": [{"type": "text", "text": continuation_prompt}]
                        })
                        if (current_messages is not self.messages):
                            current_messages.append({
                                "role": "user",
                                "content": [{"type": "text", "text": continuation_prompt}]
                            })

                        # Jumps back to the top of the while loop to stream the rest of the response
                        continue

                    # Handle all Tool Use Blocks
                    tool_use_blocks = [b for b in content_blocks if getattr(b, 'type', None) == "tool_use"]

                    if not tool_use_blocks:
                        stage_finished = True
                    else:
                        tool_results = []

                        for tool_use_block in tool_use_blocks:
                            self.logger.info(f"Processing tool: {tool_use_block.name} (ID: {tool_use_block.id})\nInput: {tool_use_block.input}")

                            yield {
                                "type": "tool_use",
                                "name": tool_use_block.name,
                                "input": tool_use_block.input,
                            }

                            # Use the correct tools
                            self.set_current_mcpclient()

                            try:
                                async with self.current_mcpclient:
                                    result = await self.current_mcpclient.call_tool(
                                        tool_use_block.name, tool_use_block.input
                                    )

                                result_content = [self.block_to_dict(b) for b in result.content]
                                is_error = getattr(result, "isError", False)

                                yield_event = {"type": "tool_result", "content": result_content}
                                if is_error: yield_event["is_error"] = True
                                yield yield_event

                                tool_result_block = {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_block.id,
                                    "content": result_content,
                                }
                                if is_error: tool_result_block["is_error"] = True

                            except Exception as e:
                                error_msg = f"Tool validation/execution error: {str(e)}\nPlease review the required arguments for '{tool_use_block.name}' and try again."
                                self.logger.error(f"Tool execution failed: {e}")

                                error_content = [{"type": "text", "text": error_msg}]
                                yield {"type": "tool_result", "content": error_content, "is_error": True}

                                tool_result_block = {
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_block.id,
                                    "content": error_content,
                                    "is_error": True
                                }

                            tool_results.append(tool_result_block)

                        # Bundle ALL tool results into a single user message
                        tool_result_msg = {
                            "role": "user",
                            "content": tool_results,
                        }
                        self.messages.append(tool_result_msg)
                        if (current_messages is not self.messages):
                            current_messages.append(tool_result_msg)

                # Save session after each stage
                await config.save_session(self.current_session, self.messages)
                self.logger.info(f"Successfully saved session after completing stage: {self.stage}")

                # Time logging
                runtime = (datetime.now() - self.start_time).total_seconds() / 60
                config.set_session_info(setting_type="time", value=runtime+self.prev_time)

                # Stage Transition Logic (Autopilot)
                next_stage = None
                auto_prompt = None

                if self.stage == "recon-planning":
                    next_stage = "recon"
                    config.set_session_info("stage", "recon")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Plan approved, proceed."
                elif self.stage == "recon":
                    next_stage = "va-planning"
                    config.set_session_info("stage", "va-planning")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Initialize the vulnerability assessment planning process."
                elif self.stage == "va-planning":
                    next_stage = "va"
                    config.set_session_info("stage", "va")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Plan approved, proceed."
                elif self.stage == "va":
                    next_stage = "exploit-planning"
                    config.set_session_info("stage", "exploit-planning")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Initialize the exploitation planning process."
                elif self.stage == "exploit-planning":
                    next_stage = "exploit"
                    config.set_session_info("stage", "exploit")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Plan approved, proceed."
                elif self.stage == "exploit":
                    next_stage = "finale"
                    config.set_session_info("stage", "finale")
                    yield {"type": "stage_update", "stage": next_stage}
                    auto_prompt = "Initialize the pentesting summarization process."
                elif self.stage == "finale":
                    next_stage = "recon-planning"
                    config.set_session_info("stage", "recon-planning")
                    yield {"type": "stage_update", "stage": next_stage}
                    yield {"type": "done"}
                    break

                # Check if user approval is needed
                try:
                    is_report_mode = config.get_session_info("report")
                except Exception:
                    is_report_mode = True
                # Break condition 2: Reporting mode enabled
                if is_report_mode and self.stage.endswith("-planning"):
                    yield {"type": "done"}
                    break

                # Break condition 3: Time limit reached
                if runtime > self.time_limit:
                    self.messages.append({
                        "role": "assistant",
                        "content": f"## ⚠️ The query exceeded the time limit.\n\n**Time limit**:{self.time_limit} mins.\n"
                    })
                    yield {"type": "done"}
                    break

                # Autopilot next stage preparations
                if next_stage:
                    self.stage = next_stage
                    if "recon" in next_stage:
                        self.messages.append({"role": "user", "content": auto_prompt})
                        self.recon_messages.append({"role": "user", "content": auto_prompt})
                    elif "va" in next_stage:
                        self.messages.append({"role": "user", "content": auto_prompt})
                        self.va_messages.append({"role": "user", "content": auto_prompt})
                    elif "exploit" in next_stage:
                        self.messages.append({"role": "user", "content": auto_prompt})
                        self.exploit_messages.append({"role": "user", "content": auto_prompt})
                    elif next_stage == "finale":
                        self.messages.append({"role": "user", "content": auto_prompt})

        except Exception as e:
            self.logger.error(f"Error in raven query: {e}")
            yield {"type": "error", "message": str(e)}
            raise

    def sanitize_history(self, messages):
        """
        Bulletproof cleanup: Ensures every tool_use block has a valid tool_result
        in the immediately following user message. Fixes crashes and empty returns.
        """
        i = 0
        while i < len(messages):
            msg = messages[i]

            # Check if this is an assistant message with tool_use blocks
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), list):
                tool_use_ids = [
                    block.get("id") for block in msg["content"]
                    if isinstance(block, dict) and block.get("type") == "tool_use"
                ]

                if tool_use_ids:
                    # Look at the next message
                    next_msg = messages[i+1] if i + 1 < len(messages) else None

                    # Ensure next_msg is a valid user message with a list content
                    if not next_msg or next_msg.get("role") != "user" or not isinstance(next_msg.get("content"), list):
                        # Create a new user message for the results and insert it
                        next_msg = {"role": "user", "content": []}
                        messages.insert(i+1, next_msg)

                    # Now next_msg is guaranteed to be a user message with a list content
                    result_ids = [
                        block.get("tool_use_id") for block in next_msg["content"]
                        if isinstance(block, dict) and block.get("type") == "tool_result"
                    ]

                    # Find missing IDs
                    missing_ids = [tid for tid in tool_use_ids if tid not in result_ids]

                    if missing_ids:
                        # Inject dummy results for missing IDs directly into next_msg
                        for tid in missing_ids:
                            next_msg["content"].append({
                                "type": "tool_result",
                                "tool_use_id": tid,
                                "content": [{"type": "text", "text": "Error: Tool execution was interrupted or returned no data."}],
                                "is_error": True
                            })
            i += 1
        return messages
