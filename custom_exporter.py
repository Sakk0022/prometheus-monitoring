import time
import requests
from prometheus_client import start_http_server, Gauge, Counter
from collections import deque  # Для простой истории цен (для volatility)

# Метрики (расширили до 12+)
price_usd = Gauge('crypto_price_usd', 'Current price in USD', ['coin', 'category'])
market_cap_usd = Gauge('crypto_market_cap_usd', 'Market cap in USD', ['coin', 'category'])
volume_24h_usd = Gauge('crypto_volume_24h_usd', '24h trading volume in USD', ['coin', 'category'])
change_24h_percent = Gauge('crypto_change_24h_percent', '24h price change percentage', ['coin', 'category'])
high_24h_usd = Gauge('crypto_high_24h_usd', '24h high price in USD', ['coin', 'category'])
low_24h_usd = Gauge('crypto_low_24h_usd', '24h low price in USD', ['coin', 'category'])
ath_usd = Gauge('crypto_ath_usd', 'All-time high price in USD', ['coin', 'category'])
atl_usd = Gauge('crypto_atl_usd', 'All-time low price in USD', ['coin', 'category'])
circulating_supply = Gauge('crypto_circulating_supply', 'Circulating supply', ['coin', 'category'])
total_supply = Gauge('crypto_total_supply', 'Total supply', ['coin', 'category'])
volatility_24h = Gauge('crypto_volatility_24h', '24h volatility (high-low)/price', ['coin', 'category'])  # Новая: для波动 графиков
volume_changes = Counter('crypto_volume_changes_total', 'Cumulative volume changes', ['coin', 'category'])  # Counter для rate графиков

coins = ['bitcoin', 'ethereum', 'solana', 'binancecoin']  # Больше монет для сравнений
categories = {'bitcoin': 'top_coin', 'ethereum': 'top_coin', 'solana': 'alt_coin', 'binancecoin': 'alt_coin'}  # Labels для группировок

# Простая история цен (последние 5 значений для расчета volatility, если API не дает)
price_history = {coin: deque(maxlen=5) for coin in coins}  # Храним последние 5 цен для stddev-like

def collect_metrics():
    prev_volumes = {coin: 0 for coin in coins}  # Для расчета изменений volume
    while True:
        try:
            ids = ','.join(coins)
            response = requests.get(
                f'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={ids}&order=market_cap_desc&per_page=10&page=1&sparkline=false&price_change_percentage=24h'
            )
            data = response.json()
            
            for coin_data in data:
                coin = coin_data['id']
                cat = categories.get(coin, 'other')
                
                current_price = coin_data.get('current_price', 0)
                price_usd.labels(coin, cat).set(current_price)
                market_cap_usd.labels(coin, cat).set(coin_data.get('market_cap', 0))
                current_volume = coin_data.get('total_volume', 0)
                volume_24h_usd.labels(coin, cat).set(current_volume)
                change_24h_percent.labels(coin, cat).set(coin_data.get('price_change_percentage_24h', 0))
                high = coin_data.get('high_24h', 0)
                low = coin_data.get('low_24h', 0)
                high_24h_usd.labels(coin, cat).set(high)
                low_24h_usd.labels(coin, cat).set(low)
                ath_usd.labels(coin, cat).set(coin_data.get('ath', 0))
                atl_usd.labels(coin, cat).set(coin_data.get('atl', 0))
                circulating_supply.labels(coin, cat).set(coin_data.get('circulating_supply', 0))
                total_supply.labels(coin, cat).set(coin_data.get('total_supply', 0))
                
                # Новая volatility
                vol = (high - low) / current_price if current_price > 0 else 0
                volatility_24h.labels(coin, cat).set(vol)
                
                # Counter для изменений volume (для rate в PromQL)
                volume_change = abs(current_volume - prev_volumes[coin])
                volume_changes.labels(coin, cat).inc(volume_change)
                prev_volumes[coin] = current_volume
                
                # История для будущих расширений (например, custom stddev)
                price_history[coin].append(current_price)
            
            print("Metrics updated")
        except Exception as e:
            print(f"Error fetching data: {e}")
        
        time.sleep(20)

if __name__ == '__main__':
    start_http_server(8000)
    collect_metrics()