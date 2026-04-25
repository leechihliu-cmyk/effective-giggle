import json
import re
from config import get_anthropic_client, CLAUDE_MODEL


class AgentError(Exception):
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"[{agent_name}] {message}")


class BaseAgent:
    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt
        self.client = get_anthropic_client()

    def call(
        self,
        user_message: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        response_format: str = "json",
    ) -> dict | str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text

        if response_format == "json":
            return self._extract_json(raw)
        return raw

    def _extract_json(self, raw: str) -> dict:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise AgentError(self.name, f"JSON 파싱 실패:\n{raw[:300]}")
