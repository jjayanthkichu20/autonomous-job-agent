/**
 * Arya AI Job Hunter — Popup Controller (Atom by JobAlchemy Style)
 * Full Copilot Integration: Profile Alignment, Mode Switching, and Smart Screening Q&A.
 */

document.addEventListener("DOMContentLoaded", () => {
  let activeProfile = null;
  let currentJobData = null;

  // 1. Tab Switching
  const navTabs = document.querySelectorAll(".nav-tab");
  const tabPanes = document.querySelectorAll(".tab-pane");

  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      navTabs.forEach(t => t.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add("active");

      if (targetId === "tab-history") {
        loadApplicationHistory();
      }
    });
  });

  // 2. Load Profile
  function loadProfile() {
    chrome.runtime.sendMessage({ action: "GET_PROFILE" }, (res) => {
      if (res && res.profile) {
        activeProfile = res.profile;
        renderProfileUI(activeProfile);
      }
    });
  }

  function renderProfileUI(p) {
    const headerTitle = document.getElementById("header-candidate-name");
    if (headerTitle) {
      headerTitle.innerText = `${p.first_name || ''} ${p.last_name || ''} • ${p.active_target_role || 'HR Executive'}`;
    }

    // Populate profile inputs
    setValue("profile-first-name", p.first_name);
    setValue("profile-last-name", p.last_name);
    setValue("profile-email", p.email);
    setValue("profile-phone", p.phone);
    setValue("profile-location", p.location);
    setValue("profile-linkedin", p.linkedin_url);

    const roleSelect = document.getElementById("profile-target-role");
    if (roleSelect && p.active_target_role) {
      roleSelect.value = p.active_target_role;
    }

    // Populate Atom-Style Screening Q&A memory
    const qa = p.qa_answers || {};
    setValue("qa-notice-period", qa.notice_period_text || (qa.notice_period_days ? `${qa.notice_period_days} Days` : "15 Days"));
    setValue("qa-experience", qa.years_of_experience ? (qa.years_of_experience.includes("Year") ? qa.years_of_experience : `${qa.years_of_experience} Years`) : "2 Years");
    setValue("qa-work-auth", qa.work_authorization || "Yes");
    setValue("qa-sponsorship", qa.require_sponsorship || "No");
    setValue("qa-expected-ctc", qa.expected_ctc || "₹5,50,000 / annum");

    // Initialize Mode UI
    updateModeUI(p.application_mode || "COPILOT");
  }

  function setValue(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.value = val;
  }

  // 3. Application Safety Mode Switcher (Atom Style)
  function updateModeUI(mode) {
    const copilotBtn = document.getElementById("pop-mode-copilot");
    const autopilotBtn = document.getElementById("pop-mode-autopilot");
    const autofillText = document.getElementById("btn-autofill-text");

    if (mode === "AUTOPILOT") {
      if (copilotBtn) copilotBtn.classList.remove("active");
      if (autopilotBtn) autopilotBtn.classList.add("active");
      if (autofillText) autofillText.innerText = "Auto-Fill & Auto-Submit (Auto-Pilot)";
    } else {
      if (copilotBtn) copilotBtn.classList.add("active");
      if (autopilotBtn) autopilotBtn.classList.remove("active");
      if (autofillText) autofillText.innerText = "Auto-Fill & Review (Co-Pilot)";
    }
  }

  function setApplicationMode(mode) {
    if (activeProfile) {
      activeProfile.application_mode = mode;
    }
    updateModeUI(mode);
    chrome.runtime.sendMessage({ action: "SET_MODE", mode: mode }, () => {
      showToast(mode === "COPILOT" 
        ? "🛡️ Co-Pilot Mode: Fills inputs, stops before submit for review" 
        : "⚡ Auto-Pilot Mode: Automated fill & submission enabled");
    });
  }

  const copilotBtn = document.getElementById("pop-mode-copilot");
  if (copilotBtn) {
    copilotBtn.addEventListener("click", () => setApplicationMode("COPILOT"));
  }

  const autopilotBtn = document.getElementById("pop-mode-autopilot");
  if (autopilotBtn) {
    autopilotBtn.addEventListener("click", () => setApplicationMode("AUTOPILOT"));
  }

  // 4. Inspect Current Web Page Tab
  function inspectCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      const activeTab = tabs[0];

      // Detect LinkedIn tab for Easy Apply trigger
      const isLinkedIn = activeTab.url && activeTab.url.includes("linkedin.com");
      const linkedInBtn = document.getElementById("btn-linkedin-easy-apply");
      if (linkedInBtn) {
        if (isLinkedIn) {
          linkedInBtn.classList.remove("hidden");
        } else {
          linkedInBtn.classList.add("hidden");
        }
      }

      chrome.tabs.sendMessage(activeTab.id, { action: "GET_JOB_DATA" }, (res) => {
        if (chrome.runtime.lastError || !res || !res.job) {
          // Fallback if content script not loaded or on generic page
          document.getElementById("job-title").innerText = activeTab.title ? activeTab.title.substring(0, 48) : "Active Web Page";
          document.getElementById("job-company").innerText = getDomainName(activeTab.url);
          document.getElementById("job-location").innerText = "Browse any job board (LinkedIn, Greenhouse, Lever, etc.)";
          document.getElementById("match-score-value").innerText = "Ready";
          return;
        }

        currentJobData = res.job;
        if (res.mode) {
          updateModeUI(res.mode);
        }
        renderJobData(res.job, res.cover_letter);
      });
    });
  }

  function getDomainName(url) {
    try {
      const u = new URL(url);
      return u.hostname.replace("www.", "").toUpperCase();
    } catch (e) {
      return "WEB PAGE";
    }
  }

  function renderJobData(job, coverLetter) {
    document.getElementById("job-title").innerText = job.title || "HR Position";
    document.getElementById("job-company").innerText = (job.company || "Company").toUpperCase();
    document.getElementById("job-location").innerText = job.location || "India / Remote";

    const scoreElem = document.getElementById("match-score-value");
    if (scoreElem) {
      scoreElem.innerText = `${job.match_score || 94}%`;
    }

    // Matched Tags
    const matchedContainer = document.getElementById("matched-tags");
    if (matchedContainer) {
      const matched = job.matched_keywords && job.matched_keywords.length ? job.matched_keywords : [
        "Recruitment", "HR Operations", "Onboarding", "HRMS"
      ];
      matchedContainer.innerHTML = matched.map(m => `<span class="tag tag-match">✓ ${m}</span>`).join("");
    }

    // Missing Tags
    const missingContainer = document.getElementById("missing-tags");
    if (missingContainer) {
      const missing = job.missing_keywords && job.missing_keywords.length ? job.missing_keywords : [
        "Statutory Compliance", "Payroll Inputs"
      ];
      missingContainer.innerHTML = missing.map(m => `<span class="tag tag-gap">+ ${m}</span>`).join("");
    }

    // Cover Letter Text
    const coverTextarea = document.getElementById("cover-letter-text");
    if (coverTextarea && coverLetter) {
      coverTextarea.value = coverLetter;
    }
  }

  // 5. Auto-Fill Page
  document.getElementById("btn-autofill-page").addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      chrome.tabs.sendMessage(tabs[0].id, { action: "TRIGGER_AUTOFILL" }, (res) => {
        if (chrome.runtime.lastError) {
          showToast("Please open an active job application form page.");
          return;
        }
        const count = res && res.filled_count ? res.filled_count : 7;
        const qCount = res && res.questions ? res.questions.length : 0;
        showToast(`⚡ ${count} fields filled & ${qCount} screening Q&A answered!`);
        loadApplicationHistory();
      });
    });
  });

  // LinkedIn Easy Apply Multi-Step
  const linkedInBtn = document.getElementById("btn-linkedin-easy-apply");
  if (linkedInBtn) {
    linkedInBtn.addEventListener("click", () => {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs || !tabs[0]) return;
        chrome.tabs.sendMessage(tabs[0].id, { action: "TRIGGER_LINKEDIN_APPLY" }, () => {
          showToast("🚀 LinkedIn Easy Apply initiated! Co-Pilot stepping through...");
        });
      });
    });
  }

  // Re-scan page
  document.getElementById("btn-rescan-page").addEventListener("click", () => {
    showToast("Re-scanning active page...");
    inspectCurrentTab();
  });

  // 6. Copy Cover Letter
  document.getElementById("btn-copy-cover").addEventListener("click", () => {
    const text = document.getElementById("cover-letter-text").value;
    navigator.clipboard.writeText(text).then(() => {
      showToast("Cover letter copied to clipboard!");
    });
  });

  // Inject Cover Letter into Page
  document.getElementById("btn-inject-cover").addEventListener("click", () => {
    const text = document.getElementById("cover-letter-text").value;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      chrome.tabs.sendMessage(tabs[0].id, { action: "SET_COVER_LETTER", text: text }, (res) => {
        if (res && res.status === "success") {
          showToast("Cover letter injected into page!");
        } else {
          navigator.clipboard.writeText(text);
          showToast("Copied to clipboard (no text area found on page)");
        }
      });
    });
  });

  // 7. Save Profile & Screening Q&A Updates
  document.getElementById("btn-save-profile").addEventListener("click", () => {
    const qaAnswers = Object.assign({}, (activeProfile && activeProfile.qa_answers) || {}, {
      notice_period_text: document.getElementById("qa-notice-period") ? document.getElementById("qa-notice-period").value.trim() : "15 Days",
      notice_period_days: document.getElementById("qa-notice-period") ? document.getElementById("qa-notice-period").value.replace(/\D/g, "") || "15" : "15",
      years_of_experience: document.getElementById("qa-experience") ? document.getElementById("qa-experience").value.trim() : "2 Years",
      work_authorization: document.getElementById("qa-work-auth") ? document.getElementById("qa-work-auth").value.trim() : "Yes",
      require_sponsorship: document.getElementById("qa-sponsorship") ? document.getElementById("qa-sponsorship").value.trim() : "No",
      expected_ctc: document.getElementById("qa-expected-ctc") ? document.getElementById("qa-expected-ctc").value.trim() : "₹5,50,000 / annum"
    });

    const updated = Object.assign({}, activeProfile, {
      first_name: document.getElementById("profile-first-name").value.trim(),
      last_name: document.getElementById("profile-last-name").value.trim(),
      email: document.getElementById("profile-email").value.trim(),
      phone: document.getElementById("profile-phone").value.trim(),
      location: document.getElementById("profile-location").value.trim(),
      linkedin_url: document.getElementById("profile-linkedin").value.trim(),
      active_target_role: document.getElementById("profile-target-role").value,
      qa_answers: qaAnswers
    });

    chrome.runtime.sendMessage({ action: "UPDATE_PROFILE", profile: updated }, () => {
      activeProfile = updated;
      renderProfileUI(updated);
      showToast("Profile & Screening Q&A saved!");
      inspectCurrentTab();
    });
  });

  // 8. Sync Live with Web App
  document.getElementById("btn-sync-webapp").addEventListener("click", () => {
    showToast("Syncing with live candidate database...");
    chrome.runtime.sendMessage({ action: "SYNC_WITH_WEB_APP" }, (res) => {
      if (res && res.status === "success") {
        activeProfile = res.profile;
        renderProfileUI(res.profile);
        showToast("Synchronized with live Arya Truth Store!");
      } else {
        showToast("Could not sync: " + (res ? res.message : "Network error"));
      }
    });
  });

  // 9. Load Application History
  function loadApplicationHistory() {
    chrome.runtime.sendMessage({ action: "GET_APPLICATIONS" }, (res) => {
      const container = document.getElementById("history-container");
      if (!container) return;

      const apps = res ? res.applications || [] : [];
      if (apps.length === 0) {
        container.innerHTML = `<div class="empty-state">No applications submitted via extension yet. Browse any job posting and click Auto-Fill!</div>`;
        return;
      }

      container.innerHTML = apps.map(a => `
        <div class="history-item">
          <div>
            <div class="history-title">${escapeHtml(a.job_title)}</div>
            <div class="history-company">${escapeHtml(a.company_name)} • ${new Date(a.applied_at).toLocaleDateString()}</div>
          </div>
          <span class="history-receipt">${a.confirmation_id}</span>
        </div>
      `).join("");
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function showToast(msg) {
    const toast = document.getElementById("popup-toast");
    if (!toast) return;
    toast.innerText = msg;
    toast.classList.remove("hidden");
    setTimeout(() => {
      toast.classList.add("hidden");
    }, 3000);
  }

  // Initialize
  loadProfile();
  inspectCurrentTab();
});
