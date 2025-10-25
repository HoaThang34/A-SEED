(function () {
  const $ = (s) => document.querySelector(s);
  
  // =========================
  // DOM References
  // =========================
  const chat = $("#chat");
  const inp = $("#inp");
  const sendBtn = $("#send");
  const intro = $("#intro");
  const startBtn = $("#start");
  
  const newChatBtn = $("#newChatBtn");
  
  const historyBtn = $("#historyBtn");
  const histModal = $("#histModal");
  const histList = $("#histList");
  const histSearch = $("#histSearch");
  const histClose = $("#histClose");
  
  const statsBtn = $("#statsBtn");
  const statsModal = $("#statsModal");
  const statsClose = $("#statsClose");
  const emotionChartCanvas = $("#emotionChart");
  
  const userChip = $("#userChip");
  const dropdownMenu = $("#dropdownMenu");
  const logoutBtn = $("#logoutBtn");

  // =========================
  // Configuration
  // =========================
  const MOOD_CHART_COLORS = {
    joy: "rgba(34, 197, 94, 0.8)",      
    sadness: "rgba(96, 165, 250, 0.8)",  
    anger: "rgba(239, 68, 68, 0.8)",     
    fear: "rgba(20, 184, 166, 0.8)",     
    disgust: "rgba(132, 204, 22, 0.8)",  
    surprise: "rgba(168, 85, 247, 0.8)", 
    neutral: "rgba(148, 163, 184, 0.8)", 
  };

  if (window.marked) {
    marked.setOptions({ breaks: true, gfm: true });
  }

  // =========================
  // State
  // =========================
  let logs = [];
  let typing = null;
  let sessionEmotions = [];
  let currentMood = 'neutral';
  let SID = localStorage.getItem("aseed_sid") || String(Date.now());
  localStorage.setItem("aseed_sid", SID);
  let emotionChartInstance = null;
  
  // =========================
  // Mood & Theme Control
  // =========================
  function setMood(mood) {
    const newMood = mood || 'neutral';
    if (newMood === currentMood) return;
    const body = document.body;
    if (currentMood) {
        body.classList.remove(`mood-${currentMood}`);
    }
    body.classList.add(`mood-${newMood}`);
    currentMood = newMood;
  }

  // =========================
  // Core Chat Functions
  // =========================
  
  function autoscroll() {
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }

  function push(role, text, emotion = null) {
    const group = document.createElement("div");
    group.className = `group ${role} fx-reveal`;
    
    if (role === 'assistant') {
        const avatar = document.createElement("div");
        avatar.className = "ai-avatar";
        avatar.textContent = "🌱";
        group.appendChild(avatar);
    }

    const messageContent = document.createElement("div");
    messageContent.className = "message-content";
    
    const msg = document.createElement("div");
    msg.className = `msg ${role === "user" ? "me" : "ai"}`;
    msg.innerHTML = window.DOMPurify ? DOMPurify.sanitize(marked.parse(text)) : text;
    messageContent.appendChild(msg);

    if (emotion && role === 'assistant') {
        const emotionTag = document.createElement("div");
        emotionTag.className = "emotion-tag";
        emotionTag.textContent = emotion;
        messageContent.appendChild(emotionTag);
    }
    
    group.appendChild(messageContent);
    chat.appendChild(group);
    
    setTimeout(() => group.classList.add('is-visible'), 10);
    autoscroll();
    return messageContent; 
  }

  function typeMessage(text, emotion) {
    hideTyping();
    const messageContent = push('assistant', '', null); 
    const msgElement = messageContent.querySelector('.msg.ai');
    
    let i = 0;
    const typingSpeed = 20; 

    const type = () => {
      if (i < text.length) {
        msgElement.innerHTML = DOMPurify.sanitize(marked.parse(text.substring(0, i + 1) + "▌"));
        i++;
        autoscroll();
        setTimeout(type, typingSpeed);
      } else {
        msgElement.innerHTML = DOMPurify.sanitize(marked.parse(text));
        
        const emotionTag = document.createElement("div");
        emotionTag.className = "emotion-tag fx-reveal is-visible";
        emotionTag.textContent = emotion;
        messageContent.appendChild(emotionTag);
        
        logs.push({ role: 'assistant', text, emotion });
        autoSaveDebounced();
        autoscroll();
      }
    };
    type();
  }

  function showTyping() {
    if (typing) return;
    typing = document.createElement("div");
    typing.className = "group assistant";
    typing.innerHTML = `<div class="ai-avatar">🌱</div><div class="msg ai dots"><i></i><i></i><i></i></div>`;
    chat.appendChild(typing);
    autoscroll();
  }

  function hideTyping() {
    if (typing) {
      typing.remove();
      typing = null;
    }
  }

  async function send() {
    const m = inp.value.trim();
    if (!m) return;
    
    logs.push({ role: 'user', text: m, emotion: null });
    push("user", m, null);
    
    inp.value = "";
    inp.style.height = 'auto'; 
    showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: m, history: logs.slice(-13) }),
      });

      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      
      if (data.error) {
        hideTyping();
        typeMessage(`Error: ${data.error}`, 'sadness');
        return;
      }
      
      const emotion = data.emotion || "neutral";
      sessionEmotions.push(emotion);
      setMood(emotion); 
      typeMessage(data.reply || "...", emotion);

    } catch (e) {
      hideTyping();
      typeMessage("I'm having trouble connecting right now. Please try again in a moment.", 'sadness');
    }
  }

  // =========================
  // UI Event Listeners
  // =========================
  sendBtn.onclick = send;
  inp.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  inp.addEventListener('input', () => {
    inp.style.height = 'auto';
    inp.style.height = (inp.scrollHeight) + 'px';
  });

  newChatBtn.onclick = () => {
    if (confirm("Are you sure you want to start a new chat? The current conversation will be saved.")) {
        logs = [];
        sessionEmotions = [];
        chat.innerHTML = "";
        SID = String(Date.now());
        localStorage.setItem("aseed_sid", SID);
        setMood('neutral');
        typeMessage(window.GREETING, 'neutral');
    }
  };

  userChip.addEventListener('click', () => dropdownMenu.classList.toggle('show'));
  window.addEventListener('click', (e) => {
    if (!userChip.contains(e.target) && !dropdownMenu.contains(e.target)) {
        dropdownMenu.classList.remove('show');
    }
  });
  
  // =========================
  // Session & History
  // =========================
  let saveTimer = null;
  function autoSaveDebounced() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(autoSave, 1000);
  }
  async function autoSave() {
    await fetch("/api/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sid: SID, chat: logs }),
    });
  }
  
  historyBtn.onclick = async () => {
      const res = await fetch("/api/sessions");
      const arr = await res.json();
      renderHist(arr);
      histModal.classList.add("show");
  };
  histClose.onclick = () => histModal.classList.remove("show");

  function renderHist(arr) {
    histList.innerHTML = "";
    const q = (histSearch.value || "").toLowerCase();
    arr.filter(x => (x.title || "").toLowerCase().includes(q)).forEach(it => {
        const row = document.createElement("div");
        row.className = "histitem";
        row.innerHTML = `<div><div class="title">${it.title}</div><div class="meta">${new Date(it.updated * 1000).toLocaleString()}</div></div>`;
        row.onclick = async () => {
            const r = await fetch("/api/load?sid=" + it.sid);
            const data = await r.json();
            if(data.chat) {
                // CORRECT LOGIC: Replace state, then re-render UI from the new state
                logs = data.chat;
                sessionEmotions = data.chat
                    .filter(m => m.role === 'assistant' && m.emotion)
                    .map(m => m.emotion);
                
                chat.innerHTML = ""; // Clear UI
                logs.forEach(m => push(m.role, m.text, m.emotion)); // Re-render from new logs
                
                SID = data.sid;
                localStorage.setItem("aseed_sid", SID);
                
                const lastMood = sessionEmotions.length > 0 ? sessionEmotions[sessionEmotions.length - 1] : 'neutral';
                setMood(lastMood);
                
                histModal.classList.remove("show");
            }
        };
        histList.appendChild(row);
      });
  }
  histSearch.oninput = () => historyBtn.onclick();

  // =========================
  // Mood Statistics
  // =========================
  function renderEmotionChart() {
    const counts = sessionEmotions.reduce((acc, emo) => { acc[emo] = (acc[emo] || 0) + 1; return acc; }, {});
    const labels = Object.keys(counts);
    const data = Object.values(counts);
    const backgroundColors = labels.map(label => MOOD_CHART_COLORS[label] || '#cccccc');
    const isLightTheme = document.documentElement.classList.contains('light');
    const textColor = isLightTheme ? '#334155' : '#e2e8f0';

    if (emotionChartInstance) emotionChartInstance.destroy();

    emotionChartInstance = new Chart(emotionChartCanvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderColor: isLightTheme ? '#ffffff' : '#1e293b',
                borderWidth: 5,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: textColor, font: { size: 14, family: 'Inter' }, padding: 20 }
                }
            },
            layout: { padding: 20 }
        }
    });
  }

  statsBtn.onclick = () => { renderEmotionChart(); statsModal.classList.add("show"); };
  statsClose.onclick = () => statsModal.classList.remove("show");

  // =========================
  // Initial Load & Auth
  // =========================
  startBtn.onclick = () => {
    intro.classList.remove("show");
    typeMessage(window.GREETING, 'neutral');
  };
  
  logoutBtn.onclick = async () => { 
    await fetch('/api/logout', { method: 'POST' }); 
    window.location.href = '/login'; 
  };

  fetch('/api/session-check').then(r => r.json()).then(data => { if(!data.logged_in) window.location.href = '/login'; });
    
  setMood('neutral'); 
})();