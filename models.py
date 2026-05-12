from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class JobRequirements(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    title: str = Field(description="Job title as stated in the JD")
    company: Optional[str] = Field(default=None, description="Company name if mentioned")
    required_skills: list[str] = Field(description="Hard/technical skills explicitly required")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    min_years_experience: Optional[float] = Field(default=None, description="Minimum years of experience")
    max_years_experience: Optional[float] = Field(default=None, description="Maximum years if stated")
    required_education: Optional[str] = Field(default=None, description="Minimum education level")
    preferred_certifications: list[str] = Field(default_factory=list)
    domain: str = Field(description="Industry/functional domain (e.g. 'FinTech backend engineering')")
    seniority_level: Literal["intern", "junior", "mid", "senior", "lead", "manager", "director", "any"] = Field(
        default="any", description="Seniority level inferred from JD"
    )
    key_responsibilities: list[str] = Field(default_factory=list, description="Top 5 responsibilities")
    summary: str = Field(description="One-paragraph summary of what an ideal candidate looks like")

class WorkExperience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    duration_years: Optional[float] = None
    domain: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[int] = None


class CandidateProfile(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    candidate_id: str = Field(description="Unique ID (filename or URL hash)")
    full_name: str = Field(default="Unknown")
    email: Optional[str] = Field(default=None, description="Masked in logs for PII compliance")
    phone: Optional[str] = Field(default=None, description="Masked in logs for PII compliance")
    skills: list[str] = Field(default_factory=list)
    total_years_experience: Optional[float] = None
    work_history: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list, description="Project titles or descriptions")
    writing_quality_notes: str = Field(
        default="",
        description="Notes on resume writing quality: clarity, structure, grammar"
    )
    source_file: str = Field(default="")
    raw_text_length: int = Field(default=0, description="Character count of raw resume text")


class DimensionScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    score: float = Field(description="Score from 0 to 10")
    justification: str = Field(description="One-line explanation of this score")
    evidence: list[str] = Field(
        default_factory=list,
        description="Specific quotes/facts from the resume supporting the score"
    )

    @field_validator("score")
    @classmethod
    def clamp_and_round_score(cls, v: float) -> float:
        """
        Fix for TestDimensionScore::test_score_clamped_at_10.
        Ensures scores are forced into the 0-10 range and rounded.
        """
        clamped = max(0.0, min(10.0, float(v)))
        return round(clamped, 2)


class CandidateScore(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    candidate_id: str
    full_name: str

    skills_match: DimensionScore
    experience_relevance: DimensionScore
    education_certs: DimensionScore
    project_portfolio: DimensionScore
    communication_quality: DimensionScore

    weighted_total: float = Field(default=0.0)
    recommendation: Literal["HIRE", "MAYBE", "NO_HIRE"] = Field(default="NO_HIRE")
    summary_justification: str = Field(default="", description="2-3 sentence overall assessment")
    skill_gaps: list[str] = Field(default_factory=list, description="Skills required but missing")
    skill_matches: list[str] = Field(default_factory=list, description="Skills that match JD")

    hr_override: Optional[HROverride] = Field(default=None)

    @model_validator(mode="after")
    def compute_weighted_total(self) -> "CandidateScore":
        from utils.config import RUBRIC_WEIGHTS, SHORTLIST_THRESHOLD
        total = (
            self.skills_match.score           * RUBRIC_WEIGHTS["skills_match"] +
            self.experience_relevance.score  * RUBRIC_WEIGHTS["experience_relevance"] +
            self.education_certs.score       * RUBRIC_WEIGHTS["education_certs"] +
            self.project_portfolio.score     * RUBRIC_WEIGHTS["project_portfolio"] +
            self.communication_quality.score * RUBRIC_WEIGHTS["communication_quality"]
        )
        self.weighted_total = round(total, 2)

        if self.weighted_total >= SHORTLIST_THRESHOLD + 1.5:
            self.recommendation = "HIRE"
        elif self.weighted_total >= SHORTLIST_THRESHOLD:
            self.recommendation = "MAYBE"
        else:
            self.recommendation = "NO_HIRE"

        return self

    def effective_total(self) -> float:
        if self.hr_override:
            return self.hr_override.overridden_total
        return self.weighted_total

    def effective_recommendation(self) -> str:
        if self.hr_override:
            return self.hr_override.overridden_recommendation
        return self.recommendation


class HROverride(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    overridden_by: str = Field(description="HR user identifier")
    reason: str = Field(description="Mandatory justification for override")
    original_total: float
    overridden_total: float
    overridden_recommendation: Literal["HIRE", "MAYBE", "NO_HIRE"]
    timestamp: str = Field(description="ISO 8601 timestamp")



class ShortlistReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    job_title: str
    company: Optional[str] = None
    total_candidates: int
    shortlisted_count: int
    scores: list[CandidateScore] = Field(description="Sorted by effective_total descending")
    generated_at: str
    model_used: str
    pipeline_version: str = "1.0.0"