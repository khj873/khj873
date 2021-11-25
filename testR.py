from os import system
import time
import pandas
import pyupbit
import datetime
import numpy
import requests
import logging
from datetime import datetime
import time, calendar

access = "oce6CqVtEk6tU5lSVyGGcQRkPEuRlt6LO11R4x1q"
secret = "AY8QfWC11UsQ5dnwU5Fy8PNPuwYLSJ11JVOUx9Al"

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def send_request(reqType, reqUrl, reqParam, reqHeader):
    try:
 
        # 요청 가능회수 확보를 위해 기다리는 시간(초)
        err_sleep_time = 0.3
 
        # 요청에 대한 응답을 받을 때까지 반복 수행
        while True:
 
            # 요청 처리
            response = requests.request(reqType, reqUrl, params=reqParam, headers=reqHeader)
 
            # 요청 가능회수 추출
            if 'Remaining-Req' in response.headers:
 
                hearder_info = response.headers['Remaining-Req']
                start_idx = hearder_info.find("sec=")
                end_idx = len(hearder_info)
                remain_sec = hearder_info[int(start_idx):int(end_idx)].replace('sec=', '')
            else:
                logging.error("헤더 정보 이상")
                logging.error(response.headers)
                break
 
            # 요청 가능회수가 3개 미만이면 요청 가능회수 확보를 위해 일정시간 대기
            if int(remain_sec) < 3:
                logging.debug("요청 가능회수 한도 도달! 남은횟수:" + str(remain_sec))
                time.sleep(err_sleep_time)
 
            # 정상 응답
            if response.status_code == 200 or response.status_code == 201:
                break
            # 요청 가능회수 초과인 경우
            elif response.status_code == 429:
                logging.error("요청 가능회수 초과!:" + str(response.status_code))
                time.sleep(err_sleep_time)
            # 그 외 오류
            else:
                logging.error("기타 에러:" + str(response.status_code))
                logging.error(response.status_code)
                break
 
            # 요청 가능회수 초과 에러 발생시에는 다시 요청
            logging.info("[restRequest] 요청 재처리중...")
 
        return response
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
        
def get_candle(target_item, tick_kind, inq_range):
    try:
 
        # ----------------------------------------
        # Tick 별 호출 URL 설정
        # ----------------------------------------
        # 분붕
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        # 일봉
        elif tick_kind == "D":
            target_url = "days"
        # 주봉
        elif tick_kind == "W":
            target_url = "weeks"
        # 월봉
        elif tick_kind == "M":
            target_url = "months"
        # 잘못된 입력
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))
  
        # ----------------------------------------
        # Tick 조회
        # ----------------------------------------
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", "https://api.upbit.com" + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()
  
        return candle_data
 
    # ----------------------------------------
    # Exception Raise
    # ----------------------------------------
    except Exception:
        raise
        
        
def get_bb(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 볼린저밴드 데이터 리턴용
        bb_list = []
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
        candles=[]
        for i in candle_data:
            candle2={}
            candle2['time']=i['candle_date_time_kst']
            candle2['open']=i['opening_price']
            candle2['high']=i['high_price']
            candle2['low']=i['low_price']
            candle2['close']=i['trade_price']
            candle2['vol']=i['candle_acc_trade_volume']
            candles.append(candle2)
        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])
 
        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pandas.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]
 
            # 표준편차(곱)
            unit = 2
 
            band1 = unit * numpy.std(df[len(df) - 20:len(df)])
            bb_center = numpy.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BH": round(band_high, 4), "BM": round(bb_center, 4),
                           "BL": round(band_low, 4)})
 
        return candles, bb_list
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

tickers=[]
tempT=pyupbit.get_tickers(fiat="KRW")
sumprice=0
for t in tempT:
    cd, bb=get_bb(t, '1', '200', 30)
    for i in range(0, 10):
        sumprice+=cd[i]['high']/cd[i]['low']
    sumprice=float(sumprice/10)
    if sumprice>1.006 and cd[0]['close']>1200:
        tickers.append(t)
print(tickers)
#print(tickers)
# 자동매매 시작
buyPrice={}
sellPrice={}
체크=False
while True:
    try:
        t_now = datetime.now()
        if t_now.minute == 11 or t_now.minute == 21 or t_now.minute == 31 or t_now.minute == 41 or t_now.minute == 51 or t_now.minute == 1:
            체크=False
        if (t_now.minute == 10 or t_now.minute == 20 or t_now.minute == 30 or t_now.minute == 40 or t_now.minute == 50 or t_now.minute == 0) and not 체크:
            tickers.clear()
            tempT=pyupbit.get_tickers(fiat="KRW")
            sumprice=0
            for t in tempT:
                cd, bb=get_bb(t, '1', '200', 30)
                for i in range(0, 10):
                    sumprice+=cd[i]['high']/cd[i]['low']
                sumprice=float(sumprice/10)
                if sumprice>1.006 and cd[0]['close']>1200:
                    tickers.append(t)
            print(tickers)
            체크=True

        account=upbit.get_balances()
        if len(account)>=2:
            try:
                #여기에 매도감시
                for ac in account:
                    if ac['currency']!='KRW':
                        ticker='KRW-'+ac['currency']
                        cd, bb=get_bb(ticker, '1', '200', 30)
                        if pyupbit.get_current_price(ticker)/float(ac['avg_buy_price']) > 1.005:
                            #매도
                            bal = upbit.get_balance(ticker)
                            if bal > 0:
                                upbit.sell_market_order(ticker, bal)
                                del buyPrice[ticker]
                                print(pyupbit.get_current_price(ticker))
                                print(ac['avg_buy_price'])
                                print("매도-이익")
                        if ticker in sellPrice:
                            if cd[0]['close']<sellPrice[ticker]:
                                #매도
                                bal = upbit.get_balance(ticker)
                                if bal > 0:
                                    upbit.sell_market_order(ticker, bal)
                                    print(pyupbit.get_current_price(ticker))
                                    print("매도-손해")
                                    if ticker in buyPrice:
                                        del buyPrice[ticker]
                        else:
                            if pyupbit.get_current_price(ticker)/float(ac['avg_buy_price']) < 0.99:
                                #매도
                                bal = upbit.get_balance(ticker)
                                if bal > 0:
                                    upbit.sell_market_order(ticker, bal)
                                    print(pyupbit.get_current_price(ticker))
                                    print("매도-손해")
                                    if ticker in buyPrice:
                                        del buyPrice[ticker]
                        break
            except Exception as e:
                print(e)
                print("매도구역err")
        else:
            for ticker in tickers:
                cd, bb=get_bb(ticker, '1', '200', 30)
                tp=0
                sumprice=0
                if bb[0]['BM']>bb[5]['BM']:
                    if cd[1]['open']<bb[1]['BM'] and cd[1]['open']>cd[1]['close'] and cd[1]['vol']>cd[2]['vol']:
                        tp=cd[1]['high']
                    if tp!=0:
                        if cd[0]['open']<cd[0]['close'] and cd[0]['close']>tp:
                            #매수. 매도는 볼린저밴드 상단에서, 손절은 볼린저밴드 중단에서
                            krw=upbit.get_balance("KRW")
                            if krw > 5000:
                                upbit.buy_market_order(ticker, krw*0.9995)
                                buyPrice[ticker]=pyupbit.get_current_price(ticker)
                                sellPrice[ticker]=cd[1]['low']
                                print(pyupbit.get_current_price(ticker))
                                print("매수:", ticker)
        time.sleep(0.4)
    except Exception as e:
        print(e)
        time.sleep(1)
'''
매수
if krw > 5000:
    upbit.buy_market_order("KRW-BTC", krw*0.9995)
'''
'''
매도
btc = get_balance("BTC")
if btc > 0.00008:
    upbit.sell_market_order("KRW-BTC", btc*0.9995)
'''