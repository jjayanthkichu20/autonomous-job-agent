/**
 * Arya AI Job Hunter — Content Script
 * Detects job postings, extracts JD, calculates ATS match score, and auto-fills application forms.
 */

(function () {
  let cachedJobData = null;
  let activeProfile = null;

  // Retrieve candidate profile from background service worker
  chrome.runtime.sendMessage({ action: "GET_PROFILE" }, (response) => {
    if (response && response.profile) {
      activeProfile = response.profile;
      initAryaPageInspector();
    }
  });

  function isJobPostingPage() {
    const url = window.location.href.toLowerCase();
    const isJobDomain = url.includes("greenhouse.io") ||
      url.includes("lever.co") ||
      url.includes("linkedin.com/jobs") ||
      url.includes("indeed.com") ||
      url.includes("myworkdayjobs.com") ||
      url.includes("naukri.com") ||
      url.includes("wellfound.com") ||
      url.includes("glassdoor.com") ||
      url.includes("ziprecruiter.com") ||
      url.includes("ashbyhq.com") ||
      url.includes("smartrecruiters.com") ||
      url.includes("workable.com") ||
      url.includes("/job/") ||
      url.includes("/jobs/") ||
      url.includes("/careers/");

    const hasJobElements = document.querySelector('h1, [class*="job-title"], [class*="jobTitle"], [data-automation-id*="job"]');
    return isJobDomain || !!hasJobElements;
  }

  function extractJobDetails() {
    if (cachedJobData) return cachedJobData;

    let title = "";
    let company = "";
    let location = "";
    let description = "";

    // 1. Schema.org JSON-LD extraction
    const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const s of jsonLdScripts) {
      try {
        const parsed = JSON.parse(s.innerText);
        const item = Array.isArray(parsed) ? parsed.find(x => x['@type'] === 'JobPosting') : (parsed['@type'] === 'JobPosting' ? parsed : null);
        if (item) {
          title = item.title || "";
          company = item.hiringOrganization ? (item.hiringOrganization.name || "") : "";
          if (item.jobLocation && item.jobLocation.address) {
            const addr = item.jobLocation.address;
            location = addr.addressLocality || addr.addressRegion || addr.addressCountry || "";
          }
          description = item.description || "";
          break;
        }
      } catch (e) {}
    }

    // 2. DOM extraction fallbacks
    if (!title) {
      const titleElem = document.querySelector(
        'h1.app-title, h1[class*="job"], h1[class*="title"], [data-automation-id="jobPostingHeader"], .topcard__title, .jobsearch-JobInfoHeader-title, h1'
      );
      if (titleElem) title = titleElem.innerText.trim();
    }

    if (!company) {
      const compElem = document.querySelector(
        '[class*="company-name"], [class*="companyName"], [data-automation-id="companyName"], .topcard__org-name-link, [class*="employer"], a[href*="company"]'
      );
      if (compElem) {
        company = compElem.innerText.trim();
      } else {
        // Fallback from hostname
        const hostParts = window.location.hostname.split('.');
        if (hostParts.length >= 2) {
          company = hostParts[hostParts.length - 2].toUpperCase();
        }
      }
    }

    if (!location) {
      const locElem = document.querySelector(
        '.location, [class*="location"], [data-automation-id="jobPostingLocation"], .topcard__flavor--bullet'
      );
      if (locElem) location = locElem.innerText.trim();
    }

    if (!description) {
      const descElem = document.querySelector(
        '#content, [class*="description"], [data-automation-id="jobPostingDescription"], #job-details, .show-more-less-html__markup'
      );
      description = descElem ? descElem.innerText.trim() : document.body.innerText.substring(0, 4000);
    }

    // Clean up title
    if (title.length > 100) title = title.split('\n')[0].substring(0, 100);

    const matchAnalysis = analyzeATSScore(title, description);

    cachedJobData = {
      title: title || "HR Professional / Specialist",
      company: company || "Target Employer",
      location: location || "India / Remote",
      description: description,
      url: window.location.href,
      match_score: matchAnalysis.score,
      matched_keywords: matchAnalysis.matched,
      missing_keywords: matchAnalysis.missing
    };

    return cachedJobData;
  }

  function analyzeATSScore(title, descText) {
    const fullText = (title + " " + descText).toLowerCase();
    const candidateSkills = (activeProfile && activeProfile.skills) ? activeProfile.skills : [
      "Recruitment & Talent Acquisition",
      "HR Operations",
      "Onboarding & Induction",
      "HRIS / ATS Administration",
      "Statutory Compliance (PF, ESI, Labour Law)",
      "Advanced Excel",
      "Candidate Screening",
      "Employee Relations"
    ];

    const matched = [];
    const missing = [];

    candidateSkills.forEach(skill => {
      // Split into keywords
      const terms = skill.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(' ').filter(w => w.length > 2);
      const isMatch = terms.some(t => fullText.includes(t));
      if (isMatch) {
        matched.push(skill);
      } else {
        missing.push(skill);
      }
    });

    // Check title affinity
    const targetRole = (activeProfile && activeProfile.active_target_role) ? activeProfile.active_target_role.toLowerCase() : "hr executive";
    const titleMatches = fullText.includes("hr") || fullText.includes("human resources") || fullText.includes("talent") || fullText.includes("recruiter") || fullText.includes("people ops");

    let baseScore = 75;
    if (titleMatches) baseScore += 10;
    const skillRatio = matched.length / Math.max(1, candidateSkills.length);
    let finalScore = Math.min(98, Math.round(baseScore + (skillRatio * 15)));

    return {
      score: finalScore,
      matched: matched,
      missing: missing
    };
  }

  function generateTailoredCoverLetter(jobDetails) {
    const p = activeProfile || { first_name: "Jayanth", last_name: "J", email: "jjayanthheven20@gmail.com", phone: "+91 97783 91171" };
    const company = jobDetails.company || "Target Enterprise";
    const title = jobDetails.title || "HR Executive";

    return `Dear Hiring Team at ${company},

I am writing to express my enthusiastic interest in the ${title} opportunity at ${company}. With proven expertise across full-cycle talent acquisition, employee onboarding, and statutory compliance (PF, ESI, Labour Law) at Trackpi Private Limited, I am excited to contribute to your people operations.

In my recent work, I managed end-to-end recruitment pipelines and administered employee lifecycle records for 150+ personnel in HRMS systems with zero audit variances. The qualifications outlined in your opening align closely with my hands-on background in structured screening, candidate engagement, and HR compliance.

I would appreciate the chance to discuss how my skill set and proactive approach can support ${company}'s operational goals.

Warm regards,
${p.first_name} ${p.last_name}
${p.email} | ${p.phone}
LinkedIn: ${p.linkedin_url || 'linkedin.com/in/jayanth-j'}`;
  }

  function autofillApplicationForm() {
    const p = activeProfile || {
      first_name: "Jayanth",
      last_name: "J",
      email: "jjayanthheven20@gmail.com",
      phone: "+91 97783 91171",
      location: "Kottayam, Kerala, India",
      linkedin_url: "https://linkedin.com/in/jayanth-j"
    };

    const job = extractJobDetails();
    const coverLetter = generateTailoredCoverLetter(job);

    let filledCount = 0;
    const inputs = Array.from(document.querySelectorAll("input, textarea, select"));

    function setNativeValue(element, value) {
      if (!element || value === undefined || value === null) return;
      const lastValue = element.value;
      element.value = value;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      element.dispatchEvent(new Event("blur", { bubbles: true }));
      element.classList.add("arya-autofilled-field");
      filledCount++;
    }

    inputs.forEach(input => {
      if (input.type === "hidden" || input.type === "submit" || input.type === "button") return;

      const name = (input.name || "").toLowerCase();
      const id = (input.id || "").toLowerCase();
      const placeholder = (input.placeholder || "").toLowerCase();
      const aria = (input.getAttribute("aria-label") || "").toLowerCase();
      const autocomplete = (input.getAttribute("autocomplete") || "").toLowerCase();

      // Check surrounding label text
      let labelText = "";
      if (input.labels && input.labels.length) {
        labelText = input.labels[0].innerText.toLowerCase();
      } else {
        const parentLabel = input.closest("label");
        if (parentLabel) labelText = parentLabel.innerText.toLowerCase();
      }

      const matchKey = `${name} ${id} ${placeholder} ${aria} ${autocomplete} ${labelText}`;

      // First Name
      if (matchKey.includes("first") && matchKey.includes("name") || autocomplete === "given-name") {
        setNativeValue(input, p.first_name);
      }
      // Last Name
      else if (matchKey.includes("last") && matchKey.includes("name") || autocomplete === "family-name") {
        setNativeValue(input, p.last_name);
      }
      // Full Name
      else if ((matchKey.includes("full") && matchKey.includes("name")) || (matchKey.includes("candidate_name")) || (name === "name" && !matchKey.includes("first") && !matchKey.includes("last"))) {
        setNativeValue(input, `${p.first_name} ${p.last_name}`);
      }
      // Email
      else if (input.type === "email" || matchKey.includes("email") || autocomplete === "email") {
        setNativeValue(input, p.email);
      }
      // Phone
      else if (input.type === "tel" || matchKey.includes("phone") || matchKey.includes("mobile") || matchKey.includes("contact") || autocomplete === "tel") {
        setNativeValue(input, p.phone);
      }
      // LinkedIn
      else if (matchKey.includes("linkedin") || placeholder.includes("linkedin.com")) {
        setNativeValue(input, p.linkedin_url);
      }
      // Location / City / Address
      else if (matchKey.includes("city") || matchKey.includes("location") || matchKey.includes("address")) {
        setNativeValue(input, p.location || "Bangalore, India");
      }
      // Current Company / Employer
      else if (matchKey.includes("company") || matchKey.includes("employer") || matchKey.includes("organization")) {
        setNativeValue(input, p.current_company || "Trackpi Private Limited");
      }
      // Current Title
      else if (matchKey.includes("title") || matchKey.includes("current role") || matchKey.includes("position")) {
        setNativeValue(input, p.current_role || "HR Executive");
      }
      // Website / Portfolio
      else if (matchKey.includes("website") || matchKey.includes("portfolio") || matchKey.includes("url")) {
        setNativeValue(input, p.portfolio_url || "https://jjayanthkichu20.github.io/autonomous-job-agent/");
      }
      // Cover Letter
      else if (input.tagName.toLowerCase() === "textarea" && (matchKey.includes("cover") || matchKey.includes("letter") || matchKey.includes("comment") || matchKey.includes("note") || matchKey.includes("message"))) {
        setNativeValue(input, coverLetter);
      }
    });

    // Notify user with on-page toast
    showPageToast(`⚡ Auto-filled ${filledCount} fields with Jayanth's calibrated CV!`);

    // Record application in background storage ledger
    chrome.runtime.sendMessage({
      action: "RECORD_APPLICATION",
      job_title: job.title,
      company_name: job.company,
      job_url: job.url,
      match_score: job.match_score
    });

    return filledCount;
  }

  function showPageToast(message) {
    const existing = document.getElementById("arya-page-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "arya-page-toast";
    toast.innerHTML = `<span>✓</span><span>${message}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.5s ease";
      setTimeout(() => toast.remove(), 500);
    }, 4000);
  }

  function injectFloatingWidget(job) {
    if (document.getElementById("arya-floating-pill")) return;

    const widget = document.createElement("div");
    widget.id = "arya-floating-pill";
    widget.innerHTML = `
      <div class="arya-logo-badge">✦</div>
      <div class="arya-meta">
        <div class="arya-title-row">
          <span class="arya-title">Arya AI Agent</span>
          <span class="arya-score-tag">${job.match_score}% Match</span>
        </div>
        <div class="arya-subtitle" title="${job.title} at ${job.company}">${job.title} • ${job.company}</div>
      </div>
      <div class="arya-actions">
        <button id="arya-btn-autofill-action" class="arya-btn-fill" title="Auto-fill with Jayanth's profile & tailored cover letter">
          ⚡ Auto-Fill
        </button>
        <button id="arya-btn-dismiss" class="arya-btn-close" title="Dismiss">✕</button>
      </div>
    `;

    document.body.appendChild(widget);

    document.getElementById("arya-btn-autofill-action").addEventListener("click", () => {
      autofillApplicationForm();
    });

    document.getElementById("arya-btn-dismiss").addEventListener("click", () => {
      widget.remove();
    });
  }

  function initAryaPageInspector() {
    if (!isJobPostingPage()) return;

    setTimeout(() => {
      const job = extractJobDetails();
      injectFloatingWidget(job);
    }, 1200);
  }

  // Handle messages from popup or background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_JOB_DATA") {
      const job = extractJobDetails();
      const coverLetter = generateTailoredCoverLetter(job);
      sendResponse({ status: "success", job: job, cover_letter: coverLetter });
      return true;
    }

    if (request.action === "TRIGGER_AUTOFILL") {
      const count = autofillApplicationForm();
      sendResponse({ status: "success", filled_count: count });
      return true;
    }

    if (request.action === "SET_COVER_LETTER") {
      const textareas = document.querySelectorAll("textarea");
      let filled = false;
      textareas.forEach(t => {
        const key = (t.name + " " + t.id + " " + t.placeholder).toLowerCase();
        if (key.includes("cover") || key.includes("letter") || key.includes("message") || textareas.length === 1) {
          t.value = request.text;
          t.dispatchEvent(new Event("input", { bubbles: true }));
          t.dispatchEvent(new Event("change", { bubbles: true }));
          filled = true;
        }
      });
      sendResponse({ status: filled ? "success" : "not_found" });
      return true;
    }
  });
})();
