document.addEventListener('DOMContentLoaded', () => {
    // Theme Management
    const themeToggleBtn = document.getElementById('theme-toggle');
    const html = document.documentElement;
    
    // Check saved theme or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemThemeDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && systemThemeDark)) {
        html.classList.add('dark');
        updateThemeIcon(true);
    } else {
        html.classList.remove('dark');
        updateThemeIcon(false);
    }

    themeToggleBtn.addEventListener('click', () => {
        const isDark = html.classList.toggle('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        updateThemeIcon(isDark);
    });

    function updateThemeIcon(isDark) {
        const icon = themeToggleBtn.querySelector('i');
        if (isDark) {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        } else {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
    }

    // Toast Notification
    window.showToast = function(message) {
        let toast = document.getElementById('toast-notification');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'toast-notification';
            toast.className = 'fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-gray-900 dark:bg-white text-white dark:text-gray-900 px-6 py-3 rounded-full shadow-lg z-50 transition-all duration-300 opacity-0 translate-y-10 flex items-center gap-3 font-medium text-sm';
            document.body.appendChild(toast);
        }
        
        toast.innerHTML = `<i class="fas fa-check-circle text-green-500"></i> ${message}`;
        
        // Trigger reflow
        void toast.offsetWidth;

        toast.classList.remove('opacity-0', 'translate-y-10');
        
        if (window.toastTimeout) clearTimeout(window.toastTimeout);
        
        window.toastTimeout = setTimeout(() => {
            toast.classList.add('opacity-0', 'translate-y-10');
        }, 3000);
    };

    // Global copy function
    window.copyToClipboard = function(text, message = "Copied to clipboard!") {
        if (!navigator.clipboard) {
            fallbackCopy(text, message);
            return;
        }
        navigator.clipboard.writeText(text).then(() => {
            showToast(message);
        }).catch(err => {
            console.error('Failed to copy: ', err);
            fallbackCopy(text, message);
        });
    };

    function fallbackCopy(text, message) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed"; 
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showToast(message);
        } catch (err) {
            console.error('Fallback copy failed', err);
            showToast('Failed to copy');
        }
        document.body.removeChild(textArea);
    }

    // Toggle External Nodes
    window.toggleNodes = function() {
        const container = document.getElementById('external-nodes');
        const btnText = document.getElementById('nodes-btn-text');
        const icon = document.getElementById('nodes-btn-icon');
        
        if (container.classList.contains('hidden')) {
            container.classList.remove('hidden');
            setTimeout(() => {
                 container.classList.remove('opacity-0', '-translate-y-2');
            }, 10);
            btnText.innerText = "Hide Nodes";
            icon.style.transform = "rotate(180deg)";
        } else {
            container.classList.add('opacity-0', '-translate-y-2');
            setTimeout(() => {
                container.classList.add('hidden');
            }, 300);
            btnText.innerText = "Show Nodes";
            icon.style.transform = "rotate(0deg)";
        }
    };

    // Tab Switching
    window.switchTab = function(tabName, btn) {
        // Content
        document.querySelectorAll('.tab-content').forEach(el => {
            el.classList.add('hidden', 'opacity-0');
        });
        const activeContent = document.getElementById(`tab-${tabName}`);
        activeContent.classList.remove('hidden');
        // Small delay for fade in
        setTimeout(() => {
            activeContent.classList.remove('opacity-0');
        }, 50);

        // Buttons
        document.querySelectorAll('.tab-btn').forEach(el => {
            el.classList.remove('text-blue-600', 'dark:text-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20', 'border-blue-200', 'dark:border-blue-800');
            el.classList.add('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        });
        
        btn.classList.remove('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        btn.classList.add('text-blue-600', 'dark:text-blue-400', 'bg-blue-50', 'dark:bg-blue-900/20', 'border-blue-200', 'dark:border-blue-800');
    };
});
