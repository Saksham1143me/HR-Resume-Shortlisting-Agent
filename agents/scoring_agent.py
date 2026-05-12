import json
import re

from typing import Optional

from langchain_google_genai import (
    ChatGoogleGenerativeAI
)

from langchain_core.messages import (
    SystemMessage,
    HumanMessage
)

from loguru import logger

from models import (
    CandidateProfile,
    JobRequirements,
    CandidateScore,
    DimensionScore
)

from utils import config


SCORING_SYSTEM_PROMPT = """
You are a highly experienced,
objective HR evaluator.

Score a candidate against a job
description using the provided rubric.

=================================================
SCORING SCALE
=================================================

0  = Completely unrelated
3  = Weak / partial
5  = Meets minimum expectations
7  = Strong fit
10 = Exceptional fit

=================================================
DIMENSIONS
=================================================

1. skills_match (30%)
2. experience_relevance (25%)
3. education_certs (15%)
4. project_portfolio (20%)
5. communication_quality (10%)

=================================================
STRICT RULES
=================================================

1. Be evidence-based.
2. Use only information present in candidate profile.
3. Do not reward irrelevant skills.
4. Communication quality is based on resume clarity.
5. Output ONLY valid JSON.
6. No markdown.
7. No explanations outside JSON.

=================================================
JSON OUTPUT FORMAT
=================================================

{
  "skills_match": {
    "score": 0,
    "justification": "",
    "evidence": []
  },

  "experience_relevance": {
    "score": 0,
    "justification": "",
    "evidence": []
  },

  "education_certs": {
    "score": 0,
    "justification": "",
    "evidence": []
  },

  "project_portfolio": {
    "score": 0,
    "justification": "",
    "evidence": []
  },

  "communication_quality": {
    "score": 0,
    "justification": "",
    "evidence": []
  },

  "summary_justification": "",

  "skill_gaps": [],

  "skill_matches": []
}

=================================================
BIAS MITIGATION
=================================================

Ignore:
- candidate name
- age
- gender
- ethnicity
- graduation year

Focus ONLY on skills, experience,
projects, education, and evidence.
"""

def extract_json(
    text: str
) -> str:

    match = re.search(

        r'\{.*\}',

        text,

        re.DOTALL
    )

    if match:

        return match.group(0)

    return "{}"


def get_llm():

    return ChatGoogleGenerativeAI(

        model=config.LLM_MODEL,

        temperature=0.0,

        max_tokens=2048,

        timeout=config.LLM_TIMEOUT,

        max_retries=config.LLM_MAX_RETRIES,

        google_api_key=config.GOOGLE_API_KEY,
    )



def _build_scoring_prompt(
    candidate: CandidateProfile,
    jd: JobRequirements
) -> str:

    candidate_summary = f"""
CANDIDATE PROFILE

Name: REDACTED

Skills:
{', '.join(candidate.skills) if candidate.skills else 'None'}

Experience:
{candidate.total_years_experience or 0} years

Work History:
{chr(10).join(
    f"- {w.role or 'Unknown'} at {w.company or 'Unknown'} "
    f"({w.duration_years or '?'} years) | "
    f"Domain: {w.domain or 'Unknown'} | "
    f"Highlights: {'; '.join(w.highlights[:2]) if w.highlights else 'None'}"

    for w in (candidate.work_history or [])[:5]
) or 'None'}

Education:
{chr(10).join(
    f"- {e.degree or ''} in {e.field or ''} "
    f"from {e.institution or ''}"

    for e in (candidate.education or [])[:3]
) or 'None'}

Certifications:
{', '.join(candidate.certifications) if candidate.certifications else 'None'}

Projects:
{chr(10).join(
    f"- {p}"

    for p in (candidate.projects or [])[:5]
) or 'None'}

Resume Writing Notes:
{candidate.writing_quality_notes or 'None'}
"""

    jd_summary = f"""
JOB DESCRIPTION

Title:
{jd.title}

Domain:
{jd.domain}

Seniority:
{jd.seniority_level}

Required Skills:
{', '.join(jd.required_skills)}

Preferred Skills:
{', '.join(jd.preferred_skills)}

Minimum Experience:
{jd.min_years_experience or 'Not specified'}

Required Education:
{jd.required_education or 'Not specified'}

Preferred Certifications:
{', '.join(jd.preferred_certifications)}

Responsibilities:
{'; '.join(jd.key_responsibilities[:5])}

Ideal Candidate Summary:
{jd.summary}
"""

    return f"""
{jd_summary}

{candidate_summary}

Evaluate the candidate objectively
against the job description.
"""

def score_candidate(
    candidate: CandidateProfile,
    jd: JobRequirements,
) -> Optional[CandidateScore]:

    logger.info(
        f"Scoring candidate: "
        f"{candidate.candidate_id}"
    )

    try:

        llm = get_llm()

        user_prompt = _build_scoring_prompt(
            candidate,
            jd
        )

        messages = [

            SystemMessage(
                content=SCORING_SYSTEM_PROMPT
            ),

            HumanMessage(
                content=user_prompt
            )
        ]


        response = llm.invoke(
            messages
        )

        raw_response = response.content

        print("\nRAW SCORING RESPONSE")
        print(raw_response)

        cleaned = raw_response.replace(
            "```json",
            ""
        )

        cleaned = cleaned.replace(
            "```",
            ""
        )

        cleaned = extract_json(
            cleaned
        )


        raw = json.loads(
            cleaned
        )


        score = CandidateScore(

            candidate_id=candidate.candidate_id,

            full_name=candidate.full_name,

            skills_match=DimensionScore(
                **raw["skills_match"]
            ),

            experience_relevance=DimensionScore(
                **raw["experience_relevance"]
            ),

            education_certs=DimensionScore(
                **raw["education_certs"]
            ),

            project_portfolio=DimensionScore(
                **raw["project_portfolio"]
            ),

            communication_quality=DimensionScore(
                **raw["communication_quality"]
            ),

            summary_justification=raw.get(
                "summary_justification",
                ""
            ),

            skill_gaps=raw.get(
                "skill_gaps",
                []
            ),

            skill_matches=raw.get(
                "skill_matches",
                []
            ),
        )

        logger.info(

            f"Scored "
            f"{candidate.candidate_id} | "

            f"Total: {score.weighted_total}/10 | "

            f"{score.recommendation}"
        )

        return score

    except KeyError as e:

        logger.error(
            f"Missing score field "
            f"for {candidate.candidate_id}: {e}"
        )

        return None

    except json.JSONDecodeError as e:

        logger.error(
            f"JSON parsing failed "
            f"for {candidate.candidate_id}: {e}"
        )

        return None

    except Exception as e:

        logger.error(
            f"Scoring failed for "
            f"{candidate.candidate_id}: {e}"
        )

        return None



def score_all_candidates(
    candidates: list[CandidateProfile],
    jd: JobRequirements,
) -> list[CandidateScore]:

    if not candidates:

        logger.warning(
            "No candidates to score."
        )

        return []

    if len(candidates) > config.MAX_RESUMES_PER_RUN:

        logger.warning(

            f"Capping resumes at "
            f"{config.MAX_RESUMES_PER_RUN}"
        )

        candidates = candidates[
            :config.MAX_RESUMES_PER_RUN
        ]

    scores = []

    for i, candidate in enumerate(
        candidates,
        1
    ):

        logger.info(
            f"Scoring {i}/"
            f"{len(candidates)}"
        )

        score = score_candidate(
            candidate,
            jd
        )

        if score:

            scores.append(score)


    scores.sort(

        key=lambda s: s.effective_total(),

        reverse=True
    )

    logger.info(

        f"Scoring completed | "

        f"{len(scores)} candidates scored."
    )

    return scores