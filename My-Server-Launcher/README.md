# My Server Launcher — Helios-based scaffold

Заготовка лаунчера для будущего Minecraft-сервера.

Архитектурная основа — dscalzi/HeliosLauncher: Electron/Node.js, distribution/manifest, загрузка файлов клиента и отдельный launch-core.

Оригинальный Helios Launcher: https://github.com/dscalzi/HeliosLauncher

Уже есть: Electron UI, адрес сервера, HTTPS Manifest URL, сохранение настроек, загрузка manifest и файлов клиента, HTTPS/path traversal проверки, настройки Minecraft/NeoForge/RAM и точка подключения настоящего launch-core.

Запуск: Node.js 22, затем npm install и npm start.

Следующий этап: Java, Minecraft 1.21.1, NeoForge, SHA-256 проверка и настоящий запуск игры.