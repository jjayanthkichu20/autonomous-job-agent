"""PDF Resume Generator: Compiles CandidateMasterProfile into an ATS-friendly PDF."""

import io
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from autonomous_job_agent.core.models import CandidateMasterProfile


def generate_candidate_pdf(profile: CandidateMasterProfile) -> bytes:
    """Generates an ATS-compliant, professional PDF resume from candidate profile."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CandidateTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        alignment=1 # Center
    )

    contact_style = ParagraphStyle(
        'ContactInfo',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )

    section_header = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1e40af'),
        spaceBefore=8,
        spaceAfter=4
    )

    role_style = ParagraphStyle(
        'RoleTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1e293b')
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
        leftIndent=12
    )

    story = []

    # 1. Header (Name & Contact)
    first_name = profile.first_name or "Candidate"
    last_name = profile.last_name or ""
    email = profile.email or ""
    phone = profile.phone or ""
    loc = profile.location or ""
    linkedin = profile.linkedin_url or ""

    story.append(Paragraph(f"{first_name} {last_name}", title_style))
    contact_line = f"{email} | {phone} | {loc}"
    if linkedin:
        contact_line += f" | {linkedin}"
    story.append(Paragraph(contact_line, contact_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=8))

    # 2. Target Roles & Specialization
    if profile.target_roles:
        story.append(Paragraph("TARGET ROLES & SPECIALIZATION", section_header))
        roles_text = " • ".join(profile.target_roles[:5])
        story.append(Paragraph(roles_text, body_style))
        story.append(Spacer(1, 4))

    # 3. Verified Core Skills
    if profile.verified_skills:
        story.append(Paragraph("CORE COMPETENCIES & TECHNICAL SKILLS", section_header))
        skills_text = ", ".join(profile.verified_skills)
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 4))

    # 4. Work Experience
    if profile.experiences:
        story.append(Paragraph("PROFESSIONAL EXPERIENCE", section_header))
        for exp in profile.experiences:
            dates = f"{exp.start_date} – {exp.end_date or 'Present'}"
            exp_header = f"<b>{exp.role}</b> | {exp.company} <i>({exp.location or ''})</i>"
            story.append(Paragraph(f"{exp_header} <font color='#64748b' size='8'>[{dates}]</font>", role_style))
            story.append(Spacer(1, 2))
            
            for ach in exp.achievements:
                bullet = f"• <b>{ach.metric}:</b> {ach.action}."
                story.append(Paragraph(bullet, bullet_style))
                story.append(Spacer(1, 2))
            story.append(Spacer(1, 4))

    # 5. Education
    if profile.education:
        story.append(Paragraph("EDUCATION & QUALIFICATIONS", section_header))
        for edu in profile.education:
            edu_text = f"<b>{edu.degree} in {edu.field_of_study}</b> — {edu.institution} ({edu.graduation_year})"
            story.append(Paragraph(edu_text, body_style))
            story.append(Spacer(1, 2))

    doc.build(story)
    return buffer.getvalue()
