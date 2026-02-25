document.addEventListener('alpine:init', () => {
    Alpine.data('proxyManager', () => ({
        isInstalled: false,
        isLoading: true,
        isSaving: false,
        isSavingConfig: false,
        users: [],
        config: {
            socks_port: 1080,
            http_port: 3128,
            max_conns: 5000
        },
        showAddModal: false,
        formData: {
            username: '',
            password: ''
        },

        init() {
            this.checkStatus();
            this.loadConfig();
        },

        async checkStatus() {
            try {
                const response = await fetch('../api/v1/proxy/status');
                const data = await response.json();
                this.isInstalled = data.installed;
                if (this.isInstalled) {
                    await this.loadUsers();
                }
            } catch (error) {
                console.error("Error checking 3proxy status:", error);
                this.showToast('Failed to check proxy status', 'error');
            } finally {
                this.isLoading = false;
            }
        },

        async loadUsers() {
            try {
                const response = await fetch('../api/v1/proxy/users');
                if (!response.ok) throw new Error("Failed to load users");
                this.users = await response.json();
            } catch (error) {
                console.error("Error loading users:", error);
                this.showToast('Failed to load users', 'error');
            }
        },

        async installProxy() {
            this.isSaving = true;
            try {
                const response = await fetch('../api/v1/proxy/install', { method: 'POST' });
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || "Installation failed.");
                }
                this.showToast('Installing 3Proxy in background...', 'info');

                // Poll status
                let attempts = 0;
                const interval = setInterval(async () => {
                    attempts++;
                    const res = await fetch('../api/v1/proxy/status');
                    const statusData = await res.json();
                    if (statusData.installed) {
                        clearInterval(interval);
                        this.isInstalled = true;
                        this.isSaving = false;
                        this.users = [];
                        this.showToast('3Proxy installed successfully!', 'success');
                    } else if (attempts > 30) {
                        clearInterval(interval);
                        this.isSaving = false;
                        this.showToast('Installation took too long. Please check the logs.', 'error');
                    }
                }, 3000);

            } catch (error) {
                this.isSaving = false;
                this.showToast(error.message, 'error');
            }
        },

        async uninstallProxy() {
            const result = await Swal.fire({
                title: 'Uninstall Proxy?',
                text: "This will remove all proxies and delete all users!",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#ef4444',
                cancelButtonColor: '#6b7280',
                confirmButtonText: 'Yes, uninstall it!'
            });

            if (result.isConfirmed) {
                this.isSaving = true;
                try {
                    const response = await fetch('../api/v1/proxy/uninstall', { method: 'DELETE' });
                    if (!response.ok) throw new Error("Uninstallation failed");

                    this.isInstalled = false;
                    this.users = [];
                    this.showToast('3Proxy uninstalled successfully', 'success');
                } catch (error) {
                    this.showToast('Failed to uninstall Proxy', 'error');
                } finally {
                    this.isSaving = false;
                }
            }
        },

        openAddUserModal() {
            this.formData = { username: '', password: '' };
            this.showAddModal = true;
        },

        closeAddUserModal() {
            this.showAddModal = false;
        },

        generateUsername() {
            const chars = "abcdefghijklmnopqrstuvwxyz0123456789";
            let username = "user_";
            for (let i = 0; i < 6; i++) {
                username += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            this.formData.username = username;
        },

        generatePassword() {
            const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
            let password = "";
            for (let i = 0; i < 12; i++) {
                password += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            this.formData.password = password;
        },

        async addUser() {
            if (!this.formData.username) {
                this.showToast('Username is required', 'error');
                return;
            }

            this.isSaving = true;
            try {
                const response = await fetch('../api/v1/proxy/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: this.formData.username,
                        password: this.formData.password
                    })
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || "Failed to add user");
                }

                this.showToast('User created successfully', 'success');
                this.closeAddUserModal();
                await this.loadUsers();
            } catch (error) {
                this.showToast(error.message, 'error');
            } finally {
                this.isSaving = false;
            }
        },

        async deleteUser(username) {
            const result = await Swal.fire({
                title: 'Delete ' + username + '?',
                text: "They will instantly lose proxy access.",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#ef4444',
                cancelButtonColor: '#6b7280',
                confirmButtonText: 'Yes, delete!'
            });

            if (result.isConfirmed) {
                try {
                    const response = await fetch(`../api/v1/proxy/users/${username}`, { method: 'DELETE' });
                    if (!response.ok) throw new Error("Deletion failed");

                    await this.loadUsers();
                    this.showToast('User deleted', 'success');
                } catch (error) {
                    this.showToast('Failed to delete user', 'error');
                }
            }
        },

        async loadConfig() {
            try {
                const response = await fetch('../api/v1/proxy/config');
                if (response.ok) {
                    const data = await response.json();
                    if (data) {
                        this.config = {
                            socks_port: data.socks_port || 1080,
                            http_port: data.http_port || 3128,
                            max_conns: data.max_conns || 5000
                        };
                    }
                }
            } catch (error) {
                console.error("Error loading proxy config:", error);
            }
        },

        async saveConfig() {
            this.isSavingConfig = true;
            try {
                const response = await fetch('../api/v1/proxy/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(this.config)
                });

                if (!response.ok) {
                    throw new Error("Failed to save configuration");
                }

                this.showToast('Proxy settings saved successfully!', 'success');
                // Reload users to update displayed ports in the UI if needed
                if (this.isInstalled) {
                    await this.loadUsers();
                }
            } catch (error) {
                this.showToast(error.message, 'error');
            } finally {
                this.isSavingConfig = false;
            }
        },

        showToast(message, type = 'success') {
            const Toast = Swal.mixin({
                toast: true,
                position: 'top-end',
                showConfirmButton: false,
                timer: 3000,
                timerProgressBar: true,
                background: document.documentElement.classList.contains('dark') ? '#18181b' : '#ffffff',
                color: document.documentElement.classList.contains('dark') ? '#ffffff' : '#374151',
                didOpen: (toast) => {
                    toast.addEventListener('mouseenter', Swal.stopTimer)
                    toast.addEventListener('mouseleave', Swal.resumeTimer)
                }
            });

            Toast.fire({
                icon: type,
                title: message
            });
        }
    }));
});
