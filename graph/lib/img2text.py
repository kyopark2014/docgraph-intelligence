"""Image → Markdown via AWS Bedrock Mantle multimodal (Foundation Model Parser).

Self-contained helpers for ``graph/pdf2text.py`` — no ``application`` imports.
"""

from __future__ import annotations

import base64
import logging
import os
import traceback
from io import BytesIO
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from PIL import Image

logger = logging.getLogger(__name__)

# Match application/info.py OpenAI GPT 5.6 Sol profile[0]
DEFAULT_MODEL_ID = "openai.gpt-5.6-sol"
DEFAULT_MANTLE_REGION = "us-east-1"
DEFAULT_PROMPT = (
    "텍스트를 추출해서 markdown 포맷으로 변환하세요. <result> tag를 붙여주세요."
)


def _mantle_region() -> str:
    return (
        (os.getenv("GRAPHIFY_IMG2TEXT_REGION") or "").strip()
        or (os.getenv("GRAPHIFY_BEDROCK_REGION") or "").strip()
        or DEFAULT_MANTLE_REGION
    )


def _mantle_model_id() -> str:
    return (
        (os.getenv("GRAPHIFY_IMG2TEXT_MODEL") or "").strip()
        or (os.getenv("GRAPHIFY_BEDROCK_MODEL") or "").strip()
        or DEFAULT_MODEL_ID
    )


def _bedrock_bearer_token(region: str) -> str:
    token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if token:
        return token
    from aws_bedrock_token_generator import provide_token

    return provide_token(region=region)


def _get_chat() -> ChatOpenAI:
    """Create OpenAI Mantle chat model for text extraction."""
    region = _mantle_region()
    model_id = _mantle_model_id()

    def bearer_token_provider() -> str:
        return _bedrock_bearer_token(region)

    return ChatOpenAI(
        model=model_id,
        api_key=bearer_token_provider,
        base_url=f"https://bedrock-mantle.{region}.api.aws/openai/v1",
        use_responses_api=True,
        max_tokens=8192,
    )


def prepare_image_base64(
    image_content: bytes,
    max_size: int = 5 * 1024 * 1024,
    max_pixels: int = 2000000,
) -> str:
    """Resize image if needed and return base64 string."""
    img = Image.open(BytesIO(image_content))
    width, height = img.size
    logger.info("Image size: %sx%s, pixels: %s", width, height, width * height)

    is_resized = False
    while width * height > max_pixels:
        width = int(width / 2)
        height = int(height / 2)
        is_resized = True
        logger.info("Resized to %sx%s", width, height)

    if is_resized:
        img = img.resize((width, height))

    for attempt in range(5):
        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        base64_size = len(img_base64.encode("utf-8"))
        logger.info("Attempt %s: base64_size = %s bytes", attempt + 1, base64_size)

        if base64_size <= max_size:
            return img_base64

        width = int(width * 0.8)
        height = int(height * 0.8)
        img = img.resize((width, height))
        logger.info("Resizing to %sx%s due to size limit", width, height)

    raise ValueError("이미지 크기가 너무 큽니다. 5MB 이하의 이미지를 사용해주세요.")


def _content_to_text(content: object) -> str:
    """Normalize LangChain/Bedrock message content to a plain string."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
                elif item.get("type") == "text" and item.get("text"):
                    parts.append(str(item["text"]))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "\n".join(parts).strip()
    return str(content).strip()


def extract_text_with_llm(img_base64: str, prompt: Optional[str] = None) -> str:
    """Extract text from image using Bedrock Mantle multimodal LLM."""
    query = prompt or DEFAULT_PROMPT

    multimodal = _get_chat()
    messages = [
        HumanMessage(
            content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_base64}"},
                },
                {"type": "text", "text": query},
            ]
        )
    ]

    extracted_text = ""
    for attempt in range(5):
        logger.info("LLM attempt: %s", attempt)
        try:
            result = multimodal.invoke(messages)
            raw = result.content
            extracted_text = _content_to_text(raw)
            logger.info(
                "LLM content type=%s raw_len=%s text_len=%s",
                type(raw).__name__,
                len(raw) if hasattr(raw, "__len__") else "n/a",
                len(extracted_text),
            )
            break
        except Exception:
            logger.warning("LLM error: %s", traceback.format_exc())

    if len(extracted_text) < 10:
        logger.warning(
            "LLM returned too little text (len=%s); marking as extraction failure",
            len(extracted_text),
        )
        extracted_text = "텍스트를 추출하지 못하였습니다."

    return extracted_text


def parse_result(text: str) -> str:
    """Extract content from <result> tag if present."""
    if text.find("<result>") != -1:
        return text[text.find("<result>") + 8 : text.find("</result>")]
    return text


# Aliases matching the former application.mcp_server_text_extraction API
_prepare_image_base64 = prepare_image_base64
_extract_text_with_llm = extract_text_with_llm
_parse_result = parse_result
