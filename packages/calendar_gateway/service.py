from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta

from packages.calendar_gateway.tools import CalendarCreateEventTool
from packages.domain import CalendarEventBinding, CalendarPreview
from packages.domain.models import now_iso
from packages.persistence import GaiaRepository
from packages.tools import ToolExecutionContext, ToolGateway, ToolRequest


class CalendarWorkflowService:
    def __init__(self, *, repository: GaiaRepository, tool_gateway: ToolGateway, create_tool: CalendarCreateEventTool) -> None:
        self.repository = repository
        self.tool_gateway = tool_gateway
        self.create_tool = create_tool

    def preview_events(self, context: ToolExecutionContext, *, season_plan_id: str, calendar_binding_id: str) -> CalendarPreview:
        plan = self.repository.get_season_plan(context.organization_id, season_plan_id)
        if plan is None:
            raise PermissionError("SeasonPlan is missing or inaccessible")
        binding = self.repository.get_calendar_binding(context.organization_id, calendar_binding_id)
        if binding is None:
            raise PermissionError("CalendarBinding is missing or inaccessible")
        actions = self.repository.list_actions_for_season_plan(context.organization_id, season_plan_id)
        event_previews = [_event_preview(plan, binding, action) for action in actions if action.get("preferred_at")]
        preview = CalendarPreview(
            organization_id=context.organization_id,
            workspace_id=context.workspace_id,
            season_plan_id=season_plan_id,
            plan_version=int(plan["version"]),
            calendar_binding_id=calendar_binding_id,
            event_previews=event_previews,
            status="preview",
            expires_at=(datetime.fromisoformat(now_iso()) + timedelta(hours=4)).isoformat(),
        )
        return self.repository.create_calendar_preview(preview)

    async def commit_preview(self, context: ToolExecutionContext, *, preview_id: str) -> dict:
        preview = self.repository.get_calendar_preview(context.organization_id, preview_id)
        if preview is None:
            raise PermissionError("CalendarPreview is missing or inaccessible")
        plan = self.repository.get_season_plan(context.organization_id, preview["season_plan_id"])
        if plan is None:
            raise PermissionError("SeasonPlan is missing or inaccessible")
        if int(plan["version"]) != int(preview["plan_version"]):
            return {"status": "STALE_PREVIEW", "created": [], "warnings": ["plan_version_changed"]}
        if preview["status"] == "committed":
            existing = self.repository.list_calendar_event_bindings_for_plan(context.organization_id, plan["id"])
            return {"status": "ALREADY_COMMITTED", "created": existing, "warnings": []}
        binding = self.repository.get_calendar_binding(context.organization_id, preview["calendar_binding_id"])
        if binding is None:
            raise PermissionError("CalendarBinding is missing or inaccessible")
        created = []
        warnings = []
        for item in preview["event_previews"]:
            existing = self.repository.find_calendar_event_binding(context.organization_id, item["action_id"], binding["id"], int(preview["plan_version"]))
            if existing is not None:
                created.append(existing)
                continue
            result = await self.tool_gateway.execute(
                self.create_tool,
                context,
                ToolRequest(
                    payload={
                        "credential_reference": binding.get("credential_reference") or binding.get("encrypted_credential_reference"),
                        "calendar_id": binding["external_calendar_id"],
                        "summary": item["summary"],
                        "description": item["description"],
                        "start": item["start"],
                        "end": item["end"],
                        "recurrence": item.get("recurrence", []),
                        "extended_properties": item.get("extended_properties", {}),
                    },
                    estimated_cost_usd=0.0,
                    contains_private_text=True,
                    contains_exact_location=False,
                ),
            )
            if result.status != "success":
                warnings.extend(result.warnings or [result.denial_reason or result.status])
                continue
            event_binding = self.repository.create_calendar_event_binding(
                CalendarEventBinding(
                    organization_id=context.organization_id,
                    action_id=item["action_id"],
                    calendar_binding_id=binding["id"],
                    external_event_id=result.data["external_event_id"],
                    plan_version=int(preview["plan_version"]),
                    status="created",
                )
            )
            created.append(asdict(event_binding))
        if created and not warnings:
            self.repository.mark_calendar_preview_committed(context.organization_id, preview_id, now_iso())
        return {"status": "COMMITTED" if created and not warnings else "PARTIAL_OR_FAILED", "created": created, "warnings": warnings}


def _event_preview(plan: dict, binding: dict, action: dict) -> dict:
    timezone = (plan.get("date_range") or {}).get("timezone", "UTC")
    start = _calendar_time(action["preferred_at"], timezone)
    duration = int(action.get("duration_minutes") or 30)
    start_dt = datetime.fromisoformat(action["preferred_at"])
    end_dt = start_dt + timedelta(minutes=duration)
    recurrence = _recurrence(action)
    return {
        "action_id": action["id"],
        "calendar_binding_id": binding["id"],
        "summary": f"GAIA - {action['title']}",
        "description": _description(plan, action),
        "start": start,
        "end": _calendar_time(end_dt.isoformat(), timezone),
        "recurrence": recurrence,
        "extended_properties": {"private": {"gaia_action_id": action["id"], "gaia_plan_id": plan["id"], "gaia_plan_version": str(plan["version"])}},
    }


def _calendar_time(value: str, timezone: str) -> dict:
    dt = datetime.fromisoformat(value)
    return {"dateTime": dt.isoformat(), "timeZone": timezone}


def _description(plan: dict, action: dict) -> str:
    return "\n".join(
        [
            f"Task: {action['instructions']}",
            f"Plan: {plan.get('name') or plan.get('objective')}",
            f"Crop/plant: {action.get('plant_or_crop_id') or 'general'}",
            f"GAIA Action ID: {action['id']}",
            "Exact private coordinates are not included.",
        ]
    )


def _recurrence(action: dict) -> list[str]:
    recurrence = action.get("recurrence") or {}
    frequency = recurrence.get("frequency")
    if frequency == "weekly":
        return [f"RRULE:FREQ=WEEKLY;COUNT={int(recurrence.get('count', 4))}"]
    if frequency == "every_2_days":
        return ["RRULE:FREQ=DAILY;INTERVAL=2;COUNT=6"]
    return []
