## [Update] - 2026-02-11 - v1.4.7

### Added
- **Masquerade Proxy Mode**: Новый режим маскировки — Proxy. Зеркалирует реальный сайт (например google.com) при зондировании DPI, вместо стандартной страницы "502 Bad Gateway". Выбор режима (String/Proxy) и ввод URL доступны в Hysteria Settings → Masquerade.
- **Renew API Endpoint**: `POST /api/v1/users/{username}/renew` — продление подписки одним вызовом: сброс даты создания, разблокировка, опциональный сброс трафика и изменение лимитов.
- **Reset Traffic Flag**: Параметр `--reset-traffic` в `edit_user.py` для обнуления счётчиков download/upload.
- **Hop Interval**: Настройка интервала переключения портов (5–300 сек) в Port Hopping — UI поле, API параметр, поддержка в URI (`hop_interval` query param).
- **Auto Installer**: Новый скрипт `install_auto.sh` — полностью автоматическая установка, спрашивает только домен. Генерирует логин/пароль и выводит URL панели.
- **API Documentation**: Документация для эндпоинтов `/renew` и `/reset` в API Docs.

### Fixed
- **Block User Toggle**: Исправлен баг, при котором переключатель блокировки пользователя не работал — планировщик (`kick_expired_users`) повторно блокировал пользователя каждые 60 сек. Теперь при разблокировке автоматически обновляется дата создания аккаунта.
- **Telegram Bot Renew**: Команда `renew_creation` в боте теперь автоматически разблокирует пользователя (`--unblocked`).
- **Secret Path Error**: Исправлена ошибка "WEBPANEL_SCRIPT" при смене Secret Path — удалена дублирующая функция с несуществующей командой.
- **Port Hopping URI Format**: URI теперь использует `mport` query параметр вместо диапазона портов в поле port, для корректной работы с клиентами.

### Improved
- **No-AVX Installer**: При отсутствии поддержки AVX на CPU инсталляторы (`install.sh`, `install_auto.sh`) теперь предлагают автоматически переключиться на `nodb` версию вместо аварийного завершения.
- **README.md**: Полностью переработан — добавлены оглавление, навигация, описания Web Panel, API, Telegram Bot, Anti-Censorship, Port Hopping, WARP, архитектура проекта, секция nodb для CPU без AVX.

### Changed
- **Masquerade API Response**: `GET /check-masquerade` возвращает JSON `{enabled, type, url}` вместо строки `{status}`.
- **Port Hopping API**: `POST /port-hopping/enable` принимает параметр `hop_interval`.
