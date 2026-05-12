from __future__ import annotations
import json
from pathlib import Path
from typing import TypedDict, Optional, Annotated
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from loguru import logger

from agents.jd_parser import parse_jd, parse_jd_from_file
from agents.resume_parser import parse_resume
from agents.scoring_agent import score_all_candidates
from models import CandidateProfile, CandidateScore, JobRequirements, ShortlistReport
from utils import config


class PipelineState(TypedDict):
    jd_text: Optional[str]
    jd_file_path: Optional[str]
    resume_paths: list[str]


    job_requirements: Optional[JobRequirements]
    candidate_profiles: list[CandidateProfile]

    candidate_scores: list[CandidateScore]

    report: Optional[ShortlistReport]
    output_paths: dict[str, str]

    errors: list[str]
    warnings: list[str]
    started_at: str
    completed_at: Optional[str]



def validate_inputs(state: PipelineState, config: RunnableConfig = None) -> PipelineState:
    """Validate all inputs before any expensive operations."""
    from utils.security import validate_upload_file

    errors = list(state.get("errors", []))
    warnings = list(state.get("warnings", []))

    has_jd_text = bool(state.get("jd_text", "").strip())
    has_jd_file = bool(state.get("jd_file_path"))
    if not has_jd_text and not has_jd_file:
        errors.append("No job description provided. Provide jd_text or jd_file_path.")

    resume_paths = state.get("resume_paths", [])
    if not resume_paths:
        errors.append("No resume files provided.")
    else:
        valid_paths = []
        for rp in resume_paths:
            ok, err = validate_upload_file(Path(rp))
            if ok:
                valid_paths.append(rp)
            else:
                warnings.append(f"Skipping {rp}: {err}")
        state["resume_paths"] = valid_paths
        if not valid_paths:
            errors.append("No valid resume files after validation.")

    if errors:
        logger.error(f"Input validation failed: {errors}")

    return {**state, "errors": errors, "warnings": warnings}


def parse_jd_node(state: PipelineState, cfg: RunnableConfig = None) -> PipelineState:

    if state.get("errors"):
        return state
    jd_text = state.get("jd_text", "")
    jd_file = state.get("jd_file_path")

    if jd_file and not jd_text:
        requirements = parse_jd_from_file(Path(jd_file))
    else:
        requirements = parse_jd(jd_text)

    if not requirements:
        return {**state, "errors": state["errors"] + ["JD parsing failed."]}

    logger.info(f"JD parsed: '{requirements.title}' | {len(requirements.required_skills)} required skills")
    return {**state, "job_requirements": requirements}


def parse_resumes_node(state: PipelineState, cfg: RunnableConfig = None) -> PipelineState:
    """Parse all resume files into CandidateProfile objects."""
    if state.get("errors"):
        return state

    profiles = []
    warnings = list(state.get("warnings", []))

    for path_str in state["resume_paths"]:
        path = Path(path_str)
        profile = parse_resume(path)
        if profile:
            profiles.append(profile)
        else:
            warnings.append(f"Failed to parse resume: {path.name}")

    if not profiles:
        return {**state, "errors": state["errors"] + ["All resumes failed to parse."],
                "warnings": warnings}

    logger.info(f"Parsed {len(profiles)} candidate profiles.")
    return {**state, "candidate_profiles": profiles, "warnings": warnings}


def score_candidates_node(state: PipelineState, cfg: RunnableConfig = None) -> PipelineState:
    if state.get("errors"):
        return state

    profiles = state.get("candidate_profiles", [])
    jd = state.get("job_requirements")

    if not profiles or not jd:
        return {**state, "errors": state["errors"] + ["Missing profiles or JD for scoring."]}

    scores = score_all_candidates(profiles, jd)

    if not scores:
        return {**state, "errors": state["errors"] + ["Scoring produced no results."]}

    logger.info(f"Scored {len(scores)} candidates.")
    return {**state, "candidate_scores": scores}


def generate_report_node(state: PipelineState, cfg: RunnableConfig = None) -> PipelineState:
    if state.get("errors"):
        return state

    scores = state.get("candidate_scores", [])
    jd = state.get("job_requirements")

    if not scores or not jd:
        return {**state, "errors": state["errors"] + ["No scores to report."]}

    shortlisted = [s for s in scores if s.effective_recommendation() in ("HIRE", "MAYBE")]

    report = ShortlistReport(
        job_title=jd.title,
        company=jd.company,
        total_candidates=len(scores),
        shortlisted_count=len(shortlisted),
        scores=scores,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_used=config.LLM_MODEL,
    )

    output_paths = {}

    from utils.report_generator import generate_json_report, generate_html_report, generate_pdf_report
    json_path = generate_json_report(report)
    output_paths["json"] = str(json_path)

    html_path = generate_html_report(report, jd)
    output_paths["html"] = str(html_path)

    try:
        pdf_path = generate_pdf_report(report, jd)
        output_paths["pdf"] = str(pdf_path)
    except Exception as e:
        logger.warning(f"PDF generation failed (HTML still available): {e}")
        state["warnings"] = state.get("warnings", []) + [f"PDF generation failed: {e}"]

    completed_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"✅ Pipeline complete. Outputs: {output_paths}")

    return {
        **state,
        "report": report,
        "output_paths": output_paths,
        "completed_at": completed_at,
    }



def _should_continue(state: PipelineState) -> str:
    if state.get("errors"):
        return "end_with_error"
    return "continue"


def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("validate_inputs", validate_inputs)
    graph.add_node("parse_jd", parse_jd_node)
    graph.add_node("parse_resumes", parse_resumes_node)
    graph.add_node("score_candidates", score_candidates_node)
    graph.add_node("generate_report", generate_report_node)

    graph.set_entry_point("validate_inputs")

 
    graph.add_edge("validate_inputs", "parse_jd")
    graph.add_edge("parse_jd", "parse_resumes")
    graph.add_edge("parse_resumes", "score_candidates")
    graph.add_edge("score_candidates", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


def run_pipeline(
    resume_paths: list[str | Path],
    jd_text: str = "",
    jd_file_path: str | Path = "",
) -> PipelineState:
    config.validate_config()

    pipeline = build_pipeline()

    initial_state: PipelineState = {
        "jd_text": jd_text,
        "jd_file_path": str(jd_file_path) if jd_file_path else "",
        "resume_paths": [str(p) for p in resume_paths],
        "job_requirements": None,
        "candidate_profiles": [],
        "candidate_scores": [],
        "report": None,
        "output_paths": {},
        "errors": [],
        "warnings": [],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    logger.info(f"Starting pipeline: {len(resume_paths)} resumes")
    final_state = pipeline.invoke(initial_state)

    if final_state["errors"]:
        logger.error(f"Pipeline finished with errors: {final_state['errors']}")
    else:
        logger.info(
            f" Pipeline complete in "
            f"{final_state.get('completed_at', 'N/A')} | "
            f"Outputs: {final_state['output_paths']}"
        )

    return final_state