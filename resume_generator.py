"""
data/generate_sample_resumes.py — Generate 5 sample PDF resumes for testing.

The 5 profiles represent:
  1. Strong match  — Hits nearly all requirements (expected HIRE)
  2. Good match    — Hits most requirements, missing a few (expected HIRE/MAYBE)
  3. Partial match — Some skills match, different domain (expected MAYBE)
  4. Weak match    — Frontend dev applying for backend role (expected NO_HIRE)
  5. No match      — Completely unrelated field (expected NO_HIRE)

Run: python data/generate_sample_resumes.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "sample_resumes"
OUTPUT_DIR.mkdir(exist_ok=True)

styles = getSampleStyleSheet()
name_style = ParagraphStyle("Name", fontName="Helvetica-Bold", fontSize=18, spaceAfter=2)
contact_style = ParagraphStyle("Contact", fontName="Helvetica", fontSize=9,
                                textColor=colors.HexColor("#6b7280"), spaceAfter=12)
section_style = ParagraphStyle("Section", fontName="Helvetica-Bold", fontSize=11,
                                textColor=colors.HexColor("#1e1b4b"), spaceAfter=4,
                                spaceBefore=10)
body_style = ParagraphStyle("Body", fontName="Helvetica", fontSize=9, leading=14, spaceAfter=4)
bullet_style = ParagraphStyle("Bullet", fontName="Helvetica", fontSize=9, leading=13,
                               leftIndent=12, spaceAfter=2)


def build_resume(filename: str, content: list) -> None:
    path = OUTPUT_DIR / filename
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    doc.build(content)
    print(f"✅ Generated: {path}")


def hr(elements):
    elements.append(HRFlowable(width="100%", thickness=0.5,
                                color=colors.HexColor("#e5e7eb"), spaceAfter=4))


# ─── Resume 1: Arjun Sharma — STRONG MATCH ────────────────────────────────────
def resume_arjun():
    e = []
    e.append(Paragraph("Arjun Sharma", name_style))
    e.append(Paragraph("arjun.sharma@email.com  |  +91 98765 43210  |  Bangalore, IN  |  github.com/arjunsharma", contact_style))
    hr(e)

    e.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    e.append(Paragraph(
        "Senior Backend Engineer with 6 years building high-throughput financial systems. "
        "Led the architecture of a payments microservices platform processing ₹500Cr+/day. "
        "Deep expertise in Python, PostgreSQL, Redis, and AWS. Strong advocate for "
        "clean architecture, observability, and test-driven development.", body_style))

    e.append(Paragraph("SKILLS", section_style))
    e.append(Paragraph(
        "<b>Languages:</b> Python (6yr), Go (2yr), SQL<br/>"
        "<b>Frameworks:</b> FastAPI, Django REST Framework, Celery<br/>"
        "<b>Databases:</b> PostgreSQL (query optimisation, partitioning), Redis, MongoDB<br/>"
        "<b>Cloud:</b> AWS (EC2, RDS, SQS, Lambda, CloudWatch), Docker, Kubernetes (EKS)<br/>"
        "<b>Messaging:</b> Apache Kafka, RabbitMQ<br/>"
        "<b>Observability:</b> Prometheus, Grafana, ELK Stack<br/>"
        "<b>Tools:</b> Git, GitHub Actions, Jenkins, Terraform, gRPC", body_style))

    e.append(Paragraph("EXPERIENCE", section_style))
    e.append(Paragraph("<b>Senior Backend Engineer</b> — RazorPay (Payments Team)  |  Jan 2021 – Present  (3.5 yr)", body_style))
    for bullet in [
        "Architected a microservices-based payment processing system handling 15M+ transactions/day with 99.99% uptime",
        "Reduced PostgreSQL query latency by 68% through indexing strategy and connection pooling (PgBouncer)",
        "Built Kafka-based event streaming pipeline for real-time reconciliation across 20+ banking partners",
        "Implemented PCI-DSS compliant encryption layer and rate limiting for all payment APIs",
        "Mentored 4 junior engineers; established backend coding standards and PR review culture",
        "Achieved 94% unit test coverage across core payment modules",
    ]:
        e.append(Paragraph(f"• {bullet}", bullet_style))

    e.append(Spacer(1, 6))
    e.append(Paragraph("<b>Backend Engineer</b> — Juspay Technologies  |  Jul 2018 – Dec 2020  (2.5 yr)", body_style))
    for bullet in [
        "Developed REST APIs for payment gateway integrations using Python/Django, serving 5M+ users",
        "Designed Redis caching layer reducing API response times by 40%",
        "Containerised 12 microservices using Docker; deployed on AWS ECS",
    ]:
        e.append(Paragraph(f"• {bullet}", bullet_style))

    e.append(Paragraph("EDUCATION", section_style))
    e.append(Paragraph("B.Tech in Computer Science  |  IIT Bombay  |  2018  |  CGPA: 8.7/10", body_style))

    e.append(Paragraph("CERTIFICATIONS", section_style))
    e.append(Paragraph("AWS Certified Solutions Architect – Associate (2022)<br/>AWS Certified Developer – Associate (2021)", body_style))

    e.append(Paragraph("PROJECTS", section_style))
    e.append(Paragraph(
        "<b>PayFast Gateway (Open Source):</b> Built a pluggable Python payment gateway library "
        "supporting 8 Indian payment methods; 1.2k GitHub stars.<br/>"
        "<b>PG Replication Monitor:</b> Prometheus exporter for PostgreSQL replication lag monitoring, "
        "used in production at 3 companies.", body_style))

    build_resume("01_arjun_sharma_strong_match.pdf", e)


# ─── Resume 2: Priya Mehta — GOOD MATCH ──────────────────────────────────────
def resume_priya():
    e = []
    e.append(Paragraph("Priya Mehta", name_style))
    e.append(Paragraph("priya.mehta@gmail.com  |  +91 87654 32109  |  Mumbai, IN", contact_style))
    hr(e)

    e.append(Paragraph("SUMMARY", section_style))
    e.append(Paragraph(
        "Backend Engineer with 5 years of experience in Python microservices and cloud infrastructure. "
        "Proficient in building REST APIs and working with AWS. Looking to transition from e-commerce "
        "to FinTech. Strong fundamentals in distributed systems and database design.", body_style))

    e.append(Paragraph("TECHNICAL SKILLS", section_style))
    e.append(Paragraph(
        "Python, FastAPI, PostgreSQL, MySQL, Redis, Docker, Kubernetes, AWS (EC2, S3, SQS, RDS), "
        "Git, GitHub Actions, Celery, REST APIs", body_style))

    e.append(Paragraph("EXPERIENCE", section_style))
    e.append(Paragraph("<b>Backend Engineer II</b> — Flipkart  |  Jun 2019 – Present  (5 yr)", body_style))
    for b in [
        "Built order management microservices in Python/FastAPI handling 2M+ daily orders",
        "Optimised PostgreSQL queries and indexes, reducing p99 latency by 35%",
        "Designed Redis caching for product catalogue (12M SKUs), improving read throughput 5x",
        "Deployed containerised services on Kubernetes; managed CI/CD with GitHub Actions",
        "Wrote unit and integration tests; maintained 88% code coverage",
    ]:
        e.append(Paragraph(f"• {b}", bullet_style))

    e.append(Paragraph("EDUCATION", section_style))
    e.append(Paragraph("B.E. in Information Technology  |  BITS Pilani  |  2019", body_style))

    e.append(Paragraph("CERTIFICATIONS", section_style))
    e.append(Paragraph("AWS Certified Developer – Associate (2023)", body_style))

    e.append(Paragraph("PROJECTS", section_style))
    e.append(Paragraph(
        "<b>Inventory Sync Service:</b> Async inventory reconciliation service using Celery + Redis.<br/>"
        "<b>API Rate Limiter Library:</b> Pluggable rate limiting middleware for FastAPI.", body_style))

    build_resume("02_priya_mehta_good_match.pdf", e)


# ─── Resume 3: Rahul Verma — PARTIAL MATCH ───────────────────────────────────
def resume_rahul():
    e = []
    e.append(Paragraph("Rahul Verma", name_style))
    e.append(Paragraph("rahul.verma@outlook.com  |  +91 76543 21098  |  Hyderabad, IN", contact_style))
    hr(e)

    e.append(Paragraph("ABOUT ME", section_style))
    e.append(Paragraph(
        "Full-stack developer with 4 years experience. Comfortable with both Python and JavaScript. "
        "Have worked on web applications and some data pipelines. Eager to learn new technologies.", body_style))

    e.append(Paragraph("SKILLS", section_style))
    e.append(Paragraph(
        "Python, Django, Flask, JavaScript, React, Node.js, MySQL, SQLite, "
        "Git, Docker (basic), Linux, REST APIs, HTML, CSS", body_style))

    e.append(Paragraph("WORK HISTORY", section_style))
    e.append(Paragraph("<b>Full Stack Developer</b> — Infosys  |  2020 – Present  (4 yr)", body_style))
    for b in [
        "Developed web applications for insurance domain clients using Django and React",
        "Created REST APIs consumed by mobile applications",
        "Worked with MySQL databases, wrote stored procedures",
        "Deployed applications on AWS EC2 (basic configuration)",
    ]:
        e.append(Paragraph(f"• {b}", bullet_style))

    e.append(Paragraph("EDUCATION", section_style))
    e.append(Paragraph("B.Tech in Computer Science  |  VIT University  |  2020", body_style))

    e.append(Paragraph("PROJECTS", section_style))
    e.append(Paragraph(
        "<b>Insurance Claims Portal:</b> Full-stack claims management system in Django+React.<br/>"
        "<b>Employee Leave Tracker:</b> Simple HR leave tracking web app.", body_style))

    build_resume("03_rahul_verma_partial_match.pdf", e)


# ─── Resume 4: Sneha Kapoor — WEAK MATCH (Frontend) ──────────────────────────
def resume_sneha():
    e = []
    e.append(Paragraph("Sneha Kapoor", name_style))
    e.append(Paragraph("sneha.kapoor@email.com  |  +91 65432 10987  |  Pune, IN", contact_style))
    hr(e)

    e.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
    e.append(Paragraph(
        "Creative Frontend Engineer with 5 years building beautiful, responsive web applications. "
        "Expert in React ecosystem and modern CSS. Have some exposure to Node.js backend. "
        "Passionate about user experience and design systems.", body_style))

    e.append(Paragraph("TECHNICAL SKILLS", section_style))
    e.append(Paragraph(
        "JavaScript (ES6+), TypeScript, React, Redux, Next.js, HTML5, CSS3, Tailwind CSS, "
        "Storybook, Jest, Cypress, Node.js (basic), MongoDB (basic), Git, Figma", body_style))

    e.append(Paragraph("EXPERIENCE", section_style))
    e.append(Paragraph("<b>Senior Frontend Engineer</b> — Swiggy  |  2019 – Present  (5 yr)", body_style))
    for b in [
        "Led the redesign of Swiggy's restaurant partner portal used by 200k+ restaurants",
        "Built a component design system in React + Storybook, reducing UI dev time by 40%",
        "Implemented micro-frontend architecture splitting monolith into 6 independent apps",
        "Collaborated with backend engineers to design REST API contracts",
        "Mentored 3 junior frontend developers",
    ]:
        e.append(Paragraph(f"• {b}", bullet_style))

    e.append(Paragraph("EDUCATION", section_style))
    e.append(Paragraph("B.Sc. in Computer Science  |  Pune University  |  2019", body_style))

    e.append(Paragraph("PROJECTS", section_style))
    e.append(Paragraph(
        "<b>React Component Library (GitHub, 800+ stars):</b> Open-source accessible component library.<br/>"
        "<b>Portfolio Site Builder:</b> SaaS tool for creating portfolio websites, used by 5k+ users.", body_style))

    build_resume("04_sneha_kapoor_weak_match.pdf", e)


# ─── Resume 5: Mohan Das — NO MATCH (Marketing) ──────────────────────────────
def resume_mohan():
    e = []
    e.append(Paragraph("Mohan Das", name_style))
    e.append(Paragraph("mohan.das@gmail.com  |  +91 54321 09876  |  Chennai, IN", contact_style))
    hr(e)

    e.append(Paragraph("PROFESSIONAL PROFILE", section_style))
    e.append(Paragraph(
        "Results-driven Digital Marketing Manager with 7 years of experience in SEO, SEM, "
        "and social media marketing. Proven track record of growing organic traffic by 300%+ "
        "and managing ₹2Cr+ annual advertising budgets.", body_style))

    e.append(Paragraph("SKILLS", section_style))
    e.append(Paragraph(
        "Google Ads, Facebook Ads, SEO, SEM, Google Analytics, Content Strategy, "
        "Email Marketing, HubSpot, Salesforce, Excel, PowerPoint, Canva", body_style))

    e.append(Paragraph("EXPERIENCE", section_style))
    e.append(Paragraph("<b>Digital Marketing Manager</b> — MakeMyTrip  |  2017 – Present  (7 yr)", body_style))
    for b in [
        "Managed ₹2Cr+ annual Google and Meta advertising budget across 12 campaigns",
        "Grew organic search traffic by 320% through content strategy and technical SEO",
        "Led a team of 5 marketing specialists and 3 content writers",
        "Implemented marketing automation workflows using HubSpot",
        "Collaborated with the product team to optimise conversion funnels",
    ]:
        e.append(Paragraph(f"• {b}", bullet_style))

    e.append(Paragraph("EDUCATION", section_style))
    e.append(Paragraph("MBA in Marketing  |  XLRI Jamshedpur  |  2017", body_style))
    e.append(Paragraph("B.Com  |  Madras University  |  2015", body_style))

    e.append(Paragraph("CERTIFICATIONS", section_style))
    e.append(Paragraph("Google Ads Certified (2023)  |  HubSpot Marketing Certified  |  Meta Blueprint", body_style))

    build_resume("05_mohan_das_no_match.pdf", e)


if __name__ == "__main__":
    print("Generating 5 sample resumes...")
    resume_arjun()
    resume_priya()
    resume_rahul()
    resume_sneha()
    resume_mohan()
    print(f"\nAll resumes saved to: {OUTPUT_DIR}")