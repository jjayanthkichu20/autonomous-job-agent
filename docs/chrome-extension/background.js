/**
 * Arya AI Job Hunter — Background Service Worker (Manifest V3)
 * Full Auto-Apply & Screening Q&A Copilot Engine
 */

const DEFAULT_PROFILE = {
  first_name: "Jayanth",
  last_name: "J",
  email: "jjayanthheven20@gmail.com",
  phone: "+91 97783 91171",
  location: "Kottayam, Kerala / Bangalore, India",
  linkedin_url: "https://linkedin.com/in/jayanth-j",
  portfolio_url: "https://jjayanthkichu20.github.io/autonomous-job-agent/",
  current_role: "HR Executive",
  current_company: "Trackpi Private Limited",
  target_roles: ["HR Executive", "HR Operations Executive", "Talent Acquisition Specialist"],
  active_target_role: "HR Executive",
  skills: [
    "Recruitment & Talent Acquisition",
    "HR Operations",
    "Onboarding & Induction",
    "HRIS / ATS Administration",
    "Statutory Compliance (PF, ESI, Labour Law)",
    "Advanced Excel & Reporting",
    "Candidate Sourcing & Screening",
    "Employee Relations"
  ],
  education: {
    institution: "APJ Abdul Kalam Technological University",
    degree: "Bachelor of Technology (B.Tech)",
    field_of_study: "Mechanical Engineering",
    graduation_year: 2024
  },
  experience: {
    company: "Trackpi Private Limited",
    role: "HR Executive",
    period: "2022 - Present",
    achievements: [
      "Spearheaded end-to-end talent acquisition pipelines for technical and operational positions, cutting time-to-hire by 28%.",
      "Administered employee lifecycle records for 150+ staff across HRMS software with 100% data audit compliance.",
      "Coordinated weekly new-hire induction and orientation programs, maintaining 96% positive candidate feedback rating."
    ]
  },
  // Application Mode: "COPILOT" (stops before final submit for safety review) or "AUTOPILOT" (full auto-submit)
  application_mode: "COPILOT",
  
  // Knowledge Base for Smart Screening Questions (Atom by JobAlchemy style)
  qa_answers: {
    years_of_experience: "2",
    years_hr_experience: "2",
    notice_period_days: "15",
    notice_period_text: "15 Days (Immediate joiner available)",
    work_authorization: "Yes",
    require_sponsorship: "No",
    current_ctc: "₹4,50,000 / annum",
    expected_ctc: "₹5,50,000 - ₹6,50,000 / annum",
    willing_to_relocate: "Yes",
    comfortable_with_hybrid_remote: "Yes",
    gender: "Male",
    highest_degree: "Bachelor of Technology",
    university: "APJ Abdul Kalam Technological University",
    graduation_year: "2024",
    why_hire_me: "I bring 2+ years of verified hands-on experience managing end-to-end recruitment pipelines, onboarding, and statutory compliance (PF, ESI) at Trackpi Private Limited with 100% audit accuracy.",
    difficult_situation: "When onboarding was delayed due to documentation discrepancies, I developed a standardized automated pre-joining checklist in HRMS, eliminating onboarding bottlenecks and achieving 100% data audit compliance."
  }
};

// Initialize extension on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(["arya_profile", "arya_extension_apps"], (result) => {
    if (!result.arya_profile) {
      chrome.storage.local.set({ arya_profile: DEFAULT_PROFILE });
    } else {
      // Ensure new QA answers and mode exist
      const merged = Object.assign({}, DEFAULT_PROFILE, result.arya_profile);
      if (!merged.qa_answers) merged.qa_answers = DEFAULT_PROFILE.qa_answers;
      if (!merged.application_mode) merged.application_mode = "COPILOT";
      chrome.storage.local.set({ arya_profile: merged });
    }

    if (!result.arya_extension_apps) {
      chrome.storage.local.set({ arya_extension_apps: [] });
    }
  });

  // Enable sidePanel behavior on action click if API exists
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => {});
  }

  // Create context menus for quick on-page actions safely
  if (chrome.contextMenus && chrome.contextMenus.removeAll) {
    chrome.contextMenus.removeAll(() => {
      chrome.contextMenus.create({
        id: "arya_autofill_page",
        title: "⚡ Auto-Fill Application Form (Arya Copilot)",
        contexts: ["page", "editable"]
      });

      chrome.contextMenus.create({
        id: "arya_evaluate_ats",
        title: "📊 Evaluate ATS Match with Jayanth's CV",
        contexts: ["selection", "page"]
      });
    });
  }
});

// Context Menu listener
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "arya_autofill_page") {
    chrome.tabs.sendMessage(tab.id, { action: "TRIGGER_AUTOFILL" });
  } else if (info.menuItemId === "arya_evaluate_ats") {
    chrome.tabs.sendMessage(tab.id, {
      action: "EVALUATE_SELECTED_TEXT",
      selectedText: info.selectionText || ""
    });
  }
});

// Message hub between background, content scripts, and popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_PROFILE") {
    chrome.storage.local.get(["arya_profile"], (res) => {
      sendResponse({ status: "success", profile: res.arya_profile || DEFAULT_PROFILE });
    });
    return true;
  }

  if (request.action === "UPDATE_PROFILE") {
    chrome.storage.local.set({ arya_profile: request.profile }, () => {
      sendResponse({ status: "success", message: "Candidate profile and QA preferences saved" });
    });
    return true;
  }

  if (request.action === "SET_MODE") {
    chrome.storage.local.get(["arya_profile"], (res) => {
      const p = res.arya_profile || DEFAULT_PROFILE;
      p.application_mode = request.mode; // "COPILOT" or "AUTOPILOT"
      chrome.storage.local.set({ arya_profile: p }, () => {
        sendResponse({ status: "success", mode: p.application_mode });
      });
    });
    return true;
  }

  if (request.action === "RECORD_APPLICATION") {
    chrome.storage.local.get(["arya_extension_apps"], (res) => {
      const apps = res.arya_extension_apps || [];
      const confId = "ATS-EXT-" + Math.floor(10000000 + Math.random() * 90000000);
      const newApp = {
        confirmation_id: confId,
        job_title: request.job_title || "HR Opening",
        company_name: request.company_name || "Target Employer",
        job_url: request.job_url || (sender.tab ? sender.tab.url : ""),
        applied_at: new Date().toISOString(),
        match_score: request.match_score || 95,
        fields_filled: request.fields_filled || 8,
        mode: request.mode || "COPILOT",
        status: request.submitted ? "SUBMITTED" : "REVIEWED_AND_FILLED"
      };

      apps.unshift(newApp);
      chrome.storage.local.set({ arya_extension_apps: apps.slice(0, 50) }, () => {
        // Show green success badge on extension icon
        chrome.action.setBadgeText({ text: "✓" });
        chrome.action.setBadgeBackgroundColor({ color: "#10B981" });
        setTimeout(() => chrome.action.setBadgeText({ text: "" }), 5000);

        sendResponse({ status: "success", confirmation_id: confId, application: newApp });
      });
    });
    return true;
  }

  if (request.action === "GET_APPLICATIONS") {
    chrome.storage.local.get(["arya_extension_apps"], (res) => {
      sendResponse({ status: "success", applications: res.arya_extension_apps || [] });
    });
    return true;
  }

  if (request.action === "SYNC_WITH_WEB_APP") {
    fetch("https://jjayanthkichu20.github.io/autonomous-job-agent/data/profile.json?_t=" + Date.now())
      .then(r => r.json())
      .then(liveProfile => {
        chrome.storage.local.get(["arya_profile"], (stored) => {
          const merged = Object.assign({}, DEFAULT_PROFILE, stored.arya_profile || {}, liveProfile);
          chrome.storage.local.set({ arya_profile: merged }, () => {
            sendResponse({ status: "success", profile: merged });
          });
        });
      })
      .catch(err => {
        sendResponse({ status: "error", message: err.message });
      });
    return true;
  }
});
