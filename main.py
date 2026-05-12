import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from loguru import logger

from agents.pipeline import run_pipeline
from agents.humaninloop import apply_hr_override, get_override_log
from models import CandidateScore

console = Console()


def display_results(state: dict) -> None:
    if state.get("errors"):
        console.print(f"\n[red]❌ Pipeline failed:[/red]")
        for err in state["errors"]:
            console.print(f"  • {err}", style="red")
        return

    report = state.get("report")
    if not report:
        console.print("[yellow]No report generated.[/yellow]")
        return

    # Header
    console.print(Panel(
        f"[bold white]{report.job_title}[/bold white]\n"
        f"[dim]{report.company or 'Company'} | Generated: {report.generated_at[:10]} | "
        f"Model: {report.model_used}[/dim]",
        title="[bold blue]HR SHORTLIST REPORT[/bold blue]",
        border_style="blue"
    ))

    console.print(f"\n📊 [bold]Total candidates:[/bold] {report.total_candidates}  |  "
                  f"[green]Shortlisted:[/green] {report.shortlisted_count}  |  "
                  f"[red]Not shortlisted:[/red] {report.total_candidates - report.shortlisted_count}")

    table = Table(show_header=True, header_style="bold magenta", border_style="dim")
    table.add_column("#", width=3, justify="center")
    table.add_column("Candidate", width=22)
    table.add_column("Skills\n(30%)", justify="center", width=9)
    table.add_column("Exp\n(25%)", justify="center", width=8)
    table.add_column("Edu\n(15%)", justify="center", width=8)
    table.add_column("Projects\n(20%)", justify="center", width=10)
    table.add_column("Comm\n(10%)", justify="center", width=8)
    table.add_column("Total", justify="center", width=7)
    table.add_column("Decision", justify="center", width=12)

    for rank, s in enumerate(report.scores, 1):
        eff_total = s.effective_total()
        eff_rec = s.effective_recommendation()
        rec_style = "bold green" if eff_rec == "HIRE" else "bold yellow" if eff_rec == "MAYBE" else "bold red"
        override_marker = " ⚙" if s.hr_override else ""

        table.add_row(
            str(rank),
            s.full_name + override_marker,
            f"{s.skills_match.score:.1f}",
            f"{s.experience_relevance.score:.1f}",
            f"{s.education_certs.score:.1f}",
            f"{s.project_portfolio.score:.1f}",
            f"{s.communication_quality.score:.1f}",
            f"[bold]{eff_total:.2f}[/bold]",
            f"[{rec_style}]{eff_rec}[/{rec_style}]",
        )

    console.print(table)

    # Top 3 detailed summaries
    console.print("\n[bold]Top Candidates — Quick Summary:[/bold]")
    for rank, s in enumerate(report.scores[:3], 1):
        eff_rec = s.effective_recommendation()
        color = "green" if eff_rec == "HIRE" else "yellow"
        console.print(
            f"  [bold]{rank}.[/bold] [bold {color}]{s.full_name}[/bold {color}] "
            f"({s.effective_total():.2f}/10)"
        )
        if s.summary_justification:
            console.print(f"     {s.summary_justification}", style="dim")
        if s.skill_gaps:
            console.print(f"     ❌ Gaps: {', '.join(s.skill_gaps[:5])}", style="red dim")

    # Output files
    if state.get("output_paths"):
        console.print("\n[bold green]📁 Output Files:[/bold green]")
        for fmt, path in state["output_paths"].items():
            console.print(f"  • {fmt.upper()}: {path}")

    # Warnings
    if state.get("warnings"):
        console.print("\n[yellow]⚠️  Warnings:[/yellow]")
        for w in state["warnings"]:
            console.print(f"  • {w}", style="yellow dim")


def main():
    parser = argparse.ArgumentParser(
        description="HR Resume & LinkedIn Shortlisting Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # JD input
    jd_group = parser.add_mutually_exclusive_group()
    jd_group.add_argument("--jd", type=Path, help="Path to JD file (PDF or TXT)")
    jd_group.add_argument("--jd-text", type=str, help="JD as inline text string")

    # Resume input
    parser.add_argument("--resumes", nargs="+", type=Path,
                        help="Resume files (PDF/DOCX) or a directory of resumes")

    # HR Override
    parser.add_argument("--override", nargs=4, metavar=("CANDIDATE_ID", "NEW_SCORE", "NEW_REC", "REASON"),
                        help="Override a score: --override candidate_id 7.5 HIRE 'Strong leadership'")
    parser.add_argument("--hr-user", type=str, default="hr_manager",
                        help="HR user ID for overrides (default: hr_manager)")

    # Options
    parser.add_argument("--show-overrides", action="store_true", help="Show HR override audit log")
    parser.add_argument("--generate-samples", action="store_true",
                        help="Generate 5 sample resumes for testing")

    args = parser.parse_args()

    # Generate sample data
    if args.generate_samples:
        console.print("[bold]Generating sample resumes...[/bold]")
        import subprocess
        subprocess.run([sys.executable, "data/generate_sample_resumes.py"], check=True)
        return

    # Show override log
    if args.show_overrides:
        log = get_override_log()
        if not log:
            console.print("No HR overrides recorded yet.")
        else:
            t = Table(title="HR Override Audit Log")
            t.add_column("Timestamp"); t.add_column("Candidate"); t.add_column("By")
            t.add_column("Old"); t.add_column("New"); t.add_column("Rec"); t.add_column("Reason")
            for entry in log:
                t.add_row(
                    entry["timestamp"][:16], entry["candidate_id"], entry["overridden_by"],
                    str(entry["original_total"]), str(entry["overridden_total"]),
                    entry["overridden_recommendation"], entry["reason"][:40]
                )
            console.print(t)
        return

    # Validate inputs
    if not args.jd and not args.jd_text:
        parser.error("Provide --jd <file> or --jd-text '<text>'")
    if not args.resumes:
        parser.error("Provide --resumes <files or directory>")

    # Resolve resume paths
    resume_paths = []
    for p in args.resumes:
        if p.is_dir():
            resume_paths.extend(list(p.glob("*.pdf")) + list(p.glob("*.docx")))
        elif p.is_file():
            resume_paths.append(p)
        else:
            console.print(f"[yellow]Warning: {p} not found, skipping.[/yellow]")

    if not resume_paths:
        console.print("[red]No resume files found.[/red]")
        sys.exit(1)

    console.print(f"\n[bold blue]🚀 Starting HR Agent[/bold blue]")
    console.print(f"  JD: {args.jd or 'inline text'}")
    console.print(f"  Resumes: {len(resume_paths)} files")
    console.print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run pipeline
    state = run_pipeline(
        resume_paths=resume_paths,
        jd_text=args.jd_text or "",
        jd_file_path=args.jd or "",
    )

    # Apply HR override if requested
    if args.override and state.get("candidate_scores"):
        candidate_id, new_score, new_rec, reason = args.override
        target = next((s for s in state["candidate_scores"] if s.candidate_id == candidate_id), None)
        if target:
            apply_hr_override(
                score=target,
                hr_user=args.hr_user,
                new_total=float(new_score),
                new_recommendation=new_rec,
                reason=reason,
            )
            console.print(f"[green]✅ Override applied to {candidate_id}[/green]")
        else:
            console.print(f"[yellow]⚠️ Candidate '{candidate_id}' not found in results.[/yellow]")

    display_results(state)


if __name__ == "__main__":
    main()