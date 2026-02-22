## [Update] - 2026-02-23 - v1.4.8

### Added
- **Subscription Template Editor**: Полностью редактируемые HTML/CSS/JS шаблоны subscription страницы через веб-панель. Настройки → Subscription Settings → Edit Template позволяет кастомизировать `index.html`, `style.css`, `script.js`. Изменения применяются без перезагрузки сервиса.
- **Tunnel Wizard Redesign**: Полная переработка интерфейса управления туннелями — новый адаптивный дизайн, расширенные фильтры (status, type, provider), поддержка пагинации, интеграция с External Nodes.
- **Auto Node Installation**: Автоматическая установка Hysteria2 на удалённых серверах через Tunnel Wizard — поддержка SSH (Ubuntu/Debian) и Docker. Генерация install-скриптов с автоконфигурацией порта, SNI, OBFS, pin. Endpoint `POST /api/v1/config/tunnel-exec` для выполнения команд.
- **External Nodes UI**: Адаптация панели для приложения HAAP — Add Node / Edit Node формы с полями location, IP, port, SNI, OBFS, pinSHA256, insecure. Node Manager (`node.py`) для CRUD операций с `nodes.json`.
- **Users Table Redesign**: Переработан дизайн таблицы пользователей — компактный вид, улучшенная читаемость, адаптивные колонки, оптимизированная производительность рендеринга.
- **Modal Redesign**: Обновлены все модальные окна — современный дизайн с плавными анимациями, улучшенная доступность, адаптивная вёрстка для мобильных устройств.
- **Subscription Page Redesign**: Полностью переработана визуальная часть subscription страницы — адаптивный дизайн, поддержка тёмной темы, копирование URI одним кликом, QR-коды для каждого сервера.

### Fixed
- **External Nodes Pin Format**: Исправлена генерация URI для External Nodes — `pinSHA256` теперь корректно конвертируется из hex-формата (`XX:XX:XX`) в формат `sha256/BASE64URL`, требуемый клиентами (HAAP/Hiddify). Добавлена функция `hex_pin_to_uri()` в `wrapper_uri.py`.
- **Port Hopping for External Nodes**: Port Hopping параметры (`mport` и `mportHopInt`) теперь корректно передаются для External Nodes в subscription URIs. Ранее эти параметры добавлялись только для основного сервера.
- **Tunnel Wizard Docker Template**: Исправлен синтаксис Jinja2 в Docker template для Tunnel Wizard — `{{.Names}}` заменён на `{{ "{{.Names}}" }}` для корректного отображения в скрипте автоустановки.

### Improved
- **Subscription URI Generation**: Улучшена обработка TLS fingerprints — функция `hex_pin_to_uri()` автоматически распознаёт формат (`sha256/...` или hex) и корректно конвертирует для всех серверов.
- **Nodes Management**: Расширен API endpoint `/api/v1/config/nodes` — добавлена поддержка heartbeat от удалённых нод, версионирование, проверка доступности.
- **Tunnel Wizard Templates**: Улучшены install-скрипты — автоматическое определение архитектуры (amd64/arm64), retry-логика для загрузок, валидация config.yaml перед запуском.
- **External Nodes Validation**: Добавлена валидация полей при добавлении/редактировании нод — проверка формата IP, диапазона портов, валидности pinSHA256 (hex формат).
