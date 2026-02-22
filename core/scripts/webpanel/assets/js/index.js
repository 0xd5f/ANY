function updateServerInfo() {
    const serverStatusUrl = document.querySelector('.content').dataset.serverStatusUrl;
    fetch(serverStatusUrl)
        .then(response => response.json())
        .then(data => {
            document.getElementById('cpu-usage').textContent = data.cpu_usage;
            const cpuBar = document.getElementById('cpu-bar-visual');
            if (cpuBar) cpuBar.style.width = data.cpu_usage;

            document.getElementById('ram-usage').textContent = `${data.ram_usage} / ${data.total_ram}`;
            
            // Calculate RAM percentage client-side
            const ramBar = document.getElementById('ram-bar-visual');
            if (ramBar) {
                let percent = 0;
                try {
                    const parseVal = (str) => {
                         if (!str) return 0;
                         const num = parseFloat(str);
                         if (str.includes('TB')) return num * 1024 * 1024;
                         if (str.includes('GB')) return num * 1024;
                         if (str.includes('MB')) return num;
                         if (str.includes('KB')) return num / 1024;
                         return num;
                    };
                    const used = parseVal(data.ram_usage);
                    const total = parseVal(data.total_ram);
                    if (total > 0) percent = (used / total) * 100;
                } catch(e) { console.error('RAM calc error', e); }
                ramBar.style.width = `${percent}%`;
            }

            document.getElementById('online-users').textContent = data.online_users;
            document.getElementById('uptime').textContent = data.uptime;

            document.getElementById('server-ipv4').textContent = `IPv4: ${data.server_ipv4 || 'N/A'}`;
            document.getElementById('server-ipv6').textContent = `IPv6: ${data.server_ipv6 || 'N/A'}`;

            document.getElementById('download-speed').textContent = data.download_speed;
            document.getElementById('upload-speed').textContent = data.upload_speed;
            document.getElementById('tcp-connections').textContent = `TCP: ${data.tcp_connections}`;
            document.getElementById('udp-connections').textContent = `UDP: ${data.udp_connections}`;

            document.getElementById('reboot-uploaded-traffic').textContent = data.reboot_uploaded_traffic;
            document.getElementById('reboot-downloaded-traffic').textContent = data.reboot_downloaded_traffic;
            document.getElementById('reboot-total-traffic').textContent = data.reboot_total_traffic;

            document.getElementById('user-uploaded-traffic').textContent = data.user_uploaded_traffic;
            document.getElementById('user-downloaded-traffic').textContent = data.user_downloaded_traffic;
            document.getElementById('user-total-traffic').textContent = data.user_total_traffic;

            pushChartPoint(data);
        })
        .catch(error => console.error('Error fetching server info:', error));
}

function updateServiceStatuses() {
    const servicesStatusUrl = document.querySelector('.content').dataset.servicesStatusUrl;
    fetch(servicesStatusUrl)
        .then(response => response.json())
        .then(data => {
            updateServiceBox('hysteria2', data.hysteria_server);
            updateServiceBox('telegrambot', data.hysteria_telegram_bot);
            updateServiceBox('iplimit', data.hysteria_iplimit);
            updateServiceBox('normalsub', data.hysteria_normal_sub);
        })
        .catch(error => console.error('Error fetching service statuses:', error));
}

function updateServiceBox(serviceName, status) {
    const statusElement = document.getElementById(serviceName + '-status');
    const statusBox = document.getElementById(serviceName + '-status-box');

    if (status === true) {
        statusElement.textContent = 'Active';
        statusBox.classList.remove('bg-rose-500');
        statusBox.classList.add('bg-emerald-500');
    } else {
        statusElement.textContent = 'Inactive';
        statusBox.classList.remove('bg-emerald-500');
        statusBox.classList.add('bg-rose-500');
    }

    if (serviceName === 'hysteria2') {
        const restartBtn = document.getElementById('restart-hysteria2-btn');
        if (status === true) {
            restartBtn.classList.add('hidden');
        } else {
            restartBtn.classList.remove('hidden');
        }
    }
}

// ---- Charts ----
const CHART_MAX = 30;
const chartLabels = [];
const cpuData = [], ramData = [], dlData = [], ulData = [];
let chartCpuRam = null, chartNetwork = null;

function parseSpeedToKbps(str) {
    if (!str) return 0;
    const n = parseFloat(str);
    if (isNaN(n)) return 0;
    const s = str.toUpperCase();
    if (s.includes('GB/S') || s.includes('GB/S')) return n * 1024 * 1024;
    if (s.includes('MB/S')) return n * 1024;
    if (s.includes('KB/S')) return n;
    if (s.includes('B/S')) return n / 1024;
    return n;
}

function parseRamMb(str) {
    if (!str) return 0;
    const n = parseFloat(str);
    if (isNaN(n)) return 0;
    const s = str.toUpperCase();
    if (s.includes('GB')) return n * 1024;
    if (s.includes('TB')) return n * 1024 * 1024;
    return n;
}

function initCharts() {
    const dark = document.documentElement.classList.contains('dark');
    const gridColor = dark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
    const tickColor = dark ? '#71717a' : '#9ca3af';
    const baseOpts = {
        responsive: true, maintainAspectRatio: true,
        animation: { duration: 300 },
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { labels: { color: tickColor, font: { size: 11 }, boxWidth: 12 } }, tooltip: { mode: 'index' } },
        scales: {
            x: { ticks: { color: tickColor, font: { size: 10 }, maxTicksLimit: 6 }, grid: { color: gridColor } },
            y: { ticks: { color: tickColor, font: { size: 10 } }, grid: { color: gridColor }, beginAtZero: true }
        }
    };

    const ctxCR = document.getElementById('chart-cpu-ram');
    const ctxNet = document.getElementById('chart-network');
    if (!ctxCR || !ctxNet) return;

    chartCpuRam = new Chart(ctxCR, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                { label: 'CPU %', data: cpuData, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 },
                { label: 'RAM %', data: ramData, borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,0.1)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 }
            ]
        },
        options: JSON.parse(JSON.stringify(baseOpts))
    });
    chartCpuRam.options.scales.y.max = 100;
    chartCpuRam.options.scales.y.ticks.callback = v => v + '%';
    chartCpuRam.update();

    chartNetwork = new Chart(ctxNet, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [
                { label: '↓ Download', data: dlData, borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 },
                { label: '↑ Upload', data: ulData, borderColor: '#ec4899', backgroundColor: 'rgba(236,72,153,0.08)', borderWidth: 2, pointRadius: 0, fill: true, tension: 0.4 }
            ]
        },
        options: JSON.parse(JSON.stringify(baseOpts))
    });
    chartNetwork.options.scales.y.ticks.callback = v => v >= 1024 ? (v/1024).toFixed(1)+'MB/s' : v.toFixed(1)+'KB/s';
    chartNetwork.update();
}

function pushChartPoint(data) {
    const now = new Date();
    const label = now.getHours().toString().padStart(2,'0') + ':' + now.getMinutes().toString().padStart(2,'0') + ':' + now.getSeconds().toString().padStart(2,'0');
    const cpu = parseFloat(data.cpu_usage) || 0;
    const ramUsedMb = parseRamMb(data.ram_usage);
    const ramTotalMb = parseRamMb(data.total_ram);
    const ramPct = ramTotalMb > 0 ? (ramUsedMb / ramTotalMb) * 100 : 0;
    const dl = parseSpeedToKbps(data.download_speed);
    const ul = parseSpeedToKbps(data.upload_speed);

    chartLabels.push(label);
    cpuData.push(parseFloat(cpu.toFixed(1)));
    ramData.push(parseFloat(ramPct.toFixed(1)));
    dlData.push(parseFloat(dl.toFixed(2)));
    ulData.push(parseFloat(ul.toFixed(2)));

    if (chartLabels.length > CHART_MAX) {
        chartLabels.shift(); cpuData.shift(); ramData.shift(); dlData.shift(); ulData.shift();
    }
    if (chartCpuRam) chartCpuRam.update();
    if (chartNetwork) chartNetwork.update();
}

document.addEventListener('DOMContentLoaded', function () {
    // Load Chart.js then init
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    s.onload = function() { initCharts(); };
    document.head.appendChild(s);

    updateServerInfo();
    updateServiceStatuses();
    setInterval(updateServerInfo, 2000);
    setInterval(updateServiceStatuses, 10000);

    const toggleIpBtn = document.getElementById('toggle-ip-visibility');
    const ipAddressesDiv = document.getElementById('ip-addresses');
    toggleIpBtn.addEventListener('click', function(e) {
        e.preventDefault();
        const isBlurred = ipAddressesDiv.style.filter === 'blur(5px)';
        ipAddressesDiv.style.filter = isBlurred ? 'none' : 'blur(5px)';
        toggleIpBtn.querySelector('i').classList.toggle('fa-eye');
        toggleIpBtn.querySelector('i').classList.toggle('fa-eye-slash');
    });

    const restartBtn = document.getElementById('restart-hysteria2-btn');
    const restartUrl = document.querySelector('.content').dataset.restartHysteriaUrl;
    restartBtn.addEventListener('click', function(e) {
        e.preventDefault();
        
        restartBtn.innerHTML = 'Restarting... <i class="fas fa-sync-alt fa-spin ml-1"></i>';
        restartBtn.style.pointerEvents = 'none';

        fetch(restartUrl, { method: 'POST' })
            .then(response => {
                if (!response.ok) return response.json().then(err => { throw new Error(err.detail || 'Unknown error'); });
                return response.json();
            })
            .then(data => {
                Swal.fire({ icon: 'success', title: 'Success', text: data.detail, timer: 2000, showConfirmButton: false });
                setTimeout(updateServiceStatuses, 1000);
            })
            .catch(error => {
                Swal.fire({ icon: 'error', title: 'Error', text: `Failed to restart Hysteria2: ${error.message}` });
            })
            .finally(() => {
                restartBtn.innerHTML = 'Restart Service <i class="fas fa-sync-alt ml-1"></i>';
                restartBtn.style.pointerEvents = 'auto';
            });
    });

    const versionUrl = $('.content').data('version-url');
    $.ajax({
        url: versionUrl,
        type: 'GET',
        success: function (response) {
            $('#panel-version-display').text(response.current_version || 'N/A');
            if (response.core_version) {
                $('#core-version-display').text(response.core_version);
                $('#core-version-row').show();
            }
        },
        error: function (error) {
            console.error("Error fetching version:", error);
            $('#panel-version-display').text('Error');
        }
    });

    function shouldCheckForUpdates() {
        const lastCheck = localStorage.getItem('lastUpdateCheck');
        const updateDismissed = localStorage.getItem('updateDismissed');
        const now = Date.now();
        const checkInterval = 24 * 60 * 60 * 1000;
        
        if (!lastCheck) return true;
        if (updateDismissed && now - parseInt(updateDismissed) < 2 * 60 * 60 * 1000) return false;
        
        return now - parseInt(lastCheck) > checkInterval;
    }

    function showUpdateBar(version, changelog) {
        $('#updateMessage').text(`Version ${version} is now available`);
        
        const converter = new showdown.Converter();
        const htmlChangelog = changelog ? converter.makeHtml(changelog) : '<p>No changelog available.</p>';
        $('#changelogText').html(htmlChangelog);

        $('#updateBar').slideDown(300);
        
        $('#viewRelease').hide(); // Hide button as we removed the link
        
        $('#showChangelog').off('click').on('click', function() {
            const $content = $('#changelogContent');
            const $icon = $(this).find('i');
            
            if ($content.is(':visible')) {
                $content.slideUp(250);
                $icon.removeClass('fa-chevron-up').addClass('fa-chevron-down');
                $(this).css('opacity', '0.8');
            } else {
                $content.slideDown(250);
                $icon.removeClass('fa-chevron-down').addClass('fa-chevron-up');
                $(this).css('opacity', '1');
            }
        });
        
        $('.dropdown-toggle').dropdown();
        
        $('#remindLater').off('click').on('click', function(e) {
            e.preventDefault();
            $('#updateBar').slideUp(350);
        });
        
        $('#skipVersion').off('click').on('click', function(e) {
            e.preventDefault();
            localStorage.setItem('dismissedVersion', version);
            localStorage.setItem('updateDismissed', Date.now().toString());
            $('#updateBar').slideUp(350);
        });
        
        $('#closeUpdateBar').off('click').on('click', function() {
            $('#updateBar').slideUp(350);
        });
    }

    function checkForUpdates() {
        // Always check (removed shouldCheckForUpdates restriction for immediate UI feedback for now, or keep logic but ensure indicator updates)
        // Ideally we check every time or respect interval but Update Indicator should show if we know there is an update
        if (!shouldCheckForUpdates()) {
             // Even if we don't fetch new info, valid if we already know? 
             // Simplest: Just run the check. The overhead is small. 
             // Or better: Let's stick to the check logic but handle the indicator inside success.
        }

        const checkVersionUrl = $('.content').data('check-version-url');
        $.ajax({
            url: checkVersionUrl,
            type: 'GET',
            timeout: 10000,
            success: function (response) {
                localStorage.setItem('lastUpdateCheck', Date.now().toString());
                
                if (response.is_latest) {
                    $('#update-indicator').addClass('hidden');
                    localStorage.removeItem('updateDismissed');
                    return;
                } else {
                    $('#update-indicator').removeClass('hidden');
                }

                const dismissedVersion = localStorage.getItem('dismissedVersion');
                if (dismissedVersion === response.latest_version) return;

                showUpdateBar(response.latest_version, response.changelog);
            },
            error: function (xhr, status, error) {
                if (status !== 'timeout') {
                    console.warn("Update check failed:", error);
                }
                localStorage.setItem('lastUpdateCheck', Date.now().toString());
            }
        });
    }

    setTimeout(checkForUpdates, 2000);
});