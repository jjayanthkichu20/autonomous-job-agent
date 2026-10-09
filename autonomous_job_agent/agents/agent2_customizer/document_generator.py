"""Document Generator: Renders ATS-compliant Markdown, Plain-Text, and Typst formatted resumes."""

from pathlib import Path
from typing import Optional
from autonomous_job_agent.core.config import config
from autonomous_job_agent.core.models import (
    ApplicationVariant,
    CandidateMasterProfile,
    JobPosting
)


class DocumentGenerator:
    """Generates clean, single-column, machine-readable ATS document variants."""

    def render_markdown_resume(
        self,
        profile: CandidateMasterProfile,
        variant: ApplicationVariant
    ) -> str:
        lines = []
        # Header
        lines.append(f"# {profile.first_name} {profile.last_name}")
        contact_items = [profile.email, profile.phone, profile.location]
        if profile.linkedin_url:
            contact_items.append(f"[LinkedIn]({profile.linkedin_url})")
        if profile.github_url:
            contact_items.append(f"[GitHub]({profile.github_url})")
        lines.append(" | ".join(contact_items))
        lines.append("")

        # Headline & Summary
        lines.append(f"## {variant.tailored_headline}")
        lines.append(variant.tailored_summary)
        lines.append("")

        # Technical Skills
        lines.append("## Technical Skills")
        lines.append(f"- **Languages & Frameworks:** {', '.join(profile.verified_skills)}")
        lines.append("")

        # Work Experience
        lines.append("## Professional Experience")
        for exp in variant.customized_experiences:
            end_date = exp.get("end_date") or "Present"
            lines.append(f"### {exp['role']} — {exp['company']}")
            lines.append(f"*{exp['start_date']} – {end_date}*")
            lines.append("")
            for bullet in exp.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")

        # Education
        if profile.education:
            lines.append("## Education")
            for edu in profile.education:
                lines.append(f"### {edu.degree} in {edu.field_of_study} — {edu.institution}")
                lines.append(f"*{edu.graduation_year}*")
                lines.append("")

        return "\n".join(lines)

    def render_typst_resume(
        self,
        profile: CandidateMasterProfile,
        variant: ApplicationVariant
    ) -> str:
        """Render Typst markup suitable for compiling directly into ATS-optimized vector PDF."""
        typst = [
            '#set page(paper: "a4", margin: (x: 1.8cm, y: 1.8cm))',
            '#set text(font: "Liberation Sans", size: 10pt)',
            '#set par(justify: false, leading: 0.55em)',
            "",
            f'= {profile.first_name} {profile.last_name}',
            f'#text(size: 8.5pt, fill: rgb("#444444"))[{profile.email} | {profile.phone} | {profile.location}]',
            "",
            f'== {variant.tailored_headline}',
            f'{variant.tailored_summary}',
            "",
            '== Technical Skills',
            f'#text(weight: "bold")[Skills:] {", ".join(profile.verified_skills)}',
            "",
            '== Professional Experience',
        ]

        for exp in variant.customized_experiences:
            end_date = exp.get("end_date") or "Present"
            typst.append(f'=== {exp["role"]} — {exp["company"]}')
            typst.append(f'#text(style: "italic", size: 8.5pt)[{exp["start_date"]} – {end_date}]')
            for bullet in exp.get("bullets", []):
                # Escape typst markup characters
                clean_bullet = bullet.replace("$", "\\$").replace("#", "\\#")
                typst.append(f'- {clean_bullet}')
            typst.append("")

        if profile.education:
            typst.append('== Education')
            for edu in profile.education:
                typst.append(f'=== {edu.degree} in {edu.field_of_study} — {edu.institution} ({edu.graduation_year})')

        return "\n".join(typst)

    def save_artifacts(
        self,
        profile: CandidateMasterProfile,
        job: JobPosting,
        variant: ApplicationVariant
    ) -> dict:
        """Persist generated documents to disk."""
        target_dir = config.artifacts_path / f"job_{job.id[:8]}_{variant.id[:8]}"
        target_dir.mkdir(parents=True, exist_ok=True)

        md_path = target_dir / "resume_tailored.md"
        typst_path = target_dir / "resume_tailored.typ"
        cl_path = target_dir / "cover_letter.txt"

        md_content = self.render_markdown_resume(profile, variant)
        typst_content = self.render_typst_resume(profile, variant)

        md_path.write_text(md_content, encoding="utf-8")
        typst_path.write_text(typst_content, encoding="utf-8")
        cl_path.write_text(variant.cover_letter, encoding="utf-8")

        return {
            "markdown_path": str(md_path),
            "typst_path": str(typst_path),
            "cover_letter_path": str(cl_path)
        }
