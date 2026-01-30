## [Update] - 2026-01-30 - v1.4.0

### Added
- **SSL Management UI**: В настройки веб-панели добавлена новая вкладка для управления SSL-сертификатами. Теперь можно вручную указывать пути к сертификатам или выбирать найденные файлы из `/etc/hysteria`.
- **Easy Certbot**: В консольное меню запуска Веб-Панели (пункт 8 -> 1) добавлена опция автоматического получения сертификатов Let's Encrypt.
- **Zero-Config SSL**: Скрипт теперь автоматически использует дефолтный email для регистрации в Certbot, не требуя ввода от пользователя.

### Fixed
- **Critical Fix**: Исправлены окончания строк (CRLF -> LF) во всех скриптах, устраняющие ошибки запуска на Linux (`command not found`, `syntax error`).
- **Web Panel UI**: Исправлено "мигание" вкладок в настройках и удалены лишние текстовые артефакты.

### Caddy Port 80 443 only
- Use self-signed certificate? (Recommended for Cloudflare Full SSL) [y/n]: n
- Do you want to generate a trusted certificate using Certbot (Let's Encrypt)? [y/n]: n
