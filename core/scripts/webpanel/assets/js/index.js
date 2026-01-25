function updateServerInfo() {
    const serverStatusUrl = document.querySelector('.content').dataset.serverStatusUrl;
    fetch(serverStatusUrl)
        .then(response => response.json())
        .then(data => {
            document.getElementById('cpu-usage').textContent = data.cpu_usage;
            const cpuBar = document.getElementById('cpu-bar-visual');
            if (cpuBar) cpuBar.style.width = data.cpu_usage;

            document.getElementById('ram-usage').textContent = `${data.ram_usage} / ${data.total_ram}`;
            document.getElementById('online-users').textContent = data.online_users;
            document.getElementById('uptime').textContent = data.uptime;

            document.getElementById('server-ipv4').textContent = `IPv4: ${data.server_ipv4 || 'N/A'}`;
            document.getElementById('server-ipv6').textContent = `IPv6: ${data.server_ipv6 || 'N/A'}`;

            document.getElementById('download-speed').textContent = `🔽 Download: ${data.download_speed}`;
            document.getElementById('upload-speed').textContent = `🔼 Upload: ${data.upload_speed}`;
            document.getElementById('tcp-connections').textContent = `TCP: ${data.tcp_connections}`;
            document.getElementById('udp-connections').textContent = `UDP: ${data.udp_connections}`;

            document.getElementById('reboot-uploaded-traffic').textContent = data.reboot_uploaded_traffic;
            document.getElementById('reboot-downloaded-traffic').textContent = data.reboot_downloaded_traffic;
            document.getElementById('reboot-total-traffic').textContent = data.reboot_total_traffic;

            document.getElementById('user-uploaded-traffic').textContent = data.user_uploaded_traffic;
            document.getElementById('user-downloaded-traffic').textContent = data.user_downloaded_traffic;
            document.getElementById('user-total-traffic').textContent = data.user_total_traffic;
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

document.addEventListener('DOMContentLoaded', function () {
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
        if (!shouldCheckForUpdates()) return;

        const checkVersionUrl = $('.content').data('check-version-url');
        $.ajax({
            url: checkVersionUrl,
            type: 'GET',
            timeout: 10000,
            success: function (response) {
                localStorage.setItem('lastUpdateCheck', Date.now().toString());
                
                if (response.is_latest) {
                    localStorage.removeItem('updateDismissed');
                    return;
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