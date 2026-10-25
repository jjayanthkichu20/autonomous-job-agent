/**
 * Arya AI Job Hunter — Content Script (Atom by JobAlchemy Style)
 * Full Auto-Apply Copilot: Form Autofill, Smart Screening Q&A, and ATS Match Alignment.
 */

(function () {
  let cachedJobData = null;
  let activeProfile = null;
  let currentAppMode = "COPILOT"; // "COPILOT" (stops before submit) or "AUTOPILOT" (full auto-submit)

  // 1. Retrieve Candidate Profile from Background
  chrome.runtime.sendMessage({ action: "GET_PROFILE" }, (response) => {
    if (response && response.profile) {
      activeProfile = response.profile;
      currentAppMode = activeProfile.application_mode || "COPILOT";
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

    const hasJobElements = document.querySelector('h1, [class*="job-title"], [class*="jobTitle"], [data-automation-id*="job"], form[action*="apply"]');
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
      const terms = skill.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(' ').filter(w => w.length > 2);
      const isMatch = terms.some(t => fullText.includes(t));
      if (isMatch) {
        matched.push(skill);
      } else {
        missing.push(skill);
      }
    });

    const titleMatches = fullText.includes("hr") || fullText.includes("human resources") || fullText.includes("talent") || fullText.includes("recruiter") || fullText.includes("people ops");

    let baseScore = 76;
    if (titleMatches) baseScore += 10;
    const skillRatio = matched.length / Math.max(1, candidateSkills.length);
    let finalScore = Math.min(98, Math.round(baseScore + (skillRatio * 14)));

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

I am writing to express my enthusiastic interest in the ${title} position at ${company}. With demonstrated experience across full-cycle talent acquisition, structured employee onboarding, and statutory compliance (PF, ESI, Labour Law) at Trackpi Private Limited, I am well-prepared to make an immediate impact on your people operations.

At Trackpi, I managed end-to-end recruitment pipelines, screened hundreds of qualified candidates, and maintained complete employee lifecycle records for 150+ staff across HRMS software with zero audit variances. The requirements outlined in your job opening closely align with my background in talent sourcing, HR operations, and proactive candidate engagement.

I would welcome the opportunity to discuss how my hands-on background and verified skill set align with your hiring goals.

Warm regards,
${p.first_name} ${p.last_name}
${p.email} | ${p.phone}
LinkedIn: ${p.linkedin_url || 'linkedin.com/in/jayanth-j'}`;
  }

  // ==========================================
  // SMART FORM AUTOFILL ENGINE (Atom-Style)
  // ==========================================
  function autofillApplicationForm(overrideMode) {
    const mode = overrideMode || currentAppMode;
    const p = activeProfile || {
      first_name: "Jayanth",
      last_name: "J",
      email: "jjayanthheven20@gmail.com",
      phone: "+91 97783 91171",
      location: "Kottayam, Kerala / Bangalore, India",
      linkedin_url: "https://linkedin.com/in/jayanth-j"
    };

    const qa = (activeProfile && activeProfile.qa_answers) ? activeProfile.qa_answers : {
      years_of_experience: "2",
      notice_period_days: "15",
      work_authorization: "Yes",
      require_sponsorship: "No",
      current_ctc: "₹4,50,000 / annum",
      expected_ctc: "₹5,50,000 - ₹6,50,000 / annum",
      willing_to_relocate: "Yes"
    };

    const job = extractJobDetails();
    const coverLetter = generateTailoredCoverLetter(job);

    let filledCount = 0;
    const answeredQuestions = [];

    function setElementValue(element, value) {
      if (!element || value === undefined || value === null) return;
      try {
        // Trigger React 16+ value tracker
        const nativeSetter = Object.getOwnPropertyDescriptor(
          element.tagName === "TEXTAREA" ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype,
          'value'
        );
        if (nativeSetter && nativeSetter.set) {
          nativeSetter.set.call(element, value);
        } else {
          element.value = value;
        }
      } catch (e) {
        element.value = value;
      }

      element.dispatchEvent(new Event("input", { bubbles: true }));
      element.dispatchEvent(new Event("change", { bubbles: true }));
      element.dispatchEvent(new Event("blur", { bubbles: true }));
      element.classList.add("arya-autofilled-field");
      filledCount++;
    }

    // 1. Process Text Inputs & Textareas
    const textInputs = Array.from(document.querySelectorAll("input, textarea"));
    textInputs.forEach(input => {
      if (input.type === "hidden" || input.type === "submit" || input.type === "button" || input.type === "radio" || input.type === "checkbox") return;

      const name = (input.name || "").toLowerCase();
      const id = (input.id || "").toLowerCase();
      const placeholder = (input.placeholder || "").toLowerCase();
      const aria = (input.getAttribute("aria-label") || "").toLowerCase();
      const autocomplete = (input.getAttribute("autocomplete") || "").toLowerCase();

      let labelText = "";
      if (input.labels && input.labels.length) {
        labelText = input.labels[0].innerText.toLowerCase();
      } else {
        const parentLabel = input.closest("label, [class*='field'], [class*='form-group']");
        if (parentLabel) labelText = parentLabel.innerText.toLowerCase();
      }

      const key = `${name} ${id} ${placeholder} ${aria} ${autocomplete} ${labelText}`;

      // First Name
      if ((key.includes("first") && key.includes("name")) || autocomplete === "given-name") {
        setElementValue(input, p.first_name);
      }
      // Last Name
      else if ((key.includes("last") && key.includes("name")) || autocomplete === "family-name") {
        setElementValue(input, p.last_name);
      }
      // Full Name
      else if ((key.includes("full") && key.includes("name")) || (key.includes("candidate_name")) || (name === "name" && !key.includes("first") && !key.includes("last"))) {
        setElementValue(input, `${p.first_name} ${p.last_name}`);
      }
      // Email
      else if (input.type === "email" || key.includes("email") || autocomplete === "email") {
        setElementValue(input, p.email);
      }
      // Phone
      else if (input.type === "tel" || key.includes("phone") || key.includes("mobile") || key.includes("contact") || autocomplete === "tel") {
        setElementValue(input, p.phone);
      }
      // LinkedIn
      else if (key.includes("linkedin") || placeholder.includes("linkedin.com")) {
        setElementValue(input, p.linkedin_url);
      }
      // Location / City / Address
      else if (key.includes("city") || key.includes("location") || key.includes("address")) {
        setElementValue(input, p.location || "Bangalore, India");
      }
      // Current Company
      else if (key.includes("company") || key.includes("employer") || key.includes("organization")) {
        setElementValue(input, p.current_company || "Trackpi Private Limited");
      }
      // Current Title
      else if (key.includes("title") || key.includes("current role") || key.includes("position")) {
        setElementValue(input, p.current_role || "HR Executive");
      }
      // Website / Portfolio
      else if (key.includes("website") || key.includes("portfolio") || key.includes("url")) {
        setElementValue(input, p.portfolio_url || "https://jjayanthkichu20.github.io/autonomous-job-agent/");
      }
      // Notice Period screening question
      else if (key.includes("notice") || key.includes("how soon") || key.includes("start date")) {
        setElementValue(input, qa.notice_period_days || "15");
        answeredQuestions.push({ q: "Notice Period", a: qa.notice_period_days + " Days" });
      }
      // Years of Experience screening question
      else if (key.includes("years") && (key.includes("experience") || key.includes("hr"))) {
        setElementValue(input, qa.years_of_experience || "2");
        answeredQuestions.push({ q: "Years of Experience", a: qa.years_of_experience + " Years" });
      }
      // Expected Salary / Compensation
      else if (key.includes("salary") || key.includes("ctc") || key.includes("compensation") || key.includes("expected pay")) {
        setElementValue(input, qa.expected_ctc || "₹5,50,000 / annum");
        answeredQuestions.push({ q: "Expected Compensation", a: qa.expected_ctc });
      }
      // Cover Letter
      else if (input.tagName.toLowerCase() === "textarea" && (key.includes("cover") || key.includes("letter") || key.includes("comment") || key.includes("message") || key.includes("note"))) {
        setElementValue(input, coverLetter);
      }
    });

    // 2. Process Select Dropdowns (Smart Screening Q&A)
    const selects = Array.from(document.querySelectorAll("select"));
    selects.forEach(select => {
      let labelText = "";
      if (select.labels && select.labels.length) {
        labelText = select.labels[0].innerText.toLowerCase();
      } else {
        const parent = select.closest("label, [class*='field'], [class*='form-group']");
        if (parent) labelText = parent.innerText.toLowerCase();
      }
      const key = `${select.name || ''} ${select.id || ''} ${labelText}`.toLowerCase();

      function chooseOption(predicate) {
        for (let i = 0; i < select.options.length; i++) {
          const opt = select.options[i];
          if (predicate(opt.text.toLowerCase(), opt.value.toLowerCase())) {
            select.selectedIndex = i;
            select.dispatchEvent(new Event("change", { bubbles: true }));
            select.classList.add("arya-autofilled-field");
            filledCount++;
            return opt.text;
          }
        }
        return null;
      }

      // Work Authorization
      if (key.includes("authorized") || key.includes("authorization") || key.includes("legal") || key.includes("eligible to work")) {
        const chosen = chooseOption((t, v) => t.includes("yes") || v === "yes" || v === "true");
        if (chosen) answeredQuestions.push({ q: "Legally Authorized to Work", a: "Yes" });
      }
      // Sponsorship
      else if (key.includes("sponsorship") || key.includes("visa") || key.includes("require sponsor")) {
        const chosen = chooseOption((t, v) => t.includes("no") || v === "no" || v === "false");
        if (chosen) answeredQuestions.push({ q: "Requires Visa Sponsorship", a: "No" });
      }
      // Notice Period
      else if (key.includes("notice") || key.includes("availability")) {
        const chosen = chooseOption((t) => t.includes("15") || t.includes("immediate") || t.includes("1 month") || t.includes("less than"));
        if (chosen) answeredQuestions.push({ q: "Notice Period", a: chosen });
      }
      // Experience Level
      else if (key.includes("experience") || key.includes("years")) {
        const chosen = chooseOption((t) => t.includes("2") || t.includes("1-3") || t.includes("1 - 3") || t.includes("2-4"));
        if (chosen) answeredQuestions.push({ q: "Experience Range", a: chosen });
      }
      // Education Degree
      else if (key.includes("degree") || key.includes("education")) {
        const chosen = chooseOption((t) => t.includes("bachelor") || t.includes("b.tech") || t.includes("graduate"));
        if (chosen) answeredQuestions.push({ q: "Highest Degree", a: chosen });
      }
    });

    // 3. Process Radio Buttons (Yes / No Screening Questions)
    const radioGroups = {};
    document.querySelectorAll("input[type='radio']").forEach(radio => {
      const name = radio.name || "unnamed";
      if (!radioGroups[name]) radioGroups[name] = [];
      radioGroups[name].push(radio);
    });

    Object.keys(radioGroups).forEach(groupName => {
      const radios = radioGroups[groupName];
      const container = radios[0].closest("fieldset, [class*='field'], [class*='form-group'], tr, div");
      const contextText = container ? container.innerText.toLowerCase() : groupName.toLowerCase();

      // Authorized to work -> Click "Yes"
      if (contextText.includes("authorized") || contextText.includes("eligible to work")) {
        const yesRadio = radios.find(r => r.value.toLowerCase() === "yes" || (r.labels && r.labels[0] && r.labels[0].innerText.toLowerCase().includes("yes")));
        if (yesRadio && !yesRadio.checked) {
          yesRadio.click();
          yesRadio.dispatchEvent(new Event("change", { bubbles: true }));
          filledCount++;
          answeredQuestions.push({ q: "Work Authorization", a: "Yes" });
        }
      }
      // Sponsorship required -> Click "No"
      else if (contextText.includes("sponsorship") || contextText.includes("sponsor")) {
        const noRadio = radios.find(r => r.value.toLowerCase() === "no" || (r.labels && r.labels[0] && r.labels[0].innerText.toLowerCase().includes("no")));
        if (noRadio && !noRadio.checked) {
          noRadio.click();
          noRadio.dispatchEvent(new Event("change", { bubbles: true }));
          filledCount++;
          answeredQuestions.push({ q: "Requires Sponsorship", a: "No" });
        }
      }
    });

    // 4. Handle Checkboxes (Consent / Policy agreements)
    document.querySelectorAll("input[type='checkbox']").forEach(cb => {
      const label = cb.closest("label") || cb.parentElement;
      const text = label ? label.innerText.toLowerCase() : "";
      if (text.includes("agree") || text.includes("consent") || text.includes("privacy") || text.includes("certify") || text.includes("terms")) {
        if (!cb.checked) {
          cb.click();
          cb.dispatchEvent(new Event("change", { bubbles: true }));
          filledCount++;
        }
      }
    });

    // Record application in background storage ledger
    chrome.runtime.sendMessage({
      action: "RECORD_APPLICATION",
      job_title: job.title,
      company_name: job.company,
      job_url: job.url,
      match_score: job.match_score,
      fields_filled: filledCount,
      mode: mode,
      submitted: mode === "AUTOPILOT"
    });

    // Update the on-page drawer Q&A display
    updateDrawerQADisplay(answeredQuestions);

    // Atom-style "Stop Before Submit" vs Auto-Pilot handling
    if (mode === "COPILOT") {
      showPageToast(`🛡️ Co-Pilot Ready: ${filledCount} fields & Q&A populated! Review and click Submit.`);
      // Smooth scroll to top of application form for candidate inspection
      const firstInput = document.querySelector(".arya-autofilled-field");
      if (firstInput) firstInput.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      showPageToast(`⚡ Auto-Pilot Active: ${filledCount} fields filled! Submitting application...`);
      setTimeout(() => {
        const submitBtn = document.querySelector("input[type='submit'], button[type='submit'], button[id*='submit'], button[class*='submit']");
        if (submitBtn) {
          submitBtn.click();
          showPageToast("✅ Application submitted successfully by Arya Auto-Pilot!");
        }
      }, 1500);
    }

    return { filled: filledCount, questions: answeredQuestions };
  }

  // ==========================================
  // LINKEDIN EASY APPLY MULTI-STEP AUTOMATION
  // ==========================================
  async function runLinkedInEasyApply() {
    showPageToast("⚡ Arya Copilot: Automating LinkedIn Easy Apply...");
    const easyApplyBtn = document.querySelector(".jobs-apply-button, button[aria-label*='Easy Apply']");
    if (easyApplyBtn) {
      easyApplyBtn.click();
      await new Promise(r => setTimeout(r, 800));
    }

    // Step navigation loop (up to 6 steps)
    for (let step = 0; step < 6; step++) {
      autofillApplicationForm("COPILOT");
      await new Promise(r => setTimeout(r, 600));

      const nextBtn = document.querySelector("button[aria-label='Continue to next step'], button[data-easy-apply-next-button]");
      const reviewBtn = document.querySelector("button[aria-label='Review your application']");

      if (reviewBtn) {
        reviewBtn.click();
        showPageToast("🛡️ Co-Pilot Safety Stop: Ready for final review before submission!");
        break;
      } else if (nextBtn) {
        nextBtn.click();
        await new Promise(r => setTimeout(r, 800));
      } else {
        break;
      }
    }
  }

  // ==========================================
  // ON-PAGE COPILOT DRAWER & FLOATING TRIGGER
  // ==========================================
  function injectOnPageCopilot(job) {
    if (document.getElementById("arya-floating-pill")) return;

    // 1. Floating Launch Pill
    const pill = document.createElement("div");
    pill.id = "arya-floating-pill";
    pill.innerHTML = `
      <div class="arya-logo-badge">✦</div>
      <div class="arya-meta">
        <div class="arya-title-row">
          <span class="arya-title">Arya AI Copilot</span>
          <span class="arya-score-tag">${job.match_score}% Match</span>
        </div>
        <div class="arya-subtitle" title="${job.title} at ${job.company}">${job.title} • ${job.company}</div>
      </div>
      <div class="arya-actions">
        <button id="arya-btn-quick-fill" class="arya-btn-fill">⚡ Auto-Fill</button>
        <button id="arya-btn-close-pill" class="arya-btn-close">✕</button>
      </div>
    `;

    // 2. Atom-Style Slide-Out Copilot Drawer
    const drawer = document.createElement("div");
    drawer.id = "arya-copilot-drawer";
    drawer.innerHTML = `
      <div class="arya-drawer-header">
        <div class="arya-drawer-brand">
          <div class="arya-logo-badge">✦</div>
          <div>
            <div class="arya-drawer-title">Arya AI Copilot</div>
            <div class="arya-drawer-candidate">${activeProfile.first_name || 'Jayanth'} J • ${activeProfile.active_target_role || 'HR Executive'}</div>
          </div>
        </div>
        <button id="arya-drawer-close-btn" class="arya-drawer-close">✕ Close</button>
      </div>

      <div class="arya-drawer-body">
        <!-- Job & Score Card -->
        <div class="arya-card">
          <div class="arya-score-row">
            <div>
              <div class="arya-job-heading">${job.title}</div>
              <div class="arya-job-sub">${job.company} • ${job.location}</div>
            </div>
            <div class="arya-score-badge-big">
              <span class="arya-score-num">${job.match_score}%</span>
              <span class="arya-score-sub">ATS</span>
            </div>
          </div>
        </div>

        <!-- Mode Selector -->
        <div class="arya-card">
          <div class="arya-card-title">Application Safety Mode</div>
          <div class="arya-mode-switcher">
            <button id="mode-copilot-btn" class="arya-mode-btn ${currentAppMode === 'COPILOT' ? 'active' : ''}">🛡️ Co-Pilot (Review)</button>
            <button id="mode-autopilot-btn" class="arya-mode-btn ${currentAppMode === 'AUTOPILOT' ? 'active' : ''}">⚡ Auto-Pilot</button>
          </div>
          <div class="arya-mode-hint" id="arya-mode-description">
            ${currentAppMode === 'COPILOT' ? 'Stops before the final submit button so you can verify answers.' : 'Automatically submits application directly upon completion.'}
          </div>
        </div>

        <!-- Main Auto-Fill Action -->
        <button id="arya-drawer-autofill-btn" class="arya-btn-main">
          <span>⚡ Auto-Fill Application & Screening Q&A</span>
        </button>

        ${window.location.hostname.includes("linkedin.com") ? `
          <button id="arya-drawer-linkedin-btn" class="arya-btn-main" style="background: linear-gradient(135deg, #0a66c2, #004182);">
            <span>🚀 Run LinkedIn Easy Apply Multi-Step</span>
          </button>
        ` : ''}

        <!-- Screening Q&A Panel -->
        <div class="arya-card">
          <div class="arya-card-title">Answered Screening Questions</div>
          <div id="arya-answered-qa-container">
            <div class="arya-qa-item">
              <div class="arya-qa-question">Notice Period:</div>
              <div class="arya-qa-answer">15 Days (Immediate availability)</div>
            </div>
            <div class="arya-qa-item">
              <div class="arya-qa-question">Work Authorization & Sponsorship:</div>
              <div class="arya-qa-answer">Authorized: Yes | Sponsorship: No</div>
            </div>
            <div class="arya-qa-item">
              <div class="arya-qa-question">Experience Alignment:</div>
              <div class="arya-qa-answer">2+ Years (Trackpi HR Executive)</div>
            </div>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(pill);
    document.body.appendChild(drawer);

    // Event Listeners
    pill.addEventListener("click", (e) => {
      if (e.target.id === "arya-btn-close-pill") {
        pill.remove();
        return;
      }
      if (e.target.id === "arya-btn-quick-fill") {
        autofillApplicationForm();
        return;
      }
      drawer.classList.add("arya-open");
    });

    document.getElementById("arya-drawer-close-btn").addEventListener("click", () => {
      drawer.classList.remove("arya-open");
    });

    document.getElementById("arya-drawer-autofill-btn").addEventListener("click", () => {
      autofillApplicationForm();
    });

    const liBtn = document.getElementById("arya-drawer-linkedin-btn");
    if (liBtn) {
      liBtn.addEventListener("click", () => {
        runLinkedInEasyApply();
      });
    }

    // Mode Switcher Handlers
    document.getElementById("mode-copilot-btn").addEventListener("click", () => {
      currentAppMode = "COPILOT";
      document.getElementById("mode-copilot-btn").classList.add("active");
      document.getElementById("mode-autopilot-btn").classList.remove("active");
      document.getElementById("arya-mode-description").innerText = "Stops before the final submit button so you can verify answers.";
      chrome.runtime.sendMessage({ action: "SET_MODE", mode: "COPILOT" });
    });

    document.getElementById("mode-autopilot-btn").addEventListener("click", () => {
      currentAppMode = "AUTOPILOT";
      document.getElementById("mode-autopilot-btn").classList.add("active");
      document.getElementById("mode-copilot-btn").classList.remove("active");
      document.getElementById("arya-mode-description").innerText = "Automatically submits application directly upon completion.";
      chrome.runtime.sendMessage({ action: "SET_MODE", mode: "AUTOPILOT" });
    });
  }

  function updateDrawerQADisplay(answeredList) {
    const container = document.getElementById("arya-answered-qa-container");
    if (!container || !answeredList || !answeredList.length) return;

    container.innerHTML = answeredList.map(item => `
      <div class="arya-qa-item">
        <div class="arya-qa-question">${item.q}:</div>
        <div class="arya-qa-answer">${item.a}</div>
      </div>
    `).join("");
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
    }, 4500);
  }

  function initAryaPageInspector() {
    if (!isJobPostingPage()) return;

    setTimeout(() => {
      const job = extractJobDetails();
      injectOnPageCopilot(job);
    }, 1200);
  }

  // Handle messages from popup or background
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "GET_JOB_DATA") {
      const job = extractJobDetails();
      const coverLetter = generateTailoredCoverLetter(job);
      sendResponse({ status: "success", job: job, cover_letter: coverLetter, mode: currentAppMode });
      return true;
    }

    if (request.action === "TRIGGER_AUTOFILL") {
      const result = autofillApplicationForm();
      sendResponse({ status: "success", filled_count: result.filled, questions: result.questions });
      return true;
    }

    if (request.action === "TRIGGER_LINKEDIN_APPLY") {
      runLinkedInEasyApply();
      sendResponse({ status: "success" });
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
