#!/usr/local/bin/python
"""
Main
"""

import os
import json
import time
import logging
from string import whitespace

from notification import Notifier
from exchanges.bittrex import Bittrex

# Let's test an API call to get our BTC balance as a test
# print(BITTREX_CLIENT.get_balance('BTC')['result']['Balance'])

#print(historical_data = BITTREX_CLIENT.get_historical_data('BTC-ETH', 30, "thirtyMin"))
def get_closing_prices(coin_pair, period, unit):
    """
    Returns closing prices within a specified time frame for a coin pair
    :type coin_pair: str
    :type period: str
    :type unit: int
    :return: Array of closing prices
    """

    historical_data = BITTREX_CLIENT.get_historical_data(coin_pair, period, unit)
    closing_prices = []
    for data_point in historical_data:
        closing_prices.append(data_point['C'])
    return closing_prices

def calculate_sma(coin_pair, period, unit):
    """
    Returns the Simple Moving Average for a coin pair
    """

    total_closing = sum(get_closing_prices(coin_pair, period, unit))
    return total_closing / period

def calculate_ema(coin_pair, period, unit):
    """
    Returns the Exponential Moving Average for a coin pair
    """

    closing_prices = get_closing_prices(coin_pair, period, unit)
    previous_ema = calculate_sma(coin_pair, period, unit)
    period_constant = 2 / (1 + period)
    current_ema = (closing_prices[-1] * period_constant) \
                  + (previous_ema * (1 - period_constant))
    return current_ema

# Improvemnts to calculate_rsi are courtesy of community contributor "pcartwright81"
def calculate_rsi(coin_pair, period, unit):
    """
    Calculates the Relative Strength Index for a coin_pair
    If the returned value is above 70, it's overbought (SELL IT!)
    If the returned value is below 30, it's oversold (BUY IT!)
    """
    closing_prices = get_closing_prices(coin_pair, period * 3, unit)
    count = 0
    changes = []
    # Calculating price changes
    for closing_price in closing_prices:
        if count != 0:
            changes.append(closing_price - closing_prices[count - 1])
        count += 1
        if count == 15:
            break

    # Calculating gains and losses
    advances = []
    declines = []
    for change in changes:
        if change > 0:
            advances.append(change)
        if change < 0:
            declines.append(abs(change))

    average_gain = (sum(advances) / 14)
    average_loss = (sum(declines) / 14)
    new_average_gain = average_gain
    new_average_loss = average_loss
    for closing_price in closing_prices:
        if count > 14 and count < len(closing_prices):
            close = closing_prices[count]
            new_change = close - closing_prices[count - 1]
            add_loss = 0
            add_gain = 0
            if new_change > 0:
                add_gain = new_change
            if new_change < 0:
                add_loss = abs(new_change)
            new_average_gain = (new_average_gain * 13 + add_gain) / 14
            new_average_loss = (new_average_loss * 13 + add_loss) / 14
            count += 1

    rs = new_average_gain / new_average_loss
    new_rs = 100 - 100 / (1 + rs)
    return new_rs


def calculate_base_line(coin_pair, unit):
    """
    Calculates (26 period high + 26 period low) / 2
    Also known as the "Kijun-sen" line
    """

    closing_prices = get_closing_prices(coin_pair, 26, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def calculate_conversion_line(coin_pair, unit):
    """
    Calculates (9 period high + 9 period low) / 2
    Also known as the "Tenkan-sen" line
    """
    closing_prices = get_closing_prices(coin_pair, 9, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def calculate_leading_span_a(coin_pair, unit):
    """
    Calculates (Conversion Line + Base Line) / 2
    Also known as the "Senkou Span A" line
    """

    base_line = calculate_base_line(coin_pair, unit)
    conversion_line = calculate_conversion_line(coin_pair, unit)
    return (base_line + conversion_line) / 2

def calculate_leading_span_b(coin_pair, unit):
    """
    Calculates (52 period high + 52 period low) / 2
    Also known as the "Senkou Span B" line
    """
    closing_prices = get_closing_prices(coin_pair, 52, unit)
    period_high = max(closing_prices)
    period_low = min(closing_prices)
    return (period_high + period_low) / 2

def find_breakout(coin_pair, period, unit):
    """
    Finds breakout based on how close the High was to Closing and Low to Opening
    """
    hit = 0
    historical_data = BITTREX_CLIENT.get_historical_data(coin_pair, period, unit)
    for data_point in historical_data:
        if (data_point['C'] == data_point['H']) and (data_point['O'] == data_point['L']):
            hit += 1

    if (hit / period) >= .75:
        notifier = Notifier(CONFIG)
        notifier.notify_all(message="{} is breaking out!".format(coin_pair))
        return "Breaking out!"
    else:
        return "#Bagholding"
    exit()

def get_signal():
    for coin_pair in COIN_PAIRS:
        breakout = find_breakout(coin_pair=coin_pair, period=5, unit="fiveMin")
        rsi = calculate_rsi(coin_pair=coin_pair, period=14, unit="thirtyMin")
        print("{}: \tBreakout: {} \tRSI: {}".format(coin_pair, breakout, rsi))
    time.sleep(300)

if __name__ == "__main__":
    # Load settings and create the CONFIG object
    CONFIG = json.load(open('default-config.json'))

    CONFIG['settings']['market_pairs'] = os.environ.get('MARKET_PAIRS', CONFIG['settings']['market_pairs'])
    CONFIG['settings']['loglevel'] = os.environ.get('LOGLEVEL', logging.INFO)
    CONFIG['exchanges']['bittrex']['required']['key'] = os.environ.get('BITTREX_KEY', CONFIG['exchanges']['bittrex']['required']['key'])
    CONFIG['exchanges']['bittrex']['required']['secret'] = os.environ.get('BITTREX_SECRET', CONFIG['exchanges']['bittrex']['required']['secret'])
    CONFIG['notifiers']['twilio']['required']['key'] = os.environ.get('TWILIO_KEY', CONFIG['notifiers']['twilio']['required']['key'])
    CONFIG['notifiers']['twilio']['required']['secret'] = os.environ.get('TWILIO_SECRET', CONFIG['notifiers']['twilio']['required']['secret'])
    CONFIG['notifiers']['twilio']['required']['sender_number'] = os.environ.get('TWILIO_SENDER_NUMBER', CONFIG['notifiers']['twilio']['required']['sender_number'])
    CONFIG['notifiers']['twilio']['required']['receiver_number'] = os.environ.get('TWILIO_RECEIVER_NUMBER', CONFIG['notifiers']['twilio']['required']['receiver_number'])

    # Set up logger
    LOGGER = logging.getLogger(__name__)
    LOGGER.setLevel(CONFIG['settings']['loglevel'])

    LOG_FORMAT = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_HANDLE = logging.StreamHandler()
    LOG_HANDLE.setLevel(logging.DEBUG)
    LOG_HANDLE.setFormatter(LOG_FORMAT)
    LOGGER.addHandler(LOG_HANDLE)

    # Configure clients for bittrex and twilio
    BITTREX_CLIENT = Bittrex(
        CONFIG['exchanges']['bittrex']['required']['key'],
        CONFIG['exchanges']['bittrex']['required']['secret'])

    # The coin pairs
    COIN_PAIRS = []
    if CONFIG['settings']['market_pairs']:
        COIN_PAIRS = CONFIG['settings']['market_pairs'].translate(str.maketrans('', '', whitespace)).split(",")
    else:
        user_markets = BITTREX_CLIENT.get_balances()
        for user_market in user_markets['result']:
            if 'BTC' in user_market['Currency']:
                continue
            market_pair = 'BTC-' + user_market['Currency']
            COIN_PAIRS.append(market_pair)
    LOGGER.debug(COIN_PAIRS)

    while True:
        get_signal()
