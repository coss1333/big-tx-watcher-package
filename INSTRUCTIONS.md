# INSTRUCTIONS — подробная пошаговая инструкция

Эта инструкция дублирует краткую версию в README, но более подробная.

## 1) Подготовка окружения
### На Linux / macOS
```bash
# клонируем / копируем файлы в папку:
mkdir -p ~/big_tx_watcher
cd ~/big_tx_watcher

# создаём виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# ставим зависимости
pip install -r requirements.txt
```

### На Windows (PowerShell)
```powershell
mkdir C:\big_tx_watcher
cd C:\big_tx_watcher

python -m venv venv
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## 2) Настройка файла .env
Скопируй `.env.example` в `.env`:
```bash
cp .env.example .env
```
Открой `.env` и замени:
- `TELEGRAM_BOT_TOKEN` — создай бота у @BotFather и вставь токен.
- `TELEGRAM_CHAT_ID` — для группы: добавь бота в группу, затем получи chat_id (например через @userinfobot или отправь сообщение ботом и посмотри update). Для супергрупп chat_id начинается с `-100`.
- `ETHERSCAN_API_KEY` — зарегистрируйся на https://etherscan.io/, попроси API key (free).

Параметры:
- `THRESHOLD_USD` — порог в USD по одному tx.
- `POLL_INTERVAL` — интервал поллинга (сек).
- `SEEN_CACHE_SECONDS` — как долго помнить уже увиденные tx.

## 3) Запуск
```bash
python big_tx_watcher.py
```
Если всё настроено — в консоли не должно быть фатальных ошибок. При обнаружении большой транзакции ты получишь сообщение в Telegram.

## 4) Дополнения / отладка
- Логирование: можно перенаправить вывод в лог-файл:
  ```bash
  nohup python big_tx_watcher.py > watcher.log 2>&1 &
  ```
- systemd unit пример (Linux) — добавлю при желании.
- Dockerfile: могу подготовить, если хочешь запуск в контейнере.

## 5) Частые проблемы и их решения
- Ошибка 429 (rate limit) от Etherscan/CoinGecko — увеличь `POLL_INTERVAL` или переключись на платный провайдер.
- Бот не пишет в группу — убедись, что бот добавлен в группу и у него есть права отправлять сообщения. Для супергрупп используй корректный `TELEGRAM_CHAT_ID` (начинается с -100...).
- Пропускаются ERC20-транзакции — в этой версии они не анализируются. Нужно добавить отслеживание логов token transfer.

Если хочешь — адаптирую код под:
- отслеживание ERC20 (USDT/USDC) по сумме в USD,
- WebSocket-подписки через Alchemy/Infura для реального времени,
- Docker + systemd + supervisor конфигурации.

