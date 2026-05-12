"""
utils/report_generator.py — Generate shortlist reports in JSON, HTML, and PDF.

Three output formats:
  1. JSON  — Machine-readable, complete data dump
  2. HTML  — Human-readable, styled, printable
  3. PDF   — Professional report via ReportLab

All formats include:
  - Ranked candidate table with scores and recommendations
  - Per-candidate dimension breakdown with justifications
  - HR override annotations (if any)
  - Pipeline metadata (model used, date, version)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from models import ShortlistReport, CandidateScore, JobRequirements
from utils import config



def generate_json_report(report: ShortlistReport) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_slug = report.job_title.lower().replace(" ", "_")[:30]
    path = config.OUTPUTS_DIR / f"shortlist_{job_slug}_{timestamp}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, default=str)

    logger.info(f"JSON report: {path}")
    return path



def _recommendation_badge(rec: str) -> str:
    colors = {"HIRE": "#10b981", "MAYBE": "#f59e0b", "NO_HIRE": "#ef4444"}
    color = colors.get(rec, "#6b7280")
    return f'<span style="background:{color};color:white;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700">{rec}</span>'


def _score_bar(score: float, weight_pct: str) -> str:
    pct = score * 10
    color = "#10b981" if score >= 7 else "#f59e0b" if score >= 5 else "#ef4444"
    return f"""
    <div style="display:flex;align-items:center;gap:8px">
        <div style="width:120px;background:#e5e7eb;border-radius:4px;height:8px">
            <div style="width:{pct}%;background:{color};border-radius:4px;height:8px"></div>
        </div>
        <span style="font-weight:600;color:{color}">{score:.1f}/10</span>
        <span style="color:#9ca3af;font-size:11px">({weight_pct})</span>
    </div>"""


def generate_html_report(report: ShortlistReport, jd: Optional[JobRequirements] = None) -> Path:
    """Generate a styled HTML shortlist report."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_slug = report.job_title.lower().replace(" ", "_")[:30]
    path = config.OUTPUTS_DIR / f"shortlist_{job_slug}_{timestamp}.html"

    weights = config.RUBRIC_WEIGHTS

    # Build candidate rows for summary table
    summary_rows = ""
    for rank, s in enumerate(report.scores, 1):
        eff_total = s.effective_total()
        eff_rec = s.effective_recommendation()
        override_note = " ⚙️" if s.hr_override else ""
        summary_rows += f"""
        <tr>
            <td style="font-weight:700;color:#6b7280">{rank}</td>
            <td style="font-weight:600">{s.full_name}{override_note}</td>
            <td>{s.skills_match.score:.1f}</td>
            <td>{s.experience_relevance.score:.1f}</td>
            <td>{s.education_certs.score:.1f}</td>
            <td>{s.project_portfolio.score:.1f}</td>
            <td>{s.communication_quality.score:.1f}</td>
            <td style="font-weight:700;font-size:16px">{eff_total:.2f}</td>
            <td>{_recommendation_badge(eff_rec)}</td>
        </tr>"""

    # Build detailed candidate sections
    detail_sections = ""
    for rank, s in enumerate(report.scores, 1):
        eff_total = s.effective_total()
        eff_rec = s.effective_recommendation()
        gap_pills = "".join(
            f'<span style="background:#fee2e2;color:#b91c1c;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px">{g}</span>'
            for g in (s.skill_gaps or [])[:8]
        ) or "<em style='color:#9ca3af'>None identified</em>"
        match_pills = "".join(
            f'<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:12px;font-size:12px;margin:2px">{m}</span>'
            for m in (s.skill_matches or [])[:10]
        ) or "<em style='color:#9ca3af'>None identified</em>"

        override_section = ""
        if s.hr_override:
            override_section = f"""
            <div style="background:#fef3c7;border-left:4px solid #f59e0b;padding:12px;margin-top:12px;border-radius:4px">
                <strong>⚙️ HR Override</strong> by {s.hr_override.overridden_by}<br>
                Score changed: {s.hr_override.original_total} → {s.hr_override.overridden_total} |
                Reason: {s.hr_override.reason}<br>
                <small style="color:#9ca3af">{s.hr_override.timestamp}</small>
            </div>"""

        dims = [
            ("Skills Match", s.skills_match, f"{int(weights['skills_match']*100)}%"),
            ("Experience Relevance", s.experience_relevance, f"{int(weights['experience_relevance']*100)}%"),
            ("Education & Certs", s.education_certs, f"{int(weights['education_certs']*100)}%"),
            ("Project/Portfolio", s.project_portfolio, f"{int(weights['project_portfolio']*100)}%"),
            ("Communication Quality", s.communication_quality, f"{int(weights['communication_quality']*100)}%"),
        ]

        dim_rows = ""
        for dim_name, dim_score, weight in dims:
            evidence_list = "".join(f"<li>{e}</li>" for e in (dim_score.evidence or [])[:3])
            dim_rows += f"""
            <tr style="border-bottom:1px solid #f3f4f6">
                <td style="padding:10px;font-weight:600;white-space:nowrap">{dim_name}</td>
                <td style="padding:10px">{_score_bar(dim_score.score, weight)}</td>
                <td style="padding:10px;color:#374151">{dim_score.justification}</td>
                <td style="padding:10px">
                    <ul style="margin:0;padding-left:16px;font-size:12px;color:#6b7280">{evidence_list}</ul>
                </td>
            </tr>"""

        detail_sections += f"""
        <div style="background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.08);padding:24px;margin-bottom:24px">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:16px">
                <div>
                    <span style="background:#e0e7ff;color:#3730a3;border-radius:50%;padding:4px 12px;font-size:13px;font-weight:700">#{rank}</span>
                    <span style="font-size:20px;font-weight:700;margin-left:12px">{s.full_name}</span>
                </div>
                <div style="text-align:right">
                    {_recommendation_badge(eff_rec)}
                    <div style="font-size:28px;font-weight:800;margin-top:4px">{eff_total:.2f}<span style="font-size:14px;color:#9ca3af">/10</span></div>
                </div>
            </div>
            <p style="color:#6b7280;margin-bottom:16px">{s.summary_justification}</p>
            <table style="width:100%;border-collapse:collapse">
                <thead>
                    <tr style="background:#f9fafb">
                        <th style="padding:10px;text-align:left;font-size:12px;color:#6b7280">Dimension</th>
                        <th style="padding:10px;text-align:left;font-size:12px;color:#6b7280">Score</th>
                        <th style="padding:10px;text-align:left;font-size:12px;color:#6b7280">Justification</th>
                        <th style="padding:10px;text-align:left;font-size:12px;color:#6b7280">Evidence</th>
                    </tr>
                </thead>
                <tbody>{dim_rows}</tbody>
            </table>
            <div style="margin-top:16px">
                <strong style="font-size:13px">✅ Skill Matches:</strong> {match_pills}
            </div>
            <div style="margin-top:8px">
                <strong style="font-size:13px">❌ Skill Gaps:</strong> {gap_pills}
            </div>
            {override_section}
        </div>"""

    jd_skills = ", ".join(jd.required_skills[:15]) if jd else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HR Shortlist Report — {report.job_title}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'DM Sans', sans-serif; background: #f3f4f6; color: #111827; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 16px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ padding: 12px 10px; text-align: left; }}
  thead tr {{ background: #1e1b4b; color: white; }}
  tbody tr:nth-child(even) {{ background: #f9fafb; }}
  tbody tr:hover {{ background: #eff6ff; }}
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e1b4b,#312e81);color:white;border-radius:16px;padding:32px;margin-bottom:32px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div>
        <p style="opacity:.7;font-size:13px;margin-bottom:4px">SHORTLIST REPORT</p>
        <h1 style="font-size:28px;font-weight:800">{report.job_title}</h1>
        {f'<p style="opacity:.8;margin-top:4px">{report.company}</p>' if report.company else ''}
      </div>
      <div style="text-align:right">
        <p style="opacity:.7;font-size:12px">Generated</p>
        <p style="font-weight:600">{report.generated_at[:10]}</p>
        <p style="opacity:.7;font-size:11px;margin-top:4px">Model: {report.model_used}</p>
      </div>
    </div>
    <div style="display:flex;gap:24px;margin-top:24px">
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:12px 20px;text-align:center">
        <p style="font-size:28px;font-weight:800">{report.total_candidates}</p>
        <p style="opacity:.8;font-size:12px">Total Candidates</p>
      </div>
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:12px 20px;text-align:center">
        <p style="font-size:28px;font-weight:800">{report.shortlisted_count}</p>
        <p style="opacity:.8;font-size:12px">Shortlisted</p>
      </div>
      <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:12px 20px;text-align:center">
        <p style="font-size:28px;font-weight:800">{report.total_candidates - report.shortlisted_count}</p>
        <p style="opacity:.8;font-size:12px">Not Shortlisted</p>
      </div>
    </div>
  </div>

  <!-- JD Summary -->
  {f'''<div style="background:white;border-radius:12px;padding:20px;margin-bottom:24px;box-shadow:0 1px 4px rgba(0,0,0,.06)">
    <h2 style="font-size:16px;font-weight:700;margin-bottom:8px">📋 Job Requirements Summary</h2>
    <p><strong>Domain:</strong> {jd.domain} | <strong>Seniority:</strong> {jd.seniority_level}</p>
    <p style="margin-top:6px"><strong>Required Skills:</strong> {jd_skills}</p>
  </div>''' if jd else ''}

  <!-- Summary Table -->
  <div style="background:white;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:32px">
    <div style="padding:20px 24px;border-bottom:1px solid #e5e7eb">
      <h2 style="font-size:18px;font-weight:700">📊 Ranking Summary</h2>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th>#</th><th>Candidate</th>
            <th>Skills (30%)</th><th>Exp (25%)</th>
            <th>Edu (15%)</th><th>Projects (20%)</th>
            <th>Comm (10%)</th><th>Total</th><th>Recommendation</th>
          </tr>
        </thead>
        <tbody>{summary_rows}</tbody>
      </table>
    </div>
  </div>

  <!-- Detailed Sections -->
  <h2 style="font-size:20px;font-weight:700;margin-bottom:16px">📝 Detailed Candidate Reports</h2>
  {detail_sections}

  <!-- Footer -->
  <div style="text-align:center;color:#9ca3af;font-size:12px;margin-top:32px">
    Generated by HR Resume Shortlisting Agent v{report.pipeline_version} |
    Model: {report.model_used} | {report.generated_at}
    <br>⚠️ This report is an AI-assisted shortlisting tool. Final hiring decisions must involve human review.
  </div>
</div>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")
    logger.info(f"HTML report: {path}")
    return path


def generate_pdf_report(report: ShortlistReport, jd: Optional[JobRequirements] = None) -> Path:
    """
    Generate a professional PDF shortlist report using ReportLab.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_slug = report.job_title.lower().replace(" ", "_")[:30]
    path = config.OUTPUTS_DIR / f"shortlist_{job_slug}_{timestamp}.pdf"

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    elements = []

    # Color palette
    NAVY    = colors.HexColor("#1e1b4b")
    INDIGO  = colors.HexColor("#4f46e5")
    GREEN   = colors.HexColor("#10b981")
    AMBER   = colors.HexColor("#f59e0b")
    RED     = colors.HexColor("#ef4444")
    GRAY    = colors.HexColor("#6b7280")
    LIGHT   = colors.HexColor("#f3f4f6")

    # Styles
    title_style = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=20,
                                  textColor=colors.white, alignment=TA_LEFT)
    h2_style    = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=13,
                                  textColor=NAVY, spaceAfter=6)
    body_style  = ParagraphStyle("Body", fontName="Helvetica", fontSize=9,
                                  textColor=colors.HexColor("#374151"), leading=14)
    small_style = ParagraphStyle("Small", fontName="Helvetica", fontSize=8,
                                  textColor=GRAY)
    dim_style   = ParagraphStyle("Dim", fontName="Helvetica", fontSize=8,
                                  textColor=colors.HexColor("#374151"), leading=12)

    # ── Cover Section ──────────────────────────────────────────────────────────
    cover_data = [[
        Paragraph(f"<font color='white'><b>HR SHORTLIST REPORT</b></font><br/>"
                  f"<font color='white' size='16'>{report.job_title}</font><br/>"
                  f"<font color='#a5b4fc' size='9'>"
                  f"{'  |  ' + report.company if report.company else ''}"
                  f"  Generated: {report.generated_at[:10]}</font>", title_style),
        Paragraph(
            f"<font color='white'><b>{report.total_candidates}</b></font><br/>"
            f"<font color='#a5b4fc' size='8'>Candidates</font><br/><br/>"
            f"<font color='white'><b>{report.shortlisted_count}</b></font><br/>"
            f"<font color='#a5b4fc' size='8'>Shortlisted</font>",
            ParagraphStyle("CoverRight", fontName="Helvetica-Bold", fontSize=20,
                           textColor=colors.white, alignment=TA_RIGHT)
        )
    ]]
    cover_table = Table(cover_data, colWidths=["75%", "25%"])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ROWPADDING", (0, 0), (-1, -1), 16),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(cover_table)
    elements.append(Spacer(1, 20))

    # ── Summary Table ─────────────────────────────────────────────────────────
    elements.append(Paragraph("Ranking Summary", h2_style))
    header = ["#", "Candidate", "Skills\n(30%)", "Exp\n(25%)", "Edu\n(15%)",
              "Projects\n(20%)", "Comm\n(10%)", "Total", "Decision"]

    table_data = [header]
    for rank, s in enumerate(report.scores, 1):
        eff_total = s.effective_total()
        eff_rec = s.effective_recommendation()
        rec_color = GREEN if eff_rec == "HIRE" else AMBER if eff_rec == "MAYBE" else RED
        table_data.append([
            str(rank),
            Paragraph(s.full_name + (" ⚙" if s.hr_override else ""), dim_style),
            f"{s.skills_match.score:.1f}",
            f"{s.experience_relevance.score:.1f}",
            f"{s.education_certs.score:.1f}",
            f"{s.project_portfolio.score:.1f}",
            f"{s.communication_quality.score:.1f}",
            Paragraph(f"<b>{eff_total:.2f}</b>", dim_style),
            Paragraph(f"<font color='white'><b>{eff_rec}</b></font>",
                      ParagraphStyle("Rec", fontName="Helvetica-Bold", fontSize=8,
                                     textColor=colors.white, alignment=TA_CENTER)),
        ])

    summary_table = Table(table_data, repeatRows=1,
                          colWidths=[0.5*cm, 4*cm, 1.5*cm, 1.5*cm,
                                      1.5*cm, 1.8*cm, 1.5*cm, 1.5*cm, 2.2*cm])

    # Dynamic row colours for recommendation
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ]
    for i, s in enumerate(report.scores, 1):
        eff_rec = s.effective_recommendation()
        bg = colors.HexColor("#d1fae5") if eff_rec == "HIRE" else \
             colors.HexColor("#fef3c7") if eff_rec == "MAYBE" else \
             colors.HexColor("#fee2e2")
        ts.append(("BACKGROUND", (8, i), (8, i), GREEN if eff_rec == "HIRE" else AMBER if eff_rec == "MAYBE" else RED))

    summary_table.setStyle(TableStyle(ts))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))

    # ── Detailed Candidate Reports ────────────────────────────────────────────
    elements.append(PageBreak())
    elements.append(Paragraph("Detailed Candidate Reports", h2_style))
    elements.append(Spacer(1, 10))

    dim_labels = [
        ("Skills Match",          "skills_match",          "30%"),
        ("Experience Relevance",  "experience_relevance",  "25%"),
        ("Education & Certs",     "education_certs",       "15%"),
        ("Project / Portfolio",   "project_portfolio",     "20%"),
        ("Communication Quality", "communication_quality", "10%"),
    ]

    for rank, s in enumerate(report.scores, 1):
        eff_total = s.effective_total()
        eff_rec = s.effective_recommendation()
        rec_color = GREEN if eff_rec == "HIRE" else AMBER if eff_rec == "MAYBE" else RED

        # Candidate header
        cand_header_data = [[
            Paragraph(f"<b>#{rank}  {s.full_name}</b>", h2_style),
            Paragraph(
                f"<font color='white'> {eff_rec} </font><br/>"
                f"<b><font size='18'>{eff_total:.2f}</font></b>/10",
                ParagraphStyle("CandRight", fontName="Helvetica-Bold", fontSize=8,
                               textColor=rec_color, alignment=TA_RIGHT)
            )
        ]]
        cand_header = Table(cand_header_data, colWidths=["75%", "25%"])
        cand_header.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
            ("ROWPADDING", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (1, 0), (1, 0), rec_color),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(cand_header)

        # Summary justification
        if s.summary_justification:
            elements.append(Paragraph(s.summary_justification, body_style))
        elements.append(Spacer(1, 8))

        # Dimension table
        dim_header = ["Dimension (Weight)", "Score", "Justification", "Evidence"]
        dim_data = [dim_header]
        for label, attr, weight in dim_labels:
            dim_score = getattr(s, attr)
            evidence_text = "; ".join(dim_score.evidence[:2]) if dim_score.evidence else "—"
            score_color = GREEN if dim_score.score >= 7 else AMBER if dim_score.score >= 5 else RED
            dim_data.append([
                Paragraph(f"{label}<br/><font color='gray' size='7'>{weight}</font>", dim_style),
                Paragraph(f"<font color='white'><b> {dim_score.score:.1f} </b></font>", dim_style),
                Paragraph(dim_score.justification or "—", dim_style),
                Paragraph(evidence_text, small_style),
            ])

        dim_table = Table(dim_data, repeatRows=1,
                          colWidths=[4*cm, 1.5*cm, 6*cm, 5*cm])
        dim_ts = [
            ("BACKGROUND", (0, 0), (-1, 0), INDIGO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i, (_, attr, _) in enumerate(dim_labels, 1):
            dim_score = getattr(s, attr)
            bg = GREEN if dim_score.score >= 7 else AMBER if dim_score.score >= 5 else RED
            dim_ts.append(("BACKGROUND", (1, i), (1, i), bg))
            dim_ts.append(("TEXTCOLOR", (1, i), (1, i), colors.white))

        dim_table.setStyle(TableStyle(dim_ts))
        elements.append(dim_table)

        # Skill gaps / matches
        if s.skill_gaps or s.skill_matches:
            gap_text = ", ".join(s.skill_gaps[:8]) or "None"
            match_text = ", ".join(s.skill_matches[:10]) or "None"
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<b>✅ Matches:</b> {match_text}", small_style))
            elements.append(Paragraph(f"<b>❌ Gaps:</b> <font color='red'>{gap_text}</font>", small_style))

        # HR Override
        if s.hr_override:
            override_data = [[Paragraph(
                f"<b>⚙️ HR Override</b> by {s.hr_override.overridden_by} on {s.hr_override.timestamp[:10]}<br/>"
                f"Score changed: {s.hr_override.original_total} → {s.hr_override.overridden_total}<br/>"
                f"Reason: {s.hr_override.reason}",
                ParagraphStyle("Override", fontName="Helvetica", fontSize=8,
                               textColor=colors.HexColor("#92400e"))
            )]]
            override_table = Table(override_data)
            override_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
                ("ROWPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 1, AMBER),
            ]))
            elements.append(Spacer(1, 6))
            elements.append(override_table)

        elements.append(Spacer(1, 16))
        elements.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#e5e7eb")))
        elements.append(Spacer(1, 12))

    # Footer disclaimer
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Generated by HR Resume Shortlisting Agent v{report.pipeline_version} | "
        f"Model: {report.model_used} | {report.generated_at[:10]}<br/>"
        "⚠️ This is an AI-assisted tool. Final hiring decisions require human review and judgment.",
        small_style
    ))

    doc.build(elements)
    logger.info(f"PDF report: {path}")
    return path