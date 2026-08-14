from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.orchestration.orchestrator import ChatResult
    from packages.orchestration.orchestrator import GaiaOrchestrator
    from packages.tools import ToolExecutionContext


JsonDict = dict[str, Any]


try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when optional dependency is absent.
    END = "__end__"
    StateGraph = None
    LANGGRAPH_AVAILABLE = False


@dataclass(frozen=True, slots=True)
class GuidanceGraphSummary:
    engine: str
    entrypoint: str
    nodes: list[str]
    edges: list[tuple[str, str]]
    legacy_orchestrator_preserved: bool = True
    services_wrapped_not_reimplemented: bool = True

    def to_dict(self) -> JsonDict:
        return {
            "engine": self.engine,
            "entrypoint": self.entrypoint,
            "nodes": self.nodes,
            "edges": [f"{left}->{right}" for left, right in self.edges],
            "legacy_orchestrator_preserved": self.legacy_orchestrator_preserved,
            "services_wrapped_not_reimplemented": self.services_wrapped_not_reimplemented,
        }


class GuidanceWorkflowGraph:
    def __init__(self, orchestrator: GaiaOrchestrator) -> None:
        self.orchestrator = orchestrator
        self._compiled = self._compile_langgraph() if LANGGRAPH_AVAILABLE else None

    async def run(
        self,
        *,
        context: ToolExecutionContext,
        conversation_id: str,
        user_message_id: str,
        message: str,
        location_id: str | None,
        user_plant_id: str | None,
    ) -> ChatResult:
        state: JsonDict = {
            "context": context,
            "conversation_id": conversation_id,
            "user_message_id": user_message_id,
            "message": message,
            "location_id": location_id,
            "user_plant_id": user_plant_id,
            "route": None,
            "result": None,
        }
        if self._compiled is not None:
            final_state = await self._compiled.ainvoke(state)
        else:
            final_state = await self._run_compat(state)
        result = final_state.get("result")
        if result is None:
            raise RuntimeError("Guidance graph completed without a ChatResult")
        return result

    def summary(self) -> GuidanceGraphSummary:
        return GuidanceGraphSummary(
            engine="langgraph" if self._compiled is not None else "langgraph-compatible-local",
            entrypoint="classify_route",
            nodes=[
                "classify_route",
                "geography",
                "environment",
                "economics",
                "season",
                "reasoning",
            ],
            edges=[
                ("classify_route", "geography|environment|economics|season|reasoning"),
                ("geography", "END"),
                ("environment", "END"),
                ("economics", "END"),
                ("season", "END"),
                ("reasoning", "END"),
            ],
        )

    def _compile_langgraph(self):
        graph = StateGraph(dict)
        graph.add_node("classify_route", self._classify_route_node)
        graph.add_node("geography", self._geography_node)
        graph.add_node("environment", self._environment_node)
        graph.add_node("economics", self._economics_node)
        graph.add_node("season", self._season_node)
        graph.add_node("reasoning", self._reasoning_node)
        graph.set_entry_point("classify_route")
        graph.add_conditional_edges(
            "classify_route",
            lambda state: state["route"],
            {
                "geography": "geography",
                "environment": "environment",
                "economics": "economics",
                "season": "season",
                "reasoning": "reasoning",
            },
        )
        for node in ["geography", "environment", "economics", "season", "reasoning"]:
            graph.add_edge(node, END)
        return graph.compile()

    async def _run_compat(self, state: JsonDict) -> JsonDict:
        state.update(await self._classify_route_node(state))
        route = state["route"]
        if route == "geography":
            state.update(await self._geography_node(state))
        elif route == "environment":
            state.update(await self._environment_node(state))
        elif route == "economics":
            state.update(await self._economics_node(state))
        elif route == "season":
            state.update(await self._season_node(state))
        else:
            state.update(await self._reasoning_node(state))
        return state

    async def _classify_route_node(self, state: JsonDict) -> JsonDict:
        from packages.orchestration.orchestrator import classify_route

        route = classify_route(str(state["message"]))
        if route == "economics" and self.orchestrator.mercator_context_provider is None:
            route = "reasoning"
        if route == "season" and (self.orchestrator.season is None or self.orchestrator.season_context_provider is None):
            route = "reasoning"
        return {**state, "route": route}

    async def _geography_node(self, state: JsonDict) -> JsonDict:
        return {
            **state,
            "result": await self.orchestrator._handle_geography(
                state["context"],
                state["conversation_id"],
                state["user_message_id"],
                state["location_id"],
            )
        }

    async def _environment_node(self, state: JsonDict) -> JsonDict:
        return {
            **state,
            "result": await self.orchestrator._handle_environment(
                state["context"],
                state["conversation_id"],
                state["user_message_id"],
                state["location_id"],
            )
        }

    async def _economics_node(self, state: JsonDict) -> JsonDict:
        return {
            **state,
            "result": await self.orchestrator._handle_economics(
                state["context"],
                state["conversation_id"],
                state["user_message_id"],
                state["location_id"],
                state["message"],
                state["user_plant_id"],
            )
        }

    async def _season_node(self, state: JsonDict) -> JsonDict:
        return {
            **state,
            "result": await self.orchestrator._handle_season(
                state["context"],
                state["conversation_id"],
                state["user_message_id"],
                state["location_id"],
                state["message"],
            )
        }

    async def _reasoning_node(self, state: JsonDict) -> JsonDict:
        return {
            **state,
            "result": await self.orchestrator._handle_reasoning(
                state["context"],
                state["conversation_id"],
                state["user_message_id"],
                state["location_id"],
                state["message"],
                state["user_plant_id"],
            )
        }
