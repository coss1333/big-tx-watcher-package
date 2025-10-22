#!/usr/bin/env python3
"""
big_tx_watcher.py

Мониторит ETH и BTC на предмет одиночных транзакций >= THRESHOLD_USD и отправляет уведомления в Telegram.

Сохраните переменные в .env (пример .env.example в комплекте).
"""
import os
import asyncio
import time
from decimal import Decimal

import aiohttp
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")
THRESHOLD_USD = float(os.getenv("THRESHOLD_USD", "5000000"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "12"))
MEMPOOL_BASE = os.getenv("MEMPOOL_BASE", "https://mempool.space")
SEEN_CACHE_SECONDS = int(os.getenv("SEEN_CACHE_SECONDS", 60*60*2))

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in env (see .env.example)")

HEADERS = {"User-Agent": "big-tx-watcher/1.0"}

async def fetch_json(session, url, params=None):
    async with session.get(url, params=params, headers=HEADERS, timeout=30) as resp:
        resp.raise_for_status()
        return await resp.json()

async def post_telegram(session, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    async with session.post(url, data=payload, timeout=20) as r:
        return await r.json()

async def get_prices(session):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids":"bitcoin,ethereum", "vs_currencies":"usd"}
    data = await fetch_json(session, url, params)
    btc = float(data.get("bitcoin", {}).get("usd", 0.0))
    eth = float(data.get("ethereum", {}).get("usd", 0.0))
    return btc, eth

def wei_hex_to_float(wei_hex: str) -> float:
    w = int(wei_hex, 16) if isinstance(wei_hex, str) and wei_hex.startswith("0x") else int(wei_hex)
    return float(Decimal(w) / Decimal(10**18))

class SeenCache:
    def __init__(self):
        self._map = {}

    def add(self, tx):
        self._map[tx] = time.time()

    def seen(self, tx):
        return tx in self._map

    def cleanup(self):
        now = time.time()
        to_del = [k for k,v in self._map.items() if now - v > SEEN_CACHE_SECONDS]
        for k in to_del:
            del self._map[k]

async def process_eth_block(session, prices, seen: SeenCache):
    if not os.getenv("ETHERSCAN_API_KEY"):
        return
    params = {"module":"proxy", "action":"eth_getBlockByNumber", "tag":"latest", "boolean":"true", "apikey": ETHERSCAN_API_KEY}
    url = "https://api.etherscan.io/api"
    resp = await fetch_json(session, url, params=params)
    result = resp.get("result")
    if not result:
        return
    block_number = int(result.get("number", "0x0"), 16)
    timestamp = int(result.get("timestamp", "0x0"), 16)
    txs = result.get("transactions", []) or []
    eth_price = prices[1]
    for tx in txs:
        try:
            txhash = tx.get("hash")
            if not txhash or seen.seen(txhash):
                continue
            value_hex = tx.get("value", "0x0")
            eth_amount = wei_hex_to_float(value_hex)
            usd = eth_amount * eth_price
            if usd >= THRESHOLD_USD:
                seen.add(txhash)
                from_addr = tx.get("from")
                to_addr = tx.get("to")
                etherscan_link = f"https://etherscan.io/tx/{txhash}"
                text = (
                    f"💎 <b>Large ETH tx detected</b>\n"
                    f"Hash: <code>{txhash}</code>\n"
                    f"From: {from_addr}\n"
                    f"To: {to_addr}\n"
                    f"Amount: {eth_amount:.6f} ETH ≈ ${usd:,.2f}\n"
                    f"Block: {block_number} • Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(timestamp))}\n"
                    f"{etherscan_link}"
                )
                await post_telegram(session, text)
        except Exception as e:
            print("ETH tx parse error:", e)

async def process_btc_block(session, prices, seen: SeenCache):
    btc_price = prices[0]
    try:
        height_url = MEMPOOL_BASE.rstrip("/") + "/api/blocks/tip/height"
        async with session.get(height_url, headers=HEADERS, timeout=20) as r:
            r.raise_for_status()
            height_text = await r.text()
            height = int(height_text.strip())
    except Exception as e:
        print("Failed get BTC tip height:", e)
        return

    try:
        block_url = MEMPOOL_BASE.rstrip("/") + f"/api/block/{height}"
        block = await fetch_json(session, block_url)
    except Exception as e:
        print("Failed get BTC block:", e)
        return

    txids = block.get("tx", [])
    for txid in txids:
        if seen.seen(txid):
            continue
        try:
            tx_url = MEMPOOL_BASE.rstrip("/") + f"/api/tx/{txid}"
            tx = await fetch_json(session, tx_url)
            vouts = tx.get("vout", [])
            total_btc = 0.0
            for v in vouts:
                val = v.get("value")
                if val is None:
                    continue
                total_btc += float(val)
            usd = total_btc * btc_price
            if usd >= THRESHOLD_USD:
                seen.add(txid)
                tx_link = f"https://mempool.space/tx/{txid}"
                text = (
                    f"💎 <b>Large BTC tx detected</b>\n"
                    f"Hash: <code>{txid}</code>\n"
                    f"Amount (sum of outputs): {total_btc:.8f} BTC ≈ ${usd:,.2f}\n"
                    f"Block: {height}\n"
                    f"{tx_link}"
                )
                await post_telegram(session, text)
        except Exception as e:
            print("BTC tx parse error:", e)

async def main_loop():
    seen = SeenCache()
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                prices = await get_prices(session)
            except Exception as e:
                print("Price fetch failed:", e)
                prices = (0.0, 0.0)
            try:
                await asyncio.gather(
                    process_eth_block(session, prices, seen),
                    process_btc_block(session, prices, seen),
                )
            except Exception as e:
                print("Processing error:", e)

            seen.cleanup()
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Stopped by user")
