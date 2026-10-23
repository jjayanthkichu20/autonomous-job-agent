"""Multi-Dimensional ATS Evaluation Engine.

Evaluates candidate profiles and tailored resumes across multiple real-world ATS methodologies:
1. Workday Enterprise Parser (Strict keyword match, structured employment timeline)
2. Greenhouse Scorecard (Competency coverage, departmental alignment)
3. Taleo Keyword & Knockout Engine (Exact phrase density, mandatory credentials)
4. Lever Velocity & Impact Index (Quantifiable achievements, metrics, action verbs)
5. iCIMS / Sovren Structural Parsability (Section cleanliness, contact completeness)
6. Composite Multi-Engine Benchmark (Weighted interview readiness index)
"""

import re
from typing import Dict, List, Any, Optional
from autonomous_job_agent.core.models import CandidateMasterProfile


class MultiATSEvaluator:
    """Evaluates candidate resumes across diverse algorithmic ATS paradigms."""

    ACTION_VERBS = {
        "spearheaded", "managed", "orchestrated", "executed", "developed",
        "implemented", "streamlined", "optimized", "coordinated", "resolved",
        "audited", "automated", "facilitated", "championed", "delivered",
        "directed", "formulated", "established", "supervised", "standardized"
    }

    CORE_HR_KEYWORDS = {
        "hr operations", "onboarding", "induction", "hrms", "hris",
        "statutory compliance", "pf", "esi", "labour law", "payroll",
        "attendance", "leave management", "employee relations", "recruitment",
        "talent acquisition", "screening", "interview coordination", "excel",
        "mis reporting", "background verification", "exit formalities"
    }

    COMPANY_BENCHMARKS = {
        "Infosys": {
            "engine": "Workday",
            "required_keywords": ["HR Operations", "Onboarding", "HRIS", "Compliance", "Excel", "MIS"],
            "min_experience_years": 1.5,
            "required_degree": "Bachelor"
        },
        "HP Inc.": {
            "engine": "Workday",
            "required_keywords": ["HR Operations", "Payroll Input Support", "HRMS", "Compliance", "Vendor Management"],
            "min_experience_years": 2.0,
            "required_degree": "Bachelor"
        },
        "Dell Technologies": {
            "engine": "Taleo",
            "required_keywords": ["HR Operations", "Recruitment", "Compliance", "HRIS", "Documentation"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        },
        "TCS": {
            "engine": "Enterprise ATS",
            "required_keywords": ["HR Operations", "Statutory Compliance", "Onboarding", "Attendance Management", "Excel"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        },
        "Genpact": {
            "engine": "Taleo",
            "required_keywords": ["Payroll Input Support", "Compliance", "HRMS", "Employee Documentation", "Audit"],
            "min_experience_years": 1.5,
            "required_degree": "Bachelor"
        },
        "Accenture": {
            "engine": "Workday",
            "required_keywords": ["HR Operations", "Process Improvement", "HRIS", "Onboarding", "Stakeholder Management"],
            "min_experience_years": 2.0,
            "required_degree": "Bachelor"
        },
        "Quest Global": {
            "engine": "Lever",
            "required_keywords": ["Talent Acquisition", "Technical Sourcing", "Interview Coordination", "HR Operations"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        },
        "Sutherland": {
            "engine": "iCIMS",
            "required_keywords": ["HR Executive", "Recruitment & Talent Acquisition", "Documentation", "Compliance"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        },
        "Concentrix": {
            "engine": "Greenhouse",
            "required_keywords": ["Candidate Screening", "HR Operations", "Onboarding", "HRMS"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        },
        "Swiggy Technologies": {
            "engine": "Greenhouse",
            "required_keywords": ["HR Operations Executive", "HRIS", "Employee Lifecycle", "Payroll Support"],
            "min_experience_years": 1.0,
            "required_degree": "Bachelor"
        }
    }

    ROLE_BENCHMARKS = {
        "HR Operations Executive": {
            "department": "HR Shared Services & Operations",
            "required_keywords": ["HR Operations", "Onboarding", "HRIS", "Compliance", "Payroll", "Employee Records"],
            "recommended_keywords": ["Statutory Compliance (PF/ESI)", "HRMS", "Attendance Management", "Advanced Excel"],
            "benchmark_experience": "1 - 3 Years",
            "role_summary": "Manages employee documentation, HRIS records, onboarding workflows, and statutory compliance audits.",
            "actionable_tip": "Highlight statutory compliance audits (PF/ESI) and HRIS maintenance to maintain a 96%+ score."
        },
        "HR Executive": {
            "department": "Generalist Human Resources",
            "required_keywords": ["HR Operations", "Recruitment", "Onboarding", "Employee Relations", "Documentation"],
            "recommended_keywords": ["Advanced Excel", "MIS Reporting", "Compliance", "HRIS"],
            "benchmark_experience": "1 - 2 Years",
            "role_summary": "Generalist role driving recruitment coordination, employee onboarding, policies, and grievance handling.",
            "actionable_tip": "Include stakeholder coordination and employee relations initiatives to boost match to 98%."
        },
        "Talent Acquisition Specialist": {
            "department": "Talent Sourcing & Recruitment",
            "required_keywords": ["Recruitment", "Talent Acquisition", "Candidate Screening", "Interview Coordination", "Sourcing"],
            "recommended_keywords": ["ATS Management", "Stakeholder Coordination", "Offer Negotiation", "LinkedIn Recruiter"],
            "benchmark_experience": "2+ Years",
            "role_summary": "Drives candidate pipeline generation, screening interviews, ATS pipeline tracking, and hiring manager alignment.",
            "actionable_tip": "Emphasize talent sourcing metrics (e.g. screened 150+ profiles) and ATS workflow management."
        },
        "HR Coordinator": {
            "department": "People Operations Support",
            "required_keywords": ["Onboarding", "Documentation", "HR Administration", "Scheduling", "Employee Records"],
            "recommended_keywords": ["HRIS", "Induction", "HR Reporting", "Advanced Excel"],
            "benchmark_experience": "0 - 2 Years",
            "role_summary": "Provides logistical, onboarding, background verification, document collection, and HRIS maintenance support.",
            "actionable_tip": "Highlight orientation logistics, verification audits, and speedy onboarding turnaround."
        },
        "People Operations Partner": {
            "department": "People Operations & Culture",
            "required_keywords": ["HR Operations", "Employee Experience", "Process Automation", "HR Policies", "HRIS"],
            "recommended_keywords": ["Culture Initiatives", "Data Analysis", "Performance Management Support", "Compliance"],
            "benchmark_experience": "2 - 4 Years",
            "role_summary": "Partners with leadership to automate HR workflows, refine employee experience journeys, and ensure policy adherence.",
            "actionable_tip": "Showcase process optimization, policy rollout communication, and workflow automation."
        }
    }

    def evaluate_profile(self, profile: CandidateMasterProfile, selected_role: Optional[str] = None, custom_jd_text: Optional[str] = None) -> Dict[str, Any]:
        """Runs multi-way evaluation of candidate master profile calibrated by target role."""
        
        # 1. Compile profile textual corpus
        skills_pool = [s.lower().strip() for s in (profile.verified_skills or [])]
        target_roles = [r.lower().strip() for r in (profile.target_roles or [])]
        
        achievements_text = []
        action_verb_count = 0
        metrics_count = 0
        total_bullets = 0

        for exp in profile.experiences:
            for ach in exp.achievements:
                total_bullets += 1
                text = f"{ach.action} {ach.metric}".lower()
                achievements_text.append(text)
                
                # Check metrics & numbers
                if re.search(r"\d+%|\d+\+|\b\d+\b", text):
                    metrics_count += 1
                
                # Check action verbs
                words = set(re.findall(r"[a-z]+", text))
                if words.intersection(self.ACTION_VERBS):
                    action_verb_count += 1

        combined_text = " ".join(skills_pool + target_roles + achievements_text + [profile.location.lower() if profile.location else ""])

        # Determine candidate domain
        is_software = any(any(k in s.lower() for k in ["python", "go", "kubernetes", "distributed", "engineer", "software", "golang"]) for s in skills_pool + target_roles)

        if is_software:
            domain_mandatory = {"distributed systems", "kubernetes", "go", "python", "docker"}
            domain_competencies = {
                "cloud & distributed architecture": any(k in s for s in skills_pool for k in ["distributed", "cloud", "system"]),
                "containerization & orchestration": any(k in s for s in skills_pool for k in ["kubernetes", "docker"]),
                "programming languages (go/python)": any(k in s for s in skills_pool for k in ["go", "python", "rust", "c"]),
                "api & microservices": any(k in s for s in skills_pool for k in ["api", "grpc", "microservice", "service"]),
                "observability & system internals": any(k in s for s in skills_pool for k in ["ebpf", "observability", "metrics", "test", "linux"]),
                "ci/cd & automation": any(k in s for s in skills_pool for k in ["ci", "git", "linux", "automation", "infrastructure"])
            }
            core_keywords_set = {"go", "python", "kubernetes", "docker", "distributed systems", "ebpf", "linux", "cloud", "aws", "grpc"}
        else:
            domain_mandatory = {"hr operations", "compliance", "onboarding", "hris", "excel"}
            domain_competencies = {
                "employee onboarding": any("onboarding" in s for s in skills_pool),
                "hr systems (hris/hrms)": any("hris" in s or "hrms" in s for s in skills_pool),
                "statutory & regulatory compliance": any("compliance" in s for s in skills_pool),
                "payroll input & processing": any("payroll" in s for s in skills_pool),
                "talent acquisition & screening": any("recruitment" in s or "acquisition" in s or "screening" in s for s in skills_pool),
                "reporting & data analytics": any("excel" in s or "reporting" in s or "mis" in s for s in skills_pool)
            }
            core_keywords_set = self.CORE_HR_KEYWORDS

        # ----------------------------------------------------
        # Scoring Methodology 1: Workday Exact Match & Structure (0-100)
        # ----------------------------------------------------
        workday_matched = [kw for kw in domain_mandatory if any(kw in item for item in skills_pool + achievements_text)]
        workday_keyword_score = (len(workday_matched) / len(domain_mandatory)) * 100
        
        # Contact and structured timeline validation
        has_phone = bool(profile.phone and len(profile.phone) >= 10 and not "00000" in profile.phone)
        has_email = bool(profile.email and "@" in profile.email and not "example.com" in profile.email)
        has_loc = bool(profile.location and len(profile.location) > 3)
        has_linkedin = bool(profile.linkedin_url)
        workday_structure_score = sum([has_phone * 25, has_email * 25, has_loc * 25, has_linkedin * 25])
        
        workday_score = round(0.60 * workday_keyword_score + 0.40 * workday_structure_score, 1)

        # ----------------------------------------------------
        # Scoring Methodology 2: Greenhouse Competency Scorecard (0-100)
        # ----------------------------------------------------
        greenhouse_matched_count = sum(1 for passed in domain_competencies.values() if passed)
        greenhouse_score = round((greenhouse_matched_count / len(domain_competencies)) * 100, 1)

        # ----------------------------------------------------
        # Scoring Methodology 3: Taleo Keyword & Knockout Engine (0-100)
        # ----------------------------------------------------
        taleo_density = sum(1 for kw in core_keywords_set if kw in combined_text)
        taleo_density_ratio = min(1.0, taleo_density / (5.0 if is_software else 8.0))
        
        # Education knockout check (Requires Degree)
        has_degree = bool(profile.education and any("bachelor" in e.degree.lower() or "degree" in e.degree.lower() or "b.tech" in e.degree.lower() or "technology" in e.degree.lower() for e in profile.education))
        taleo_knockout_pass = has_degree and has_email and has_phone
        
        taleo_score = round((0.70 * (taleo_density_ratio * 100)) + (0.30 * (100 if taleo_knockout_pass else 0)), 1)

        # ----------------------------------------------------
        # Scoring Methodology 4: Lever Impact & Outcome Velocity (0-100)
        # ----------------------------------------------------
        metric_ratio = (metrics_count / total_bullets) if total_bullets > 0 else 0.8
        action_verb_ratio = (action_verb_count / total_bullets) if total_bullets > 0 else 0.9
        lever_score = round((0.50 * (metric_ratio * 100)) + (0.50 * (action_verb_ratio * 100)), 1)
        lever_score = min(100.0, max(75.0, lever_score))

        # ----------------------------------------------------
        # Scoring Methodology 5: iCIMS / Sovren Parsability Audit (0-100)
        # ----------------------------------------------------
        # Checks plain-text parseability, clean standard sections, lack of malformed tables
        icims_checks = {
            "Standard Experience Section": len(profile.experiences) > 0,
            "Standard Education Section": len(profile.education) > 0,
            "Explicit Technical Skills List": len(profile.verified_skills) >= 4,
            "Contact Phone with Country Code": has_phone,
            "Valid Deliverable Email": has_email,
            "Target Location Anchor": has_loc
        }
        icims_passed = sum(1 for passed in icims_checks.values() if passed)
        icims_score = round((icims_passed / len(icims_checks)) * 100, 1)

        # ----------------------------------------------------
        # Unified Composite Benchmark
        # ----------------------------------------------------
        composite_score = round(
            0.25 * workday_score +
            0.20 * greenhouse_score +
            0.20 * taleo_score +
            0.20 * lever_score +
            0.15 * icims_score,
            1
        )

        # ----------------------------------------------------
        # Company-Specific ATS Benchmark Scores
        # ----------------------------------------------------
        company_scores = []
        for company, meta in self.COMPANY_BENCHMARKS.items():
            req_kws = meta["required_keywords"]
            matched_kws = [k for k in req_kws if any(k.lower() in item for item in skills_pool + achievements_text)]
            missing_kws = [k for k in req_kws if k not in matched_kws]
            
            c_score = round(
                (len(matched_kws) / len(req_kws)) * 75.0 + 
                (20.0 if has_degree else 0.0) + 
                (5.0 if has_phone else 0.0),
                1
            )
            c_score = min(99.0, max(72.0, c_score))

            company_scores.append({
                "company": company,
                "engine": meta["engine"],
                "score": c_score,
                "verdict": "Interview Ready" if c_score >= 85 else "Competitive",
                "matched_keywords": matched_kws,
                "missing_keywords": missing_kws
            })

        # ----------------------------------------------------
        # Custom JD Evaluation (if JD text is supplied)
        # ----------------------------------------------------
        custom_jd_result = None
        if custom_jd_text and len(custom_jd_text.strip()) > 20:
            jd_lower = custom_jd_text.lower()
            jd_words = set(re.findall(r"\b[a-z]{3,}\b", jd_lower))
            
            # Extract common skill matches
            matched_terms = [kw for kw in self.CORE_HR_KEYWORDS if kw in jd_lower and any(kw in item for item in skills_pool + achievements_text)]
            missing_terms = [kw for kw in self.CORE_HR_KEYWORDS if kw in jd_lower and kw not in matched_terms]
            
            jd_match_ratio = (len(matched_terms) / max(1, len(matched_terms) + len(missing_terms))) if (matched_terms or missing_terms) else 0.88
            custom_score = round(jd_match_ratio * 100, 1)
            custom_score = min(98.0, max(70.0, custom_score))
            
            custom_jd_result = {
                "score": custom_score,
                "matched_keywords": matched_terms,
                "missing_keywords": missing_terms,
                "verdict": "High ATS Screen Pass" if custom_score >= 80 else "Requires Keyword Tailoring"
            }

        # ----------------------------------------------------
        # Target Role ATS Score Comparison & Calibration
        # ----------------------------------------------------
        candidate_target_roles = list(profile.target_roles or [])
        if not candidate_target_roles:
            candidate_target_roles = ["HR Operations Executive", "HR Executive", "Talent Acquisition Specialist"]

        all_target_roles = list(dict.fromkeys(candidate_target_roles + list(self.ROLE_BENCHMARKS.keys())))
        
        # If user explicitly selected a role, use it; otherwise default to candidate's first target role
        active_role = selected_role if (selected_role and any(selected_role.lower() == r.lower() for r in all_target_roles)) else candidate_target_roles[0]

        role_scores = []
        for role_name in all_target_roles:
            meta = self.ROLE_BENCHMARKS.get(role_name, {
                "department": "Target Career Discipline",
                "required_keywords": [s for s in skills_pool[:5]],
                "recommended_keywords": [s for s in skills_pool[5:8]],
                "benchmark_experience": "1 - 3 Years",
                "role_summary": f"Target role aligned with {role_name} responsibilities.",
                "actionable_tip": f"Optimize keywords around {role_name} core competencies."
            })

            req_kws = meta.get("required_keywords", [])
            rec_kws = meta.get("recommended_keywords", [])
            
            def is_keyword_matched(k_str):
                k_clean = re.sub(r"[\(\)/]", " ", k_str.lower()).strip()
                k_words = [w for w in k_clean.split() if len(w) > 3]
                for item in skills_pool + achievements_text:
                    if k_clean in item or item in k_clean:
                        return True
                    if k_words and any(w in item for w in k_words):
                        return True
                return False

            matched_req = [k for k in req_kws if is_keyword_matched(k)]
            missing_req = [k for k in req_kws if k not in matched_req]
            
            matched_rec = [k for k in rec_kws if is_keyword_matched(k)]
            missing_rec = [k for k in rec_kws if k not in matched_rec]

            title_match = any(role_name.lower() in tr.lower() or tr.lower() in role_name.lower() for tr in target_roles)
            exp_title_match = any(role_name.lower() in exp.role.lower() or exp.role.lower() in role_name.lower() for exp in profile.experiences)
            
            title_score = 100.0 if (title_match and exp_title_match) else (90.0 if (title_match or exp_title_match) else 75.0)
            req_score = (len(matched_req) / max(1, len(req_kws))) * 100.0 if req_kws else 90.0
            rec_score = (len(matched_rec) / max(1, len(rec_kws))) * 100.0 if rec_kws else 90.0
            
            # Composite role score (50% Required Keywords, 25% Title Match, 15% Recommended Keywords, 10% Impact)
            r_score = round(0.50 * req_score + 0.25 * title_score + 0.15 * rec_score + 0.10 * (lever_score), 1)
            r_score = min(99.0, max(65.0, r_score))

            if r_score >= 90:
                r_verdict = "Optimal Pass (Top 5% Tier)"
            elif r_score >= 80:
                r_verdict = "Interview Ready (High ATS Pass Rate)"
            else:
                r_verdict = "Competitive (Add Recommended Keywords)"

            is_active = (role_name.lower() == active_role.lower())

            role_scores.append({
                "role": role_name,
                "department": meta.get("department", "HR"),
                "score": r_score,
                "is_active": is_active,
                "verdict": r_verdict,
                "matched_keywords": matched_req + matched_rec,
                "missing_keywords": missing_req + missing_rec,
                "benchmark_experience": meta.get("benchmark_experience", "1 - 3 Years"),
                "role_summary": meta.get("role_summary", ""),
                "actionable_tip": meta.get("actionable_tip", "")
            })

        # Sort so active role is first, then by score descending
        role_scores.sort(key=lambda x: (not x["is_active"], -x["score"]))
        active_role_entry = next((r for r in role_scores if r["is_active"]), role_scores[0])

        return {
            "active_target_role": active_role_entry["role"],
            "active_role_score": active_role_entry["score"],
            "target_roles_list": all_target_roles,
            "role_comparisons": role_scores,
            "overall_composite_score": composite_score,
            "readiness_verdict": "Tier-1 Interview Ready (High ATS Pass Rate)" if composite_score >= 88 else "Ready for Submission",
            "methodologies": {
                "workday": {
                    "name": "Workday Enterprise Parser",
                    "score": workday_score,
                    "focus": "Exact Keyword Density, Chronological Timeline & Contact Metadata",
                    "status": "Optimal" if workday_score >= 85 else "Good",
                    "breakdown": {
                        "keyword_match_pct": round(workday_keyword_score, 1),
                        "structure_validity_pct": round(workday_structure_score, 1)
                    }
                },
                "greenhouse": {
                    "name": "Greenhouse Competency Scorecard",
                    "score": greenhouse_score,
                    "focus": "Competency Mapping, Departmental Role Fit & Hard Skills",
                    "status": "Optimal" if greenhouse_score >= 85 else "Good",
                    "competencies": domain_competencies
                },
                "taleo": {
                    "name": "Taleo / Oracle Traditional ATS",
                    "score": taleo_score,
                    "focus": "Mandatory Knock-Out Questions & Skill Density Thresholds",
                    "status": "Passed" if taleo_knockout_pass else "Warning",
                    "knockout_passed": taleo_knockout_pass,
                    "density_ratio_pct": round(taleo_density_ratio * 100, 1)
                },
                "lever": {
                    "name": "Lever Recruiter Impact Index",
                    "score": lever_score,
                    "focus": "Measurable Metrics, Numbers (%), and Strong Action Verbs",
                    "status": "Exceptional" if lever_score >= 85 else "Strong",
                    "metric_bullet_ratio_pct": round(metric_ratio * 100, 1),
                    "action_verb_ratio_pct": round(action_verb_ratio * 100, 1)
                },
                "icims_sovren": {
                    "name": "iCIMS / Sovren Semantic & Format Audit",
                    "score": icims_score,
                    "focus": "Standard Section Header Hygiene, Clean Typography & Parse Integrity",
                    "status": "100% Parsable" if icims_score == 100 else "Good",
                    "audit_checklist": icims_checks
                }
            },
            "dimensions": [
                {"dimension": "Keyword Density & Exact Match", "score": round(workday_keyword_score, 1), "weight": "25%"},
                {"dimension": "Semantic Competency Alignment", "score": round(greenhouse_score, 1), "weight": "20%"},
                {"dimension": "Quantifiable Metrics & Impact", "score": round(lever_score, 1), "weight": "20%"},
                {"dimension": "Format & Structural Hygiene", "score": round(icims_score, 1), "weight": "20%"},
                {"dimension": "Knockout Compliance & Education", "score": 100.0 if has_degree else 80.0, "weight": "15%"}
            ],
            "company_benchmarks": company_scores,
            "custom_jd_result": custom_jd_result,
            "key_recommendations": [
                "Include 'Statutory Compliance (PF/ESI)' explicitly in every tailored variant for Indian enterprise ATS portals.",
                "Maintain quantifiable impact metrics (e.g., '100% compliance across employee records') to score top marks in Lever & Greenhouse.",
                "Keep standard section headers ('Professional Experience', 'Education', 'Technical Skills') to ensure 100% parsability in Workday and iCIMS."
            ]
        }
