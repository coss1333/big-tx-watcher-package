# big_tx_watcher — package

В этом архиве:
- `big_tx_watcher.py` — основной скрипт (async Python).
- `.env.example` — пример файла с переменными окружения.
- `requirements.txt` — зависимости.
- `INSTRUCTIONS.md` — подробная, пошаговая инструкция (отдельный файл).

---

## Быстрая инструкция (коротко)

1. Скопируй файлы на сервер/компьютер.
2. Создай виртуальное окружение и установи зависимости:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate.bat # Windows (PowerShell)
   pip install -r requirements.txt
   ```
3. Скопируй `.env.example` в `.env` и заполни:
   - `TELEGRAM_BOT_TOKEN` — токен бота
   - `TELEGRAM_CHAT_ID` — id чата или супергруппы (например, -100123...)
   - `ETHERSCAN_API_KEY` — (получается бесплатно на https://etherscan.io/)
4. Запусти:
   ```bash
   python big_tx_watcher.py
   ```
5. По умолчанию будет мониториться каждый `POLL_INTERVAL` секунд. При нахождении транзакции >= `THRESHOLD_USD` в одном tx — бот отправит сообщение в Telegram.

---

## Замечания
- Для отслеживания крупных **ERC20-token** (USDT/USDC) потребуется дополнить код — в present версии отслеживаются только native transfers (ETH value и сумма выходов BTC).
- На бесплатных API существуют rate limits. Если видишь ошибки 429 — увеличь `POLL_INTERVAL` или используй платные/устойчивые провайдеры (Alchemy/Infura для ETH, приватный Esplora/mempool для BTC).
- Для production рекомендую запускать скрипт как systemd-сервис или в Docker.

Все подробности — в файле `INSTRUCTIONS.md` внутри архива.
