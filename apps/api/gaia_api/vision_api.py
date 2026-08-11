from __future__ import annotations

from dataclasses import asdict

from packages.tools import ToolExecutionContext
from packages.vision import VisionAnalysisTool, VisionService


async def post_vision_media(
    vision: VisionService,
    context: ToolExecutionContext,
    *,
    image_base64: str,
    content_type: str = "image/jpeg",
    user_plant_id: str | None = None,
) -> dict:
    media = await vision.create_image_attachment(
        context,
        image_base64=image_base64,
        content_type=content_type,
        user_plant_id=user_plant_id,
    )
    public = asdict(media)
    public["metadata"] = {key: value for key, value in public["metadata"].items() if key != "inline_base64"}
    return public


async def post_vision_analyze(
    vision: VisionService,
    context: ToolExecutionContext,
    *,
    tool: VisionAnalysisTool,
    media_attachment_id: str,
    user_plant_id: str | None = None,
    location_id: str | None = None,
    prompt: str = "Describe visible plant evidence and cautious hypotheses.",
) -> dict:
    result = await vision.analyze_attachment(
        context,
        tool=tool,
        media_attachment_id=media_attachment_id,
        user_plant_id=user_plant_id,
        location_id=location_id,
        prompt=prompt,
    )
    return {
        "visual_analysis": asdict(result.visual_analysis),
        "provider_status": result.provider_result.status,
        "warnings": result.provider_result.warnings,
        "observation_id": result.observation_id,
    }

