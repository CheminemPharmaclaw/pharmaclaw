"""
BaseAgent — Foundation for all PharmaClaw AI agents.

Handles LLM communication, tool dispatch, and conversation management.
Supports any provider via litellm (OpenAI, Anthropic, Ollama, Gemini, etc.).
"""

import json
from typing import Any, Callable

try:
    import litellm
    litellm.drop_params = True  # Gracefully handle unsupported params
    _HAS_LITELLM = True
except ImportError:
    _HAS_LITELLM = False


def _check_litellm():
    if not _HAS_LITELLM:
        raise ImportError(
            "AI agents require litellm. Install with:\n"
            "  pip install pharmaclaw[agents]\n"
            "or:\n"
            "  pip install litellm"
        )


class BaseAgent:
    """Base class for all PharmaClaw AI agents.

    Args:
        api_key: Your LLM provider API key (e.g., OpenAI sk-..., Anthropic sk-ant-...).
        model: Model name. Defaults to 'gpt-4o-mini' (cheap and good).
            Examples: 'gpt-4o', 'claude-sonnet-4-20250514', 'ollama/llama3', 'gemini/gemini-pro'.
        provider: Optional provider hint ('openai', 'anthropic', 'ollama', etc.).
            Usually auto-detected from model name.
        base_url: Optional custom API endpoint (for Ollama, vLLM, etc.).
        temperature: LLM temperature (0.0 = deterministic, 1.0 = creative). Default 0.1.
        verbose: Print tool calls and reasoning to stderr.

    Example:
        >>> from pharmaclaw.agents import ChemistryAgent
        >>> agent = ChemistryAgent(api_key="sk-...")
        >>> result = agent.ask("What is the molecular weight of aspirin?")
    """

    # Subclasses override these
    AGENT_NAME: str = "base"
    SYSTEM_PROMPT: str = "You are a helpful assistant."
    TOOLS: list[dict] = []
    TOOL_FUNCTIONS: dict[str, Callable] = {}

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        provider: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.1,
        verbose: bool = False,
    ):
        _check_litellm()
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.base_url = base_url
        self.temperature = temperature
        self.verbose = verbose
        self._history: list[dict] = []

    def _call_llm(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Call the LLM with messages and optional tool definitions."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = litellm.completion(**kwargs)
        return response

    def _execute_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool function and return JSON string result."""
        fn = self.TOOL_FUNCTIONS.get(name)
        if fn is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = fn(**arguments)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def ask(self, question: str, reset: bool = False) -> dict:
        """Ask the agent a question in natural language.

        Args:
            question: Your question or task description.
            reset: If True, clear conversation history first.

        Returns:
            dict with 'answer' (str), 'tool_calls' (list), and 'data' (dict).
        """
        if reset:
            self._history = []

        # Build messages
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": question})

        tool_calls_log = []
        collected_data = {}
        max_iterations = 10  # Safety limit

        for _ in range(max_iterations):
            response = self._call_llm(messages, self.TOOLS if self.TOOLS else None)
            choice = response.choices[0]
            msg = choice.message

            # If the model wants to call tools
            if msg.tool_calls:
                # Add assistant message with tool calls
                messages.append(msg.model_dump())

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}

                    if self.verbose:
                        import sys
                        print(f"  🔧 {fn_name}({json.dumps(fn_args, default=str)[:200]})", file=sys.stderr)

                    result_str = self._execute_tool(fn_name, fn_args)
                    tool_calls_log.append({
                        "tool": fn_name,
                        "args": fn_args,
                        "result": json.loads(result_str) if result_str else None,
                    })

                    # Store tool results for structured output
                    try:
                        collected_data[fn_name] = json.loads(result_str)
                    except Exception:
                        collected_data[fn_name] = result_str

                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                # Continue loop — model may want to call more tools or respond
                continue

            # No tool calls — model is done, return the response
            answer = msg.content or ""

            # Update conversation history
            self._history.append({"role": "user", "content": question})
            self._history.append({"role": "assistant", "content": answer})

            return {
                "agent": self.AGENT_NAME,
                "answer": answer,
                "tool_calls": tool_calls_log,
                "data": collected_data,
            }

        # If we hit max iterations
        return {
            "agent": self.AGENT_NAME,
            "answer": "Reached maximum tool call iterations.",
            "tool_calls": tool_calls_log,
            "data": collected_data,
        }

    def clear_history(self):
        """Clear conversation history."""
        self._history = []

    def __repr__(self):
        return f"{self.__class__.__name__}(model={self.model!r})"
