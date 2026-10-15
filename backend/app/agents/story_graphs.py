"""LangGraph workflows for Story Analysis and Screenplay Generation.

Implements typed state, nodes, and bounded schema-repair loops (FRD §8, §11).
"""

from __future__ import annotations

import logging
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph
from pydantic import ValidationError

from app.providers.base import TextProvider
from app.schemas.story import ProductionSettings, Screenplay, StoryBible

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- Story Analysis Graph
class StoryAnalysisState(TypedDict):
    story_text: str
    genre: str
    tone: str
    language: str
    story_bible: dict[str, Any] | None
    error: str | None
    repair_attempts: int
    raw_invalid_json: str | None


def build_story_analysis_graph(text_provider: TextProvider, max_repair_attempts: int = 2):
    def analyze_node(state: StoryAnalysisState) -> StoryAnalysisState:
        try:
            bible = text_provider.analyze_story(
                story_text=state["story_text"],
                genre=state["genre"],
                tone=state["tone"],
                language=state["language"],
            )
            return {
                **state,
                "story_bible": bible.model_dump(),
                "error": None,
                "raw_invalid_json": None,
            }
        except ValidationError as val_err:
            return {
                **state,
                "error": str(val_err),
                "raw_invalid_json": getattr(val_err, "json", lambda: str(val_err))(),
            }
        except Exception as exc:
            return {**state, "error": f"Story extraction failed: {exc}"}

    def repair_node(state: StoryAnalysisState) -> StoryAnalysisState:
        attempts = state.get("repair_attempts", 0) + 1
        logger.info("LangGraph repair loop: attempt %d for StoryBible", attempts)
        try:
            repaired_bible = text_provider.repair_json(
                invalid_json=state.get("raw_invalid_json") or "",
                target_schema=StoryBible,
                error_context=state.get("error") or "",
            )
            return {
                **state,
                "story_bible": repaired_bible.model_dump(),
                "error": None,
                "repair_attempts": attempts,
            }
        except Exception as exc:
            return {
                **state,
                "error": f"Repair attempt {attempts} failed: {exc}",
                "repair_attempts": attempts,
            }

    def decide_analysis_next(state: StoryAnalysisState) -> str:
        if state.get("story_bible") is not None:
            return END
        if state.get("repair_attempts", 0) < max_repair_attempts and state.get("raw_invalid_json"):
            return "repair"
        return END

    workflow = StateGraph(StoryAnalysisState)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("repair", repair_node)
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges("analyze", decide_analysis_next, {"repair": "repair", END: END})
    workflow.add_conditional_edges("repair", decide_analysis_next, {"repair": "repair", END: END})
    return workflow.compile()


# ---------------------------------------------------------------- Screenplay Graph
class ScreenplayState(TypedDict):
    story_bible: dict[str, Any]
    settings: dict[str, Any]
    screenplay: dict[str, Any] | None
    error: str | None
    repair_attempts: int
    raw_invalid_json: str | None


def build_screenplay_graph(text_provider: TextProvider, max_repair_attempts: int = 2):
    def screenplay_node(state: ScreenplayState) -> ScreenplayState:
        try:
            bible = StoryBible.model_validate(state["story_bible"])
            settings = ProductionSettings.model_validate(state["settings"])
            sp = text_provider.generate_screenplay(story_bible=bible, settings=settings)
            return {
                **state,
                "screenplay": sp.model_dump(),
                "error": None,
                "raw_invalid_json": None,
            }
        except ValidationError as val_err:
            return {
                **state,
                "error": str(val_err),
                "raw_invalid_json": str(val_err),
            }
        except Exception as exc:
            return {**state, "error": f"Screenplay generation failed: {exc}"}

    def repair_node(state: ScreenplayState) -> ScreenplayState:
        attempts = state.get("repair_attempts", 0) + 1
        logger.info("LangGraph repair loop: attempt %d for Screenplay", attempts)
        try:
            repaired_sp = text_provider.repair_json(
                invalid_json=state.get("raw_invalid_json") or "",
                target_schema=Screenplay,
                error_context=state.get("error") or "",
            )
            return {
                **state,
                "screenplay": repaired_sp.model_dump(),
                "error": None,
                "repair_attempts": attempts,
            }
        except Exception as exc:
            return {
                **state,
                "error": f"Repair attempt {attempts} failed: {exc}",
                "repair_attempts": attempts,
            }

    def decide_screenplay_next(state: ScreenplayState) -> str:
        if state.get("screenplay") is not None:
            return END
        if state.get("repair_attempts", 0) < max_repair_attempts and state.get("raw_invalid_json"):
            return "repair"
        return END

    workflow = StateGraph(ScreenplayState)
    workflow.add_node("screenplay", screenplay_node)
    workflow.add_node("repair", repair_node)
    workflow.set_entry_point("screenplay")
    workflow.add_conditional_edges("screenplay", decide_screenplay_next, {"repair": "repair", END: END})
    workflow.add_conditional_edges("repair", decide_screenplay_next, {"repair": "repair", END: END})
    return workflow.compile()
