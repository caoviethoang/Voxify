/**
 * Studio Text-to-Speech thuần JavaScript (ES6+)
 * Không phụ thuộc thư viện ngoài, tối ưu hiệu năng và độ mượt mà.
 */

(() => {
  "use strict";

  // Biến trạng thái ứng dụng
  const state = {
    appName: "TTS Studio",
    maxTextLength: 20000,
    chunkSize: 2500,
    defaultVoice: "vi-VN-HoaiMyNeural",
    allVoices: [],
    selectedVoiceId: "vi-VN-HoaiMyNeural",
    activeFilter: "vietnamese",
    searchQuery: "",
    rate: 0,
    pitch: 0,
    volume: 0,
    currentAudioBlob: null,
    currentAudioUrl: null,
    history: [],
  };

  // Mẫu văn bản tiếng Việt tự nhiên
  const SAMPLE_TEXT = `Chào mừng bạn đến với phòng thu âm Text-to-Speech chất lượng cao! Hệ thống hỗ trợ xử lý ngữ điệu tự nhiên, mượt mà và tối ưu hóa chuyên sâu cho tiếng Việt. Bạn có thể dễ dàng điều chỉnh tốc độ đọc, cao độ và âm lượng theo ý thích để tạo nên giọng đọc hoàn hảo nhất cho video, sách nói hay tài liệu học tập. Hãy thử nghiệm ngay hôm nay!`;

  // Các phần tử DOM
  const dom = {
    appBrandTitle: document.getElementById("appBrandTitle"),
    footerBrand: document.getElementById("footerBrand"),
    textInput: document.getElementById("textInput"),
    charCount: document.getElementById("charCount"),
    maxCharLimit: document.getElementById("maxCharLimit"),
    chunkInfoText: document.getElementById("chunkInfoText"),
    btnSampleText: document.getElementById("btnSampleText"),
    btnClearText: document.getElementById("btnClearText"),
    
    // Voices
    voiceStatsBadge: document.getElementById("voiceStatsBadge"),
    voiceSearchInput: document.getElementById("voiceSearchInput"),
    voiceTabs: document.querySelectorAll(".tab-btn"),
    voiceList: document.getElementById("voiceList"),
    
    // Sliders
    rateSlider: document.getElementById("rateSlider"),
    rateValLabel: document.getElementById("rateValLabel"),
    pitchSlider: document.getElementById("pitchSlider"),
    pitchValLabel: document.getElementById("pitchValLabel"),
    volumeSlider: document.getElementById("volumeSlider"),
    volumeValLabel: document.getElementById("volumeValLabel"),
    btnResetControls: document.getElementById("btnResetControls"),
    
    // Action buttons
    btnPreview: document.getElementById("btnPreview"),
    btnGenerate: document.getElementById("btnGenerate"),
    
    // Player
    playerCard: document.getElementById("playerCard"),
    playerVoiceLabel: document.getElementById("playerVoiceLabel"),
    audioElement: document.getElementById("audioElement"),
    btnDownload: document.getElementById("btnDownload"),
    
    // History & Toasts
    historyList: document.getElementById("historyList"),
    btnClearHistory: document.getElementById("btnClearHistory"),
    toastContainer: document.getElementById("toastContainer"),
  };

  // =========================================================================
  // Khởi tạo ứng dụng
  // =========================================================================
  async function init() {
    setupEventListeners();
    await loadConfig();
    await loadVoices();
  }

  // =========================================================================
  // Nạp cấu hình từ backend (tránh hardcode thương hiệu)
  // =========================================================================
  async function loadConfig() {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const config = await res.json();
        state.appName = config.app_name || state.appName;
        state.maxTextLength = config.max_text_length || 20000;
        state.chunkSize = config.chunk_size || 2500;
        if (config.default_voice) {
          state.defaultVoice = config.default_voice;
          state.selectedVoiceId = config.default_voice;
        }

        // Cập nhật giao diện theo config
        document.title = `${state.appName} - Trình chuyển đổi Text-to-Speech`;
        if (dom.appBrandTitle) dom.appBrandTitle.textContent = state.appName;
        if (dom.footerBrand) dom.footerBrand.textContent = state.appName;
        if (dom.maxCharLimit) dom.maxCharLimit.textContent = state.maxTextLength.toLocaleString("vi-VN");
        if (dom.textInput) dom.textInput.maxLength = state.maxTextLength;
      }
    } catch (err) {
      console.warn("Không thể tải cấu hình backend, sử dụng mặc định:", err);
    }
  }

  // =========================================================================
  // Nạp danh sách giọng đọc từ /api/voices
  // =========================================================================
  async function loadVoices() {
    try {
      const res = await fetch("/api/voices");
      if (!res.ok) throw new Error("Máy chủ trả về lỗi khi tải giọng đọc.");
      
      const data = await res.json();
      state.allVoices = data.voices || [];

      if (dom.voiceStatsBadge) {
        dom.voiceStatsBadge.textContent = `${data.vietnamese_count || 0} giọng VN / ${data.total || 0} tổng cộng`;
      }

      // Đảm bảo có giọng được chọn
      const defaultExists = state.allVoices.some(v => v.id === state.selectedVoiceId);
      if (!defaultExists && state.allVoices.length > 0) {
        state.selectedVoiceId = state.allVoices[0].id;
      }

      renderVoiceList();
    } catch (err) {
      console.error(err);
      if (dom.voiceList) {
        dom.voiceList.innerHTML = `
          <div class="voice-loading text-danger">
            <span>Không thể tải danh sách giọng đọc. Vui lòng thử tải lại trang.</span>
          </div>`;
      }
      showToast("Không thể tải danh sách giọng đọc. Vui lòng kiểm tra lại mạng.", "error");
    }
  }

  // =========================================================================
  // Hiển thị danh sách giọng đọc theo bộ lọc và tìm kiếm
  // =========================================================================
  function renderVoiceList() {
    if (!dom.voiceList) return;

    const query = state.searchQuery.toLowerCase().trim();
    const filter = state.activeFilter;

    const filtered = state.allVoices.filter(v => {
      // Lọc theo Tab
      if (filter === "vietnamese" && !v.is_vietnamese) return false;
      if (filter === "female" && v.gender.toLowerCase() !== "female") return false;
      if (filter === "male" && v.gender.toLowerCase() !== "male") return false;

      // Tìm kiếm theo từ khóa
      if (query) {
        const matchName = v.name.toLowerCase().includes(query);
        const matchId = v.id.toLowerCase().includes(query);
        const matchLocale = (v.locale_name || "").toLowerCase().includes(query) || (v.locale || "").toLowerCase().includes(query);
        const matchGender = (v.gender === "Female" ? "nữ" : "nam").includes(query);
        return matchName || matchId || matchLocale || matchGender;
      }
      return true;
    });

    if (filtered.length === 0) {
      dom.voiceList.innerHTML = `
        <div class="voice-loading">
          <span>Không tìm thấy giọng đọc phù hợp.</span>
        </div>`;
      return;
    }

    const html = filtered.map(v => {
      const isSelected = v.id === state.selectedVoiceId;
      const isFemale = v.gender.toLowerCase() === "female";
      const avatarClass = isFemale ? "female" : "male";
      const genderText = isFemale ? "Nữ" : "Nam";
      const avatarInitial = isFemale ? "♀" : "♂";

      return `
        <div class="voice-item ${isSelected ? "selected" : ""}" data-id="${v.id}">
          <div class="voice-item-left">
            <div class="voice-avatar ${avatarClass}" title="${genderText}">
              ${avatarInitial}
            </div>
            <div class="voice-meta">
              <span class="voice-name">${escapeHtml(v.name)}</span>
              <span class="voice-sub">${escapeHtml(v.locale_name || v.locale)} • ${genderText}</span>
            </div>
          </div>
          <div class="voice-badges">
            ${v.is_vietnamese ? `<span class="voice-badge voice-badge-vi">Tiếng Việt</span>` : ""}
          </div>
        </div>
      `;
    }).join("");

    dom.voiceList.innerHTML = html;

    // Gắn sự kiện click chọn giọng
    dom.voiceList.querySelectorAll(".voice-item").forEach(item => {
      item.addEventListener("click", () => {
        const voiceId = item.getAttribute("data-id");
        if (voiceId) {
          state.selectedVoiceId = voiceId;
          renderVoiceList();
        }
      });
    });
  }

  // =========================================================================
  // Thiết lập sự kiện người dùng
  // =========================================================================
  function setupEventListeners() {
    // Textarea đếm ký tự & ước lượng phân đoạn
    if (dom.textInput) {
      dom.textInput.addEventListener("input", updateCharacterCount);
    }

    // Văn bản mẫu
    if (dom.btnSampleText) {
      dom.btnSampleText.addEventListener("click", () => {
        dom.textInput.value = SAMPLE_TEXT;
        updateCharacterCount();
        showToast("Đã nạp đoạn văn bản mẫu tiếng Việt.", "info");
      });
    }

    // Xóa văn bản
    if (dom.btnClearText) {
      dom.btnClearText.addEventListener("click", () => {
        dom.textInput.value = "";
        updateCharacterCount();
        dom.textInput.focus();
      });
    }

    // Tìm kiếm giọng
    if (dom.voiceSearchInput) {
      dom.voiceSearchInput.addEventListener("input", (e) => {
        state.searchQuery = e.target.value;
        renderVoiceList();
      });
    }

    // Bộ lọc Tab giọng đọc
    dom.voiceTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        dom.voiceTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        state.activeFilter = tab.getAttribute("data-filter") || "vietnamese";
        renderVoiceList();
      });
    });

    // Thanh trượt Tốc độ (Speed)
    if (dom.rateSlider) {
      dom.rateSlider.addEventListener("input", (e) => {
        state.rate = parseInt(e.target.value, 10);
        const speedMultiplier = (1 + state.rate / 100).toFixed(2);
        const sign = state.rate > 0 ? "+" : "";
        dom.rateValLabel.textContent = `${speedMultiplier}x (${sign}${state.rate}%)`;
      });
    }

    // Thanh trượt Cao độ (Pitch)
    if (dom.pitchSlider) {
      dom.pitchSlider.addEventListener("input", (e) => {
        state.pitch = parseInt(e.target.value, 10);
        const sign = state.pitch > 0 ? "+" : "";
        dom.pitchValLabel.textContent = `${sign}${state.pitch}Hz`;
      });
    }

    // Thanh trượt Âm lượng (Volume)
    if (dom.volumeSlider) {
      dom.volumeSlider.addEventListener("input", (e) => {
        state.volume = parseInt(e.target.value, 10);
        const sign = state.volume > 0 ? "+" : "";
        dom.volumeValLabel.textContent = `${sign}${state.volume}%`;
      });
    }

    // Đặt lại các thanh trượt
    if (dom.btnResetControls) {
      dom.btnResetControls.addEventListener("click", resetSliders);
    }

    // Nút Nghe thử
    if (dom.btnPreview) {
      dom.btnPreview.addEventListener("click", () => handleSynthesize(true));
    }

    // Nút Tạo giọng nói đầy đủ
    if (dom.btnGenerate) {
      dom.btnGenerate.addEventListener("click", () => handleSynthesize(false));
    }

    // Tải xuống MP3
    if (dom.btnDownload) {
      dom.btnDownload.addEventListener("click", downloadCurrentAudio);
    }

    // Xóa toàn bộ lịch sử
    if (dom.btnClearHistory) {
      dom.btnClearHistory.addEventListener("click", clearHistory);
    }
  }

  // =========================================================================
  // Cập nhật bộ đếm ký tự và tính số đoạn
  // =========================================================================
  function updateCharacterCount() {
    const text = dom.textInput ? dom.textInput.value : "";
    const len = text.length;
    
    if (dom.charCount) dom.charCount.textContent = len.toLocaleString("vi-VN");

    const counterWrap = dom.charCount ? dom.charCount.parentElement : null;
    if (counterWrap) {
      counterWrap.classList.remove("warning", "danger");
      if (len > 18000) {
        counterWrap.classList.add(len >= 20000 ? "danger" : "warning");
      }
    }

    // Dự kiến phân đoạn nếu vượt quá chunkSize (2.500 ký tự)
    if (dom.chunkInfoText) {
      if (len === 0) {
        dom.chunkInfoText.textContent = "1 đoạn xử lý trực tiếp";
      } else if (len <= state.chunkSize) {
        dom.chunkInfoText.textContent = `1 đoạn (${len} ký tự)`;
      } else {
        const estimatedChunks = Math.ceil(len / state.chunkSize);
        dom.chunkInfoText.textContent = `Dài: ~${estimatedChunks} đoạn ghép tự động`;
      }
    }
  }

  // =========================================================================
  // Đặt lại các thanh trượt về giá trị chuẩn
  // =========================================================================
  function resetSliders() {
    state.rate = 0;
    state.pitch = 0;
    state.volume = 0;

    if (dom.rateSlider) dom.rateSlider.value = "0";
    if (dom.pitchSlider) dom.pitchSlider.value = "0";
    if (dom.volumeSlider) dom.volumeSlider.value = "0";

    if (dom.rateValLabel) dom.rateValLabel.textContent = "1.0x (0%)";
    if (dom.pitchValLabel) dom.pitchValLabel.textContent = "0Hz";
    if (dom.volumeValLabel) dom.volumeValLabel.textContent = "0%";
  }

  // =========================================================================
  // Xử lý gọi API tổng hợp giọng nói
  // =========================================================================
  async function handleSynthesize(isPreview = false) {
    const rawText = dom.textInput ? dom.textInput.value.trim() : "";

    if (!rawText) {
      showToast("Vui lòng nhập văn bản trước khi tạo giọng nói.", "error");
      dom.textInput.focus();
      return;
    }

    if (!state.selectedVoiceId) {
      showToast("Vui lòng chọn một giọng đọc trong danh sách.", "error");
      return;
    }

    // Kiểm tra giới hạn 20.000 ký tự nếu không phải nghe thử
    if (!isPreview && rawText.length > state.maxTextLength) {
      showToast(`Văn bản vượt quá giới hạn tối đa ${state.maxTextLength.toLocaleString("vi-VN")} ký tự.`, "error");
      return;
    }

    // Định dạng tham số gửi lên API
    const rateParam = `${state.rate >= 0 ? "+" : ""}${state.rate}%`;
    const pitchParam = `${state.pitch >= 0 ? "+" : ""}${state.pitch}Hz`;
    const volumeParam = `${state.volume >= 0 ? "+" : ""}${state.volume}%`;

    const payload = {
      text: rawText,
      voice: state.selectedVoiceId,
      rate: rateParam,
      pitch: pitchParam,
      volume: volumeParam,
      preview: isPreview,
    };

    setLoadingState(true, isPreview);

    try {
      const response = await fetch("/api/tts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errorMsg = "Có lỗi xảy ra khi tạo giọng nói.";
        try {
          const errData = await response.json();
          if (errData && errData.detail) {
            errorMsg = errData.detail;
          }
        } catch (_) {}
        throw new Error(errorMsg);
      }

      const audioBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioBlob);

      // Giải phóng URL cũ nếu có
      if (state.currentAudioUrl) {
        URL.revokeObjectURL(state.currentAudioUrl);
      }

      state.currentAudioBlob = audioBlob;
      state.currentAudioUrl = audioUrl;

      // Cập nhật Audio Player
      displayAudioPlayer(audioUrl, isPreview);

      // Thêm vào Lịch sử phiên làm việc
      addToHistory({
        id: Date.now().toString(),
        text: rawText,
        preview: isPreview,
        voiceId: state.selectedVoiceId,
        rate: rateParam,
        pitch: pitchParam,
        volume: volumeParam,
        blob: audioBlob,
        url: audioUrl,
        timestamp: new Date(),
      });

      showToast(
        isPreview ? "Đã tạo nghe thử 200 ký tự đầu thành công!" : "Đã tạo giọng nói hoàn tất!",
        "success"
      );
    } catch (err) {
      console.error("Lỗi TTS:", err);
      showToast(err.message || "Lỗi kết nối khi tạo giọng nói. Vui lòng thử lại.", "error");
    } finally {
      setLoadingState(false, isPreview);
    }
  }

  // =========================================================================
  // Hiển thị trình phát nhạc & tự động phát
  // =========================================================================
  function displayAudioPlayer(audioUrl, isPreview) {
    if (!dom.playerCard || !dom.audioElement) return;

    dom.playerCard.style.display = "block";
    
    // Tìm tên thân thiện của giọng đang chọn
    const voiceObj = state.allVoices.find(v => v.id === state.selectedVoiceId);
    const voiceName = voiceObj ? `${voiceObj.name} (${voiceObj.id})` : state.selectedVoiceId;

    if (dom.playerVoiceLabel) {
      dom.playerVoiceLabel.textContent = `${voiceName} ${isPreview ? "• [Nghe thử]" : ""}`;
    }

    dom.audioElement.src = audioUrl;
    dom.audioElement.play().catch(e => {
      console.log("Trình duyệt chặn autoplay âm thanh:", e);
    });
  }

  // =========================================================================
  // Tải xuống file MP3 hiện tại
  // =========================================================================
  function downloadCurrentAudio() {
    if (!state.currentAudioBlob && !state.currentAudioUrl) {
      showToast("Chưa có bản ghi âm nào để tải về.", "error");
      return;
    }

    triggerDownload(state.currentAudioUrl, getDownloadFilename());
  }

  function getDownloadFilename(prefix = "speech") {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    return `${prefix}_${state.selectedVoiceId}_${timestamp}.mp3`;
  }

  function triggerDownload(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // =========================================================================
  // Trạng thái Loading của các nút
  // =========================================================================
  function setLoadingState(isLoading, isPreview) {
    if (dom.btnGenerate) {
      dom.btnGenerate.disabled = isLoading;
      const spinner = dom.btnGenerate.querySelector(".btn-spinner");
      const icon = dom.btnGenerate.querySelector(".btn-icon");
      const text = dom.btnGenerate.querySelector(".btn-text-content");

      if (spinner && icon && text) {
        spinner.style.display = isLoading && !isPreview ? "inline-block" : "none";
        icon.style.display = isLoading && !isPreview ? "none" : "inline-block";
        text.textContent = isLoading && !isPreview ? "Đang xử lý..." : "Tạo giọng nói";
      }
    }

    if (dom.btnPreview) {
      dom.btnPreview.disabled = isLoading;
      const text = dom.btnPreview.querySelector("span");
      if (text) {
        text.textContent = isLoading && isPreview ? "Đang nghe thử..." : "Nghe thử (200 ký tự)";
      }
    }
  }

  // =========================================================================
  // Quản lý Lịch sử tạo âm thanh trong phiên
  // =========================================================================
  function addToHistory(item) {
    state.history.unshift(item);
    renderHistory();
  }

  function renderHistory() {
    if (!dom.historyList) return;

    if (dom.btnClearHistory) {
      dom.btnClearHistory.style.display = state.history.length > 0 ? "inline-flex" : "none";
    }

    if (state.history.length === 0) {
      dom.historyList.innerHTML = `
        <div class="history-empty">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path></svg>
          <p>Chưa có bản ghi âm nào. Hãy nhập văn bản và bấm "Tạo giọng nói" hoặc "Nghe thử"!</p>
        </div>`;
      return;
    }

    const html = state.history.map((item, index) => {
      const voiceObj = state.allVoices.find(v => v.id === item.voiceId);
      const voiceName = voiceObj ? voiceObj.name : item.voiceId;
      const snippet = item.text.length > 90 ? item.text.slice(0, 90) + "…" : item.text;
      const timeStr = item.timestamp.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

      return `
        <div class="history-card" data-index="${index}">
          <div class="history-info">
            <div class="history-snippet">"${escapeHtml(snippet)}"</div>
            <div class="history-meta">
              <span class="history-voice-tag">${escapeHtml(voiceName)}</span>
              ${item.preview ? `<span class="badge badge-primary">Nghe thử</span>` : ""}
              <span>Tốc độ: ${item.rate}</span>
              <span>•</span>
              <span>${timeStr}</span>
            </div>
          </div>
          <div class="history-actions">
            <button type="button" class="btn btn-secondary btn-sm btn-replay" data-index="${index}" title="Phát lại đoạn âm thanh này">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Phát
            </button>
            <button type="button" class="btn btn-outline btn-sm btn-history-download" data-index="${index}" title="Tải xuống MP3">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            </button>
          </div>
        </div>
      `;
    }).join("");

    dom.historyList.innerHTML = html;

    // Gắn sự kiện nút phát lại và tải xuống trong lịch sử
    dom.historyList.querySelectorAll(".btn-replay").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        const item = state.history[idx];
        if (item && item.url) {
          state.currentAudioUrl = item.url;
          state.currentAudioBlob = item.blob;
          displayAudioPlayer(item.url, item.preview);
          showToast("Đang phát lại từ lịch sử phiên.", "info");
        }
      });
    });

    dom.historyList.querySelectorAll(".btn-history-download").forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-index"), 10);
        const item = state.history[idx];
        if (item && item.url) {
          triggerDownload(item.url, `speech_${item.voiceId}_${Date.now()}.mp3`);
        }
      });
    });
  }

  function clearHistory() {
    // Thu hồi các Object URL để giải phóng RAM
    state.history.forEach(item => {
      if (item.url && item.url !== state.currentAudioUrl) {
        URL.revokeObjectURL(item.url);
      }
    });
    state.history = [];
    renderHistory();
    showToast("Đã xóa toàn bộ lịch sử trong phiên.", "info");
  }

  // =========================================================================
  // Toast thông báo người dùng
  // =========================================================================
  function showToast(message, type = "info") {
    if (!dom.toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>`;
    } else if (type === "error") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
    }

    toast.innerHTML = `
      ${iconSvg}
      <div class="toast-msg">${escapeHtml(message)}</div>
    `;

    dom.toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.transition = "opacity 0.3s ease, transform 0.3s ease";
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      setTimeout(() => {
        if (toast.parentElement) toast.parentElement.removeChild(toast);
      }, 300);
    }, 4000);
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Khởi chạy khi DOM sẵn sàng
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
