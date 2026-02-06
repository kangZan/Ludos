"""Async LLM client wrapper with structured output support."""

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.config.settings import settings
from src.utils.json_parser import extract_json
from src.utils.errors import RuntimeWorkflowError

logger = structlog.get_logger(__name__)

_llm_instance: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    """Get or create the shared LLM instance."""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.7,
        )
    return _llm_instance


def _supports_structured_output() -> bool:
    """Return True if the current backend supports structured output."""
    base_url = settings.llm_base_url.lower()
    model = settings.llm_model.lower()
    if "deepseek" in base_url or "deepseek" in model:
        return False
    return True


async def call_llm(
    system_prompt: str,
    user_message: str,
    response_format: type[BaseModel] | None = None,
    temperature: float | None = None,
    max_retries: int = 2,
) -> dict:
    """Call the LLM with optional structured output.

    Args:
        system_prompt: System message for the LLM.
        user_message: User/human message content.
        response_format: Optional Pydantic model for structured output.
        temperature: Override default temperature.
        max_retries: Number of retries on parse failure.

    Returns:
        Parsed dict from LLM response.
    """
    llm = get_llm()
    if temperature is not None:
        llm = llm.with_config({"temperature": temperature})

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]

    for attempt in range(max_retries + 1):
        try:
            if response_format is not None and _supports_structured_output():
                structured_llm = llm.with_structured_output(response_format)
                result = await structured_llm.ainvoke(messages)
                if isinstance(result, BaseModel):
                    return result.model_dump()
                return dict(result)  # type: ignore[arg-type]

            response = await llm.ainvoke(messages)
            content = str(response.content)
            parsed = extract_json(content)
            if parsed is not None:
                return parsed

            return {"content": content}

        except Exception as exc:
            # If structured output fails on an unsupported backend, retry without it.
            if response_format is not None and not _supports_structured_output():
                response = await llm.ainvoke(messages)
                content = str(response.content)
                parsed = extract_json(content)
                if parsed is not None:
                    return parsed
                return {"content": content}
            if attempt < max_retries:
                logger.warning(
                    "llm_call_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                continue
            logger.error("llm_call_failed", attempts=max_retries + 1)
            raise RuntimeWorkflowError("LLM call failed") from exc

    raise RuntimeError("Unreachable: all retries exhausted")
