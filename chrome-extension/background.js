/**
 * Arya AI Job Hunter — Background Service Worker (Manifest V3)
 * Manages candidate profile synchronization, context menus, and application recording.
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
  auto_pilot_enabled: true
};

chrome.runtime.onInstalled.addListener(() => {
  // Initialize storage with candidate master profile if not already set
  chrome.storage.local.get(["arya_profile", "arya_extension_apps"], (result) => {
    if (!result.arya_profile) {
      chrome.storage.local.set({ arya_profile: DEFAULT_PROFILE });
    }
    if (!result.arya_extension_apps) {
      chrome.storage.local.set({ arya_extension_apps: [] });
    }
  });

  // Context menus for quick actions on any webpage
  chrome.contextMenus.create({
    id: "arya_autofill",
    title: "⚡ Auto-Fill Application Form with Arya",
    contexts: ["page", "editable"]
  });

  chrome.contextMenus.create({
    id: "arya_score_jd",
    title: "📊 Evaluate ATS Match with Jayanth's CV",
    contexts: ["selection"]
  });

  console.log("Arya AI Job Hunter Extension installed successfully!");
});

// Handle Context Menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab || !tab.id) return;

  if (info.menuItemId === "arya_autofill") {
    chrome.tabs.sendMessage(tab.id, { action: "TRIGGER_AUTOFILL" });
  } else if (info.menuItemId === "arya_score_jd") {
    chrome.tabs.sendMessage(tab.id, {
      action: "EVALUATE_SELECTED_TEXT",
      selectedText: info.selectionText
    });
  }
});

// Message listener for popup & content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "GET_PROFILE") {
    chrome.storage.local.get(["arya_profile"], (res) => {
      sendResponse({ status: "success", profile: res.arya_profile || DEFAULT_PROFILE });
    });
    return true; // Keep channel open for async response
  }

  if (request.action === "UPDATE_PROFILE") {
    chrome.storage.local.set({ arya_profile: request.profile }, () => {
      sendResponse({ status: "success", message: "Candidate profile updated" });
    });
    return true;
  }

  if (request.action === "RECORD_APPLICATION") {
    chrome.storage.local.get(["arya_extension_apps"], (res) => {
      const apps = res.arya_extension_apps || [];
      const confId = "ATS-EXT-" + Math.floor(10000000 + Math.random() * 90000000);
      const newApp = {
        confirmation_id: confId,
        job_title: request.job_title || "HR Position",
        company_name: request.company_name || "Target Employer",
        job_url: request.job_url || (sender.tab ? sender.tab.url : ""),
        applied_at: new Date().toISOString(),
        match_score: request.match_score || 95,
        status: "SUBMITTED"
      };

      // Add to front
      apps.unshift(newApp);
      chrome.storage.local.set({ arya_extension_apps: apps.slice(0, 50) }, () => {
        // Set badge on extension icon
        chrome.action.setBadgeText({ text: "✓" });
        chrome.action.setBadgeBackgroundColor({ color: "#10B981" });
        setTimeout(() => chrome.action.setBadgeText({ text: "" }), 4000);

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
