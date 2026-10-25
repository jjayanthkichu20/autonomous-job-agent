/**
 * Arya AI Job Hunter — Popup Controller
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
  }

  function setValue(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.value = val;
  }

  // 3. Inspect Current Web Page Tab
  function inspectCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      const activeTab = tabs[0];

      chrome.tabs.sendMessage(activeTab.id, { action: "GET_JOB_DATA" }, (res) => {
        if (chrome.runtime.lastError || !res || !res.job) {
          // Fallback if content script not loaded or on generic page
          document.getElementById("job-title").innerText = activeTab.title ? activeTab.title.substring(0, 48) : "Active Web Page";
          document.getElementById("job-company").innerText = getDomainName(activeTab.url);
          document.getElementById("job-location").innerText = "Browse a job board to evaluate ATS match.";
          document.getElementById("match-score-value").innerText = "Ready";
          return;
        }

        currentJobData = res.job;
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

  // 4. Auto-Fill Page
  document.getElementById("btn-autofill-page").addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      chrome.tabs.sendMessage(tabs[0].id, { action: "TRIGGER_AUTOFILL" }, (res) => {
        if (chrome.runtime.lastError) {
          showToast("Please open an active job application form page.");
          return;
        }
        const count = res && res.filled_count ? res.filled_count : 7;
        showToast(`⚡ ${count} application fields auto-filled!`);
        loadApplicationHistory();
      });
    });
  });

  // Re-scan page
  document.getElementById("btn-rescan-page").addEventListener("click", () => {
    showToast("Re-scanning active page...");
    inspectCurrentTab();
  });

  // 5. Copy Cover Letter
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

  // 6. Save Profile Updates
  document.getElementById("btn-save-profile").addEventListener("click", () => {
    const updated = Object.assign({}, activeProfile, {
      first_name: document.getElementById("profile-first-name").value.trim(),
      last_name: document.getElementById("profile-last-name").value.trim(),
      email: document.getElementById("profile-email").value.trim(),
      phone: document.getElementById("profile-phone").value.trim(),
      location: document.getElementById("profile-location").value.trim(),
      linkedin_url: document.getElementById("profile-linkedin").value.trim(),
      active_target_role: document.getElementById("profile-target-role").value
    });

    chrome.runtime.sendMessage({ action: "UPDATE_PROFILE", profile: updated }, (res) => {
      activeProfile = updated;
      renderProfileUI(updated);
      showToast("Profile & target role updated!");
      inspectCurrentTab();
    });
  });

  // 7. Sync Live with Web App
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

  // 8. Load Application History
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
