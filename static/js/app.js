let currentVideoId = null;
let currentTaskId = null;
let pollInterval = null;

// DOM Elements
const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const keyDot = document.getElementById('keyDot');

const dropZone = document.getElementById('dropZone');
const videoFileInput = document.getElementById('videoFileInput');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const generateBtn = document.getElementById('generateBtn');

const tabUpload = document.getElementById('tabUpload');
const tabYoutube = document.getElementById('tabYoutube');
const fileUploadContainer = document.getElementById('fileUploadContainer');
const youtubeContainer = document.getElementById('youtubeContainer');
const youtubeUrlInput = document.getElementById('youtubeUrlInput');
const fetchYtBtn = document.getElementById('fetchYtBtn');
const ytStatusDisplay = document.getElementById('ytStatusDisplay');

const progressSection = document.getElementById('progressSection');
const progressBar = document.getElementById('progressBar');
const progressPct = document.getElementById('progressPct');
const statusMessage = document.getElementById('statusMessage');

const resultsSection = document.getElementById('resultsSection');
const resultsSummary = document.getElementById('resultsSummary');
const clipsGrid = document.getElementById('clipsGrid');
const downloadAllZipBtn = document.getElementById('downloadAllZipBtn');

// Modals
const videoModal = document.getElementById('videoModal');
const closeVideoModal = document.getElementById('closeVideoModal');
const modalVideoPlayer = document.getElementById('modalVideoPlayer');
const modalVideoTitle = document.getElementById('modalVideoTitle');
const modalViralityBadge = document.getElementById('modalViralityBadge');
const modalQualityBadge = document.getElementById('modalQualityBadge');
const modalDownloadLink = document.getElementById('modalDownloadLink');

const cookiesModal = document.getElementById('cookiesModal');
const openCookiesBtn = document.getElementById('openCookiesBtn');
const closeCookiesModal = document.getElementById('closeCookiesModal');
const cookieDot = document.getElementById('cookieDot');
const cookieStatusText = document.getElementById('cookieStatusText');
const cookieSizeRow = document.getElementById('cookieSizeRow');
const cookieSizeText = document.getElementById('cookieSizeText');
const cookieDropZone = document.getElementById('cookieDropZone');
const cookieFileInput = document.getElementById('cookieFileInput');
const deleteCookiesBtn = document.getElementById('deleteCookiesBtn');

const cleanCacheBtn = document.getElementById('cleanCacheBtn');

// Toast Notification System
function showToast(msg, type = 'success') {
  const container = document.getElementById('toastContainer');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
  toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(15px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 350);
  }, 3500);
}

// Tabs
const tabLiveStudio = document.getElementById('tabLiveStudio');
const liveStudioContainer = document.getElementById('liveStudioContainer');

function activateTab(activeBtn, showContainer) {
  [tabUpload, tabYoutube, tabLiveStudio].forEach(btn => btn?.classList.remove('active'));
  [fileUploadContainer, youtubeContainer, liveStudioContainer].forEach(c => {
    if (c) c.style.display = 'none';
  });
  activeBtn.classList.add('active');
  showContainer.style.display = 'block';
}

tabUpload.addEventListener('click', () => activateTab(tabUpload, fileUploadContainer));
tabYoutube.addEventListener('click', () => activateTab(tabYoutube, youtubeContainer));
if (tabLiveStudio && liveStudioContainer) {
  tabLiveStudio.addEventListener('click', () => activateTab(tabLiveStudio, liveStudioContainer));
}

// Live Stream Studio Controls
const liveStreamUrlInput = document.getElementById('liveStreamUrlInput');
const detectLiveBtn = document.getElementById('detectLiveBtn');
const liveStreamCard = document.getElementById('liveStreamCard');
const liveStreamerThumb = document.getElementById('liveStreamerThumb');
const liveTagPill = document.getElementById('liveTagPill');
const liveChannelName = document.getElementById('liveChannelName');
const liveStreamTitle = document.getElementById('liveStreamTitle');
const liveCategoryBadge = document.getElementById('liveCategoryBadge');
const liveViewersBadge = document.getElementById('liveViewersBadge');
const captureLiveBtn = document.getElementById('captureLiveBtn');
const liveCaptureStatus = document.getElementById('liveCaptureStatus');
const livePillBtns = document.querySelectorAll('.live-pill-btn');

let selectedLiveDuration = 60;
livePillBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    livePillBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedLiveDuration = parseInt(btn.dataset.dur, 10) || 60;
  });
});

if (detectLiveBtn) {
  detectLiveBtn.addEventListener('click', async () => {
    const url = liveStreamUrlInput.value.trim();
    if (!url) {
      showToast('Please enter a Twitch, Kick, or YouTube Live stream URL', 'info');
      return;
    }
    detectLiveBtn.disabled = true;
    detectLiveBtn.textContent = '⏳ Checking...';
    try {
      const res = await fetch('/api/live/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });
      const data = await res.json();
      if (data.is_live) {
        liveStreamCard.style.display = 'flex';
        liveChannelName.textContent = data.uploader || 'Live Streamer';
        liveStreamTitle.textContent = data.title || 'Ongoing Live Broadcast';
        liveCategoryBadge.textContent = `🎮 ${data.category || 'Live'}`;
        const viewers = data.viewers ? (data.viewers > 999 ? (data.viewers / 1000).toFixed(1) + 'k' : data.viewers) : 'Live';
        liveViewersBadge.textContent = `👥 ${viewers} Viewers`;
        if (data.thumbnail) {
          liveStreamerThumb.src = data.thumbnail;
        } else {
          liveStreamerThumb.src = 'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=300&h=160&fit=crop';
        }
        captureLiveBtn.disabled = false;
        showToast(`Streamer is 🔴 LIVE: ${data.uploader}`);
        
        // Auto-select Streamer Split layout for gaming streams!
        const reframeModeSelect = document.getElementById('reframeMode');
        if (reframeModeSelect) {
          reframeModeSelect.value = 'split_gaming';
        }
      } else {
        liveStreamCard.style.display = 'none';
        captureLiveBtn.disabled = true;
        showToast(data.error ? `Stream check: ${data.error}` : 'Streamer is currently OFFLINE', 'error');
      }
    } catch (err) {
      showToast(`Error checking stream: ${err.message}`, 'error');
    } finally {
      detectLiveBtn.disabled = false;
      detectLiveBtn.textContent = '🔍 Check Stream';
    }
  });
}

if (captureLiveBtn) {
  captureLiveBtn.addEventListener('click', async () => {
    const url = liveStreamUrlInput.value.trim();
    if (!url) return;
    captureLiveBtn.disabled = true;
    liveCaptureStatus.textContent = `🔴 Capturing ${selectedLiveDuration}s live broadcast snippet...`;
    showToast(`Capturing live ${selectedLiveDuration}s snippet...`);
    try {
      const res = await fetch('/api/fetch_url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, live_duration: selectedLiveDuration })
      });
      const data = await res.json();
      if (data.video_id) {
        currentVideoId = data.video_id;
        liveCaptureStatus.textContent = `✅ Ready: [LIVE] ${data.title} (${Math.round(data.duration || 0)}s)`;
        generateBtn.disabled = false;
        showToast('Live snippet captured! Click Generate Viral Clips.');
      } else {
        liveCaptureStatus.textContent = `Failed: ${data.error || 'Could not capture stream'}`;
        showToast(`Capture failed: ${data.error}`, 'error');
      }
    } catch (err) {
      liveCaptureStatus.textContent = `Error: ${err.message}`;
      showToast(`Capture error: ${err.message}`, 'error');
    } finally {
      captureLiveBtn.disabled = false;
    }
  });
}

// Init: check API key status & cookies status
fetch('/api/config')
  .then(res => res.json())
  .then(data => {
    if (data.has_key) {
      keyDot.classList.add('active');
      apiKeyInput.placeholder = `AI Studio Key (${data.masked_key}) ✓`;
    }
  });

function loadCookieStatus() {
  fetch('/api/cookies')
    .then(res => res.json())
    .then(data => {
      if (data.has_cookies) {
        if (cookieDot) cookieDot.classList.add('active');
        if (cookieStatusText) {
          cookieStatusText.textContent = '🟢 Connected & Active';
          cookieStatusText.style.color = '#10b981';
        }
        if (cookieSizeRow) cookieSizeRow.style.display = 'flex';
        if (cookieSizeText) cookieSizeText.textContent = `${data.size_kb} KB`;
        if (deleteCookiesBtn) deleteCookiesBtn.style.display = 'inline-block';
      } else {
        if (cookieDot) cookieDot.classList.remove('active');
        if (cookieStatusText) {
          cookieStatusText.textContent = '⚪ Not Connected';
          cookieStatusText.style.color = '#94a3b8';
        }
        if (cookieSizeRow) cookieSizeRow.style.display = 'none';
        if (deleteCookiesBtn) deleteCookiesBtn.style.display = 'none';
      }
    })
    .catch(() => {});
}
loadCookieStatus();

// Cookies Modal Listeners
if (openCookiesBtn && cookiesModal) {
  openCookiesBtn.addEventListener('click', () => {
    cookiesModal.style.display = 'flex';
    loadCookieStatus();
  });
}

if (closeCookiesModal && cookiesModal) {
  closeCookiesModal.addEventListener('click', () => {
    cookiesModal.style.display = 'none';
  });
}

if (cookiesModal) {
  cookiesModal.addEventListener('click', (e) => {
    if (e.target === cookiesModal) cookiesModal.style.display = 'none';
  });
}

if (cookieDropZone && cookieFileInput) {
  cookieDropZone.addEventListener('click', () => cookieFileInput.click());

  cookieFileInput.addEventListener('change', () => {
    if (cookieFileInput.files.length) {
      uploadCookieFile(cookieFileInput.files[0]);
    }
  });

  ['dragenter', 'dragover'].forEach(evt => {
    cookieDropZone.addEventListener(evt, e => {
      e.preventDefault();
      cookieDropZone.style.borderColor = '#6366f1';
    });
  });

  ['dragleave', 'drop'].forEach(evt => {
    cookieDropZone.addEventListener(evt, e => {
      e.preventDefault();
      cookieDropZone.style.borderColor = '';
    });
  });

  cookieDropZone.addEventListener('drop', e => {
    if (e.dataTransfer.files.length) {
      uploadCookieFile(e.dataTransfer.files[0]);
    }
  });
}

async function uploadCookieFile(file) {
  const formData = new FormData();
  formData.append('cookies', file);
  try {
    const res = await fetch('/api/cookies', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.status === 'saved') {
      showToast('YouTube cookies uploaded successfully!');
      loadCookieStatus();
    } else {
      showToast(data.error || 'Failed to upload cookies', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

if (deleteCookiesBtn) {
  deleteCookiesBtn.addEventListener('click', async () => {
    if (!confirm('Remove YouTube cookies file?')) return;
    try {
      await fetch('/api/cookies', { method: 'DELETE' });
      showToast('YouTube cookies removed');
      loadCookieStatus();
    } catch (err) {
      showToast(`Error: ${err.message}`, 'error');
    }
  });
}

// Clean Cache Button
if (cleanCacheBtn) {
  cleanCacheBtn.addEventListener('click', async () => {
    cleanCacheBtn.disabled = true;
    cleanCacheBtn.textContent = '🧹 Cleaning...';
    try {
      const res = await fetch('/api/clean_cache', { method: 'POST' });
      const data = await res.json();
      showToast(`Cleaned ${data.files_removed} temp files (${data.freed_mb} MB freed)!`);
    } catch (err) {
      showToast(`Error cleaning cache: ${err.message}`, 'error');
    } finally {
      cleanCacheBtn.disabled = false;
      cleanCacheBtn.textContent = '🧹 Clean Cache';
    }
  });
}

// Video Player Modal Listeners
if (closeVideoModal && videoModal) {
  closeVideoModal.addEventListener('click', () => {
    videoModal.style.display = 'none';
    if (modalVideoPlayer) {
      modalVideoPlayer.pause();
      modalVideoPlayer.src = '';
    }
  });
}

if (videoModal) {
  videoModal.addEventListener('click', (e) => {
    if (e.target === videoModal) {
      videoModal.style.display = 'none';
      if (modalVideoPlayer) {
        modalVideoPlayer.pause();
        modalVideoPlayer.src = '';
      }
    }
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (videoModal && videoModal.style.display === 'flex') {
      videoModal.style.display = 'none';
      if (modalVideoPlayer) {
        modalVideoPlayer.pause();
        modalVideoPlayer.src = '';
      }
    }
    if (cookiesModal && cookiesModal.style.display === 'flex') {
      cookiesModal.style.display = 'none';
    }
  }
});

// Live Subtitle Interactive Previewer
const subtitlePresetSelect = document.getElementById('subtitlePreset');
const subtitlePreviewStage = document.getElementById('subtitlePreviewStage');
const previewHookBanner = document.getElementById('previewHookBanner');
const showHookHeaderCheckbox = document.getElementById('showHookHeader');

function updateSubtitlePreviewTheme() {
  if (!subtitlePresetSelect || !subtitlePreviewStage) return;
  const val = subtitlePresetSelect.value || 'hormozi';
  subtitlePreviewStage.className = `subtitle-preview-stage theme-${val}`;
}

if (subtitlePresetSelect) {
  subtitlePresetSelect.addEventListener('change', updateSubtitlePreviewTheme);
  updateSubtitlePreviewTheme();
}

if (showHookHeaderCheckbox && previewHookBanner) {
  showHookHeaderCheckbox.addEventListener('change', () => {
    previewHookBanner.style.display = showHookHeaderCheckbox.checked ? 'block' : 'none';
  });
}

// Animated word bounce in preview stage
let activeWordIdx = 0;
const previewWords = ['pw1', 'pw2', 'pw3', 'pw4', 'pw5'];
setInterval(() => {
  previewWords.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (i === activeWordIdx) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
  activeWordIdx = (activeWordIdx + 1) % previewWords.length;
}, 900);

// Fetch Video from Link (YouTube / Twitch / etc.)
fetchYtBtn.addEventListener('click', async () => {
  const url = youtubeUrlInput.value.trim();
  if (!url) {
    ytStatusDisplay.textContent = 'Please enter a valid video URL (YouTube, Twitch, etc.)';
    return;
  }

  const liveDuration = document.getElementById('liveDuration')?.value || 180;

  fetchYtBtn.disabled = true;
  ytStatusDisplay.textContent = '⚡ Connecting & resolving high-speed stream...';

  try {
    const res = await fetch('/api/fetch_url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, live_duration: liveDuration })
    });
    const data = await res.json();
    
    if (data.task_id) {
      // Poll high-speed download progress
      const pollDl = setInterval(async () => {
        try {
          const sRes = await fetch(`/api/download_status/${data.task_id}`);
          const sData = await sRes.json();
          if (sData.status === 'downloading') {
            ytStatusDisplay.textContent = `⚡ ${sData.message || 'Downloading video...'}`;
          } else if (sData.status === 'completed') {
            clearInterval(pollDl);
            fetchYtBtn.disabled = false;
            const resData = sData.result || {};
            currentVideoId = resData.video_id;
            const platformTag = resData.platform ? `[${resData.platform}] ` : '';
            ytStatusDisplay.textContent = `Ready: ${platformTag}${resData.title} (${Math.round(resData.duration || 0)}s)`;
            generateBtn.disabled = false;
            showToast(`Fetched: ${resData.title}`);
          } else if (sData.status === 'failed') {
            clearInterval(pollDl);
            fetchYtBtn.disabled = false;
            ytStatusDisplay.textContent = `Failed: ${sData.error || 'Download failed'}`;
            showToast(sData.error || 'Failed to fetch video', 'error');
          }
        } catch (pollErr) {
          clearInterval(pollDl);
          fetchYtBtn.disabled = false;
          ytStatusDisplay.textContent = `Error: ${pollErr.message}`;
        }
      }, 500);
    } else if (data.video_id) {
      currentVideoId = data.video_id;
      const platformTag = data.platform ? `[${data.platform}] ` : '';
      ytStatusDisplay.textContent = `Ready: ${platformTag}${data.title} (${Math.round(data.duration || 0)}s)`;
      generateBtn.disabled = false;
      fetchYtBtn.disabled = false;
      showToast(`Fetched: ${data.title}`);
    } else {
      ytStatusDisplay.textContent = `Failed: ${data.error || 'Could not download video'}`;
      showToast(data.error || 'Failed to fetch video', 'error');
      fetchYtBtn.disabled = false;
    }
  } catch (err) {
    ytStatusDisplay.textContent = `Error: ${err.message}`;
    showToast(`Error: ${err.message}`, 'error');
    fetchYtBtn.disabled = false;
  }
});

// Save API Key
saveKeyBtn.addEventListener('click', async () => {
  const key = apiKeyInput.value.trim();
  if (!key) return;

  if (key.startsWith('http://') || key.startsWith('https://') || key.includes('youtu') || key.includes('twitch')) {
    alert('⚠️ That looks like a video link, not an API key!\n\nWe have automatically moved it to the Video URL tab for you.');
    tabYoutube.click();
    youtubeUrlInput.value = key;
    apiKeyInput.value = '';
    apiKeyInput.placeholder = 'Enter Google AI Studio Key...';
    return;
  }

  const res = await fetch('/api/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: key })
  });
  const data = await res.json();
  if (data.has_key) {
    keyDot.classList.add('active');
    apiKeyInput.value = '';
    apiKeyInput.placeholder = `AI Studio Key (${data.masked_key}) ✓`;
    showToast('Google AI Studio Key saved securely!');
  }
});

// Drag and drop events
dropZone.addEventListener('click', () => videoFileInput.click());

['dragenter', 'dragover'].forEach(eventName => {
  dropZone.addEventListener(eventName, e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
});

['dragleave', 'drop'].forEach(eventName => {
  dropZone.addEventListener(eventName, e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  });
});

dropZone.addEventListener('drop', e => {
  if (e.dataTransfer.files.length) {
    handleFileUpload(e.dataTransfer.files[0]);
  }
});

videoFileInput.addEventListener('change', () => {
  if (videoFileInput.files.length) {
    handleFileUpload(videoFileInput.files[0]);
  }
});

async function handleFileUpload(file) {
  fileNameDisplay.textContent = `Uploading: ${file.name}...`;
  const formData = new FormData();
  formData.append('video', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (data.video_id) {
      currentVideoId = data.video_id;
      fileNameDisplay.textContent = `Ready: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
      generateBtn.disabled = false;
      showToast(`Uploaded: ${file.name}`);
    } else {
      fileNameDisplay.textContent = `Upload failed: ${data.error || 'Unknown error'}`;
      showToast(`Upload failed: ${data.error}`, 'error');
    }
  } catch (err) {
    fileNameDisplay.textContent = `Upload error: ${err.message}`;
    showToast(`Upload error: ${err.message}`, 'error');
  }
}

// Generate Shorts
generateBtn.addEventListener('click', async () => {
  if (!currentVideoId) return;

  generateBtn.disabled = true;
  progressSection.style.display = 'block';
  resultsSection.style.display = 'none';
  clipsGrid.innerHTML = '';

  const reframeMode = document.getElementById('reframeMode').value;
  const aspectRatio = document.getElementById('aspectRatio')?.value || '9:16';
  const dubLanguage = document.getElementById('dubLanguage')?.value || 'none';
  const subtitlePreset = document.getElementById('subtitlePreset').value;
  const lengthPref = document.getElementById('lengthPref').value;
  const clipCount = document.getElementById('clipCount').value;
  const captionLanguage = document.getElementById('captionLanguage')?.value || 'auto';
  const videoQuality = document.getElementById('videoQuality')?.value || '1080p';
  const showHookHeader = document.getElementById('showHookHeader')?.checked ?? true;
  const enableEmojis = document.getElementById('enableEmojis')?.checked ?? true;
  const enableDynamicZoom = document.getElementById('enableDynamicZoom')?.checked ?? true;
  const enableProgressBar = document.getElementById('enableProgressBar')?.checked ?? true;
  const enableColorPop = document.getElementById('enableColorPop')?.checked ?? true;
  const enableAudioBoost = document.getElementById('enableAudioBoost')?.checked ?? true;
  const enableHookSfx = document.getElementById('enableHookSfx')?.checked ?? true;
  const enableSeamlessLoop = document.getElementById('enableSeamlessLoop')?.checked ?? true;

  try {
    const res = await fetch('/api/process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: currentVideoId,
        reframe_mode: reframeMode,
        aspect_ratio: aspectRatio,
        dub_language: dubLanguage,
        subtitle_preset: subtitlePreset,
        enable_emojis: enableEmojis,
        length_pref: lengthPref,
        clip_count: clipCount,
        caption_language: captionLanguage,
        video_quality: videoQuality,
        show_hook_header: showHookHeader,
        enable_dynamic_zoom: enableDynamicZoom,
        enable_progress_bar: enableProgressBar,
        enable_color_pop: enableColorPop,
        enable_audio_boost: enableAudioBoost,
        enable_hook_sfx: enableHookSfx,
        enable_seamless_loop: enableSeamlessLoop
      })
    });
    const data = await res.json();
    if (data.task_id) {
      currentTaskId = data.task_id;
      pollTask(data.task_id);
    } else {
      alert(`Error starting pipeline: ${data.error || 'Unknown'}`);
      generateBtn.disabled = false;
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
    generateBtn.disabled = false;
  }
});

function pollTask(taskId) {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${taskId}`);
      const task = await res.json();

      progressBar.style.width = `${task.progress}%`;
      progressPct.textContent = `${task.progress}%`;
      statusMessage.textContent = task.message;

      if (task.status === 'completed') {
        clearInterval(pollInterval);
        progressSection.style.display = 'none';
        generateBtn.disabled = false;
        currentTaskId = taskId;
        renderResults(task.result);
        showToast('All viral shorts rendered successfully!');
      } else if (task.status === 'failed') {
        clearInterval(pollInterval);
        progressSection.style.display = 'none';
        generateBtn.disabled = false;
        alert(`Generation failed: ${task.error}`);
        showToast(`Generation failed: ${task.error}`, 'error');
      }
    } catch (err) {
      console.error('Polling error', err);
    }
  }, 1000);
}

// Download All (.ZIP) Listener
if (downloadAllZipBtn) {
  downloadAllZipBtn.addEventListener('click', () => {
    if (!currentTaskId) {
      showToast('No active batch to download', 'info');
      return;
    }
    showToast('Preparing your .ZIP archive with clips & post copy...');
    window.location.href = `/api/download_all/${currentTaskId}`;
  });
}

function renderResults(result) {
  resultsSummary.textContent = result.summary || 'Generated short-form vertical clips:';
  resultsSection.style.display = 'block';

  clipsGrid.innerHTML = '';
  result.clips.forEach(clip => {
    const card = document.createElement('div');
    card.className = 'clip-card';

    const ytText = clip.social_copy?.youtube || `${clip.title} #Shorts`;
    const ttText = clip.social_copy?.tiktok || `${clip.hook_headline || clip.title} #fyp`;
    const igText = clip.social_copy?.instagram || `${clip.title} #reels`;

    let badgeClass = 'viral-blue';
    let badgeText = `⚡ ${clip.virality_score}/100`;
    if (clip.virality_score >= 95) {
      badgeClass = 'viral-gold';
      badgeText = `🔥 ${clip.virality_score}/100`;
    } else if (clip.virality_score >= 90) {
      badgeClass = 'viral-green';
      badgeText = `🚀 ${clip.virality_score}/100`;
    }

    card.innerHTML = `
      <div class="video-container">
        <video controls playsinline preload="metadata">
          <source src="${clip.preview_url}" type="video/mp4">
          Your browser does not support the video tag.
        </video>
      </div>
      <div class="clip-info">
        <div class="clip-header">
          <div class="clip-title">${clip.title}</div>
          <div class="viral-badge ${badgeClass}">${badgeText}</div>
        </div>

        ${clip.hook_type ? `<div class="hook-type-pill">${clip.hook_type}</div>` : ''}

        <div class="clip-scores">
          <span class="score-chip">Hook: <strong>${clip.hook_score}%</strong></span>
          <span class="score-chip">Flow: <strong>${clip.flow_score}%</strong></span>
          <span class="score-chip">Engagement: <strong>${clip.engagement_score || 95}%</strong></span>
          <span class="score-chip">Curiosity: <strong>${clip.curiosity_gap || '9.6/10'}</strong></span>
          <span class="score-chip risk-${(clip.drop_off_risk || 'low').toLowerCase().replace(/\s+/g, '-')}">Drop-off: <strong>${clip.drop_off_risk || 'Very Low'}</strong></span>
          <span class="score-chip">⏱ <strong>${clip.duration}s</strong></span>
          <span class="score-chip">📺 <strong>${clip.quality || '1080p'}</strong></span>
          <span class="score-chip">📐 <strong>${clip.aspect_ratio || '9:16'}</strong></span>
          ${clip.dub_language && clip.dub_language !== 'none' ? `<span class="score-chip" style="background: rgba(234, 179, 8, 0.2); border-color: #eab308; color: #fef08a;">🎙️ <strong>${clip.dub_label || clip.dub_language.toUpperCase()}</strong></span>` : ''}
        </div>

        ${clip.hook_headline ? `
          <div class="hook-headline-preview">
            <span class="hook-badge-tag">TOP HOOK BANNER</span>
            <span>🔥 ${clip.hook_headline} 🔥</span>
          </div>
        ` : ''}

        ${clip.hook ? `<div class="clip-hook">"${clip.hook}"</div>` : ''}

        <!-- AI Virality & Algorithm Growth Insights -->
        <details class="virality-details">
          <summary>🧠 AI Virality & Algorithm Growth Insights</summary>
          <div class="virality-details-content">
            <p><strong>Retention Psychology:</strong> ${clip.reason || 'High emotional resonance and pattern interrupt.'}</p>
            ${clip.viral_action_tip ? `<p class="viral-tip"><strong>🚀 Growth Hack:</strong> ${clip.viral_action_tip}</p>` : ''}
          </div>
        </details>

        <!-- Opus Social Copy Box -->
        <div class="social-section">
          <div class="social-tabs">
            <button class="social-tab active" data-platform="yt">YouTube</button>
            <button class="social-tab" data-platform="tt">TikTok</button>
            <button class="social-tab" data-platform="ig">Instagram</button>
          </div>
          <div class="social-content-row">
            <span class="social-text">${ytText}</span>
            <button class="btn-copy">Copy</button>
          </div>
        </div>

        <div class="card-action-buttons" style="display: flex; gap: 8px; margin-top: 10px;">
          <button type="button" class="btn-preview-modal btn-sm" style="flex: 1; padding: 10px 12px; background: #1e293b; border: 1px solid #475569; color: #f8fafc; border-radius: 8px; cursor: pointer; font-weight: 700;">
            ▶️ Fullscreen Preview
          </button>
          <a href="${clip.download_url}" class="btn-download" style="flex: 1;" download>
            ⬇️ Download Short
          </a>
        </div>
      </div>
    `;

    // Hook up fullscreen preview modal
    const previewBtn = card.querySelector('.btn-preview-modal');
    if (previewBtn && videoModal && modalVideoPlayer) {
      previewBtn.addEventListener('click', () => {
        modalVideoPlayer.src = clip.preview_url;
        modalVideoTitle.textContent = clip.title;
        modalViralityBadge.textContent = `Virality: ${clip.virality_score}/100`;
        modalQualityBadge.textContent = clip.quality || '1080p';
        modalDownloadLink.href = clip.download_url;
        modalDownloadLink.setAttribute('download', clip.video_file || 'short.mp4');
        videoModal.style.display = 'flex';
        modalVideoPlayer.play().catch(() => {});
      });
    }

    // Hook up social tab switcher for this card
    const textEl = card.querySelector('.social-text');
    const copyBtn = card.querySelector('.btn-copy');
    const tabBtns = card.querySelectorAll('.social-tab');

    const socialTexts = { yt: ytText, tt: ttText, ig: igText };
    let currentPlatform = 'yt';

    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentPlatform = btn.dataset.platform;
        textEl.textContent = socialTexts[currentPlatform];
      });
    });

    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(textEl.textContent).then(() => {
        copyBtn.textContent = 'Copied!';
        showToast('Social post copy copied to clipboard!');
        setTimeout(() => copyBtn.textContent = 'Copy', 1500);
      });
    });

    clipsGrid.appendChild(card);
  });
}
