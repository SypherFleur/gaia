from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    TOOL_READ = "tool.read"
    CALENDAR_READ = "calendar.read"
    CALENDAR_CREATE = "calendar.create"
    CALENDAR_UPDATE = "calendar.update"
    CALENDAR_DELETE = "calendar.delete"
    REGULATION_READ = "regulation.read"
    RESEARCH_READ = "research.read"
    MARKET_READ = "market.read"
    VISION_ANALYZE = "vision.analyze"
    MODEL_CHAT = "model.chat"
    ADMIN_PROVIDER_CONFIGURE = "admin.provider.configure"
    ADMIN_COST_CONFIGURE = "admin.cost.configure"
