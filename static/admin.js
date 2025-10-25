(function () {
    const $ = s => document.querySelector(s);

    const setText = (id, text) => {
        const el = $(`#${id}`);
        if (el) el.textContent = text;
    };
    
    const setBar = (id, percent) => {
        const el = $(`#${id}`);
        if (el) el.style.width = `${percent}%`;
    };

    const fmtBytes = (bytes) => {
        if (bytes === 0) return '0 B';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${parseFloat((bytes / Math.pow(1024, i)).toFixed(2))} ${['B', 'KB', 'MB', 'GB', 'TB'][i]}`;
    };

    async function pollStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) {
                if (res.status === 401) window.location.href = '/admin';
                return;
            }
            const data = await res.json();

            // System Status
            const uptime = data.uptime_sec;
            const hours = Math.floor(uptime / 3600);
            const minutes = Math.floor((uptime % 3600) / 60);
            const seconds = uptime % 60;
            setText('uptime', `${hours}h ${minutes}m ${seconds}s`);
            setText('python', data.python_version);
            setText('pid', data.process.pid);
            setText('rss', fmtBytes(data.process.rss_bytes));

            // Resource Usage
            setText('cpuPercent', `${data.cpu.percent.toFixed(1)}%`);
            setBar('cpuBar', data.cpu.percent);
            setText('ramPercent', `${data.memory.percent.toFixed(1)}%`);
            setBar('ramBar', data.memory.percent);

            // Ollama
            setText('ollamaStatus', data.ollama.ok ? '🟢 Online' : '🔴 Offline');
            setText('ollamaHost', data.ollama.host);
            setText('ollamaModel', data.ollama.model_name);
            setText('ollamaModels', data.ollama.models_count);

            // GPU
            if (data.gpus && data.gpus.length > 0) {
                $('#gpuCard').style.display = 'block';
                const gpuHtml = data.gpus.map(gpu => `
                    <div class="kv-grid" style="margin-top: 10px;">
                        <div class="key">Name</div><div class="val">${gpu.name}</div>
                        <div class="key">Usage</div><div class="val">${gpu.util_percent}%</div>
                        <div class="key">Memory</div><div class="val">${gpu.memory_used_mb} / ${gpu.memory_total_mb} MB</div>
                    </div>
                `).join('');
                $('#gpuInfo').innerHTML = gpuHtml;
            }

        } catch (e) {
            console.error("Failed to fetch stats", e);
        }
    }

    $('#logoutBtn').onclick = async () => {
        await fetch('/api/admin/logout', { method: 'POST' });
        window.location.href = '/admin';
    };

    $('#restartBtn').onclick = async () => {
        if (confirm('Are you sure you want to restart the server? This will disconnect all users.')) {
            try {
                await fetch('/api/admin/restart', { method: 'POST' });
                alert('Server is restarting. The page will be unresponsive for a moment.');
            } catch (e) {
                alert('Failed to send restart command.');
            }
        }
    };
    
    pollStats();
    setInterval(pollStats, 2000);
})();