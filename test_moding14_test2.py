import json
from math import fabs
from os import system
import time
import pandas
import pyupbit
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


def get_rsi(target_item, tick_kind, inq_range):
    try:
 
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
 
        df = pandas.DataFrame(candle_data)
        df = df.reindex(index=df.index[::-1]).reset_index()
 
        df['close'] = df["trade_price"]
 
        # RSI 계산
        def rsi(ohlc: pandas.DataFrame, period: int = 14):
            ohlc["close"] = ohlc["close"]
            delta = ohlc["close"].diff()
 
            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0
 
            _gain = up.ewm(com=(period - 1), min_periods=period).mean()
            _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()
 
            RS = _gain / _loss
            return pandas.Series(100 - (100 / (1 + RS)), name="RSI")
        rsiList=[]
        for i in range(1, len(df)-14):
            rsiList.append(round(rsi(df, 14).iloc[-i], 4))
        return rsiList
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise


def get_bb50(target_item, tick_kind, inq_range, loop_cnt):
    try:
 
        # 캔들 데이터 조회용
        candle_datas = []
 
        # 볼린저밴드 데이터 리턴용
        bb_list = []
        ma5List = []
        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)
        candles=[]
        for i in candle_data:
            candle2={}
            candle2['time']=i['candle_date_time_kst']
            candle2['timestamp']=i['timestamp']
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
 
            band1 = unit * numpy.std(df[len(df) - 50:len(df)])
            bb_center = numpy.mean(df[len(df) - 50:len(df)])
            ma5 = numpy.mean(df[len(df) - 5:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1
 
            bb_list.append({"type": "BB", "DT": dfDt[0], "BH": round(band_high, 4), "BM": round(bb_center, 4),
                           "BL": round(band_low, 4)})
            ma5List.append(ma5)
 
        return candles, bb_list, ma5List
 
 
    # ----------------------------------------
    # 모든 함수의 공통 부분(Exception 처리)
    # ----------------------------------------
    except Exception:
        raise

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

def get_volumeOrder(tickerList):
    tickers=""
    for i in range(len(tickerList)-1):
        tickers+=tickerList[i]+"%2C%20"
    tickers+=tickerList[len(tickerList)-1]
    url = "https://api.upbit.com/v1/ticker?markets="+tickers
    headers = {"Accept": "application/json"}
    response = requests.request("GET", url, headers=headers)
    responseDict = json.loads(response.text)
    responseDict=sorted(responseDict, key=(lambda x: x['acc_trade_price_24h']), reverse=True)
    responseList = []
    
    for r in responseDict:
        if r['acc_trade_price_24h']>50000000000:
            responseList.append(r['market'])
    
#    print(responseList)
    return responseList, responseDict



# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

tickers=[]
tempT=pyupbit.get_tickers(fiat="KRW")
ttt=pyupbit.get_current_price(tempT)
for t in tempT:
    try:
        가격=ttt[t]
        #if 가격>1200:
        if 가격>500:
            tickers.append(t)
    except Exception as e:
        continue

tickers, tickersDic=get_volumeOrder(tickers)
tempT2=[]
for i in range(int(len(tickers))):
    tempT2.append(tickers[i])

tickers.clear()
tickers=tempT2
print(tickers)
'''
업개수=0
다운개수=0
for ticker in tickers:
    cd, bb, ma5=get_bb50(ticker, '5', '20', 20)
    if cd[0]['close']<bb[0]['BM']:
        다운개수+=1
    if cd[0]['close']>bb[0]['BM']:
        업개수+=1
print("업개수", 업개수)
print("다운개수", 다운개수)
'''
체크=False
#print(tickers)
# 자동매매 시작
buyCount=0
sellCount=0
총액=0
매수하한점=9999999999999
매수주문시간={}
주문티커={}
매수봉시간={}
사용가능금액=0 #사용가능한 최대금액
지갑수=3
매수티커리스트=[]
매도하한락={}
최고점={}
최종체크={}
한시간예정고점={}
예상고점돌파={}
중간값={}
손절점={}
임시매수리스트=[]

while True:
    try:
        t_now = datetime.now()
        for ticker in tickers:
            if not ticker in 주문티커:
                주문티커[ticker]=""
            if not ticker in 매수주문시간:
                매수주문시간[ticker]=t_now
            t_min=매수주문시간[ticker]-t_now
            if t_min.total_seconds()<=-1800 and 주문티커[ticker]!="":
                print(주문티커[ticker])
                orderNumList=upbit.get_order(주문티커[ticker])
                if len(orderNumList)>0:
                    for orderNum in orderNumList:
                        if orderNum['side']=='bid':
                            print('삭제')
                            print('임시매수리스트', 임시매수리스트)
                            임시매수리스트.remove(ticker)
                            upbit.cancel_order(orderNum['uuid'])
                주문티커[ticker]=""
                
            if t_min.total_seconds()<=-1801:
                매수주문시간[ticker] = datetime.now()
                주문티커[ticker]=""
            
        if t_now.minute == 11 or t_now.minute == 21 or t_now.minute == 31 or t_now.minute == 41 or t_now.minute == 51 or t_now.minute == 1:
            체크=False
        if (t_now.minute == 10 or t_now.minute == 20 or t_now.minute == 30 or t_now.minute == 40 or t_now.minute == 50 or t_now.minute == 0) and not 체크:
            tickers.clear()
            tempT=pyupbit.get_tickers(fiat="KRW")
            ttt=pyupbit.get_current_price(tempT)
            for t in tempT:
                try:
                    가격=ttt[t]
                    #if 가격>1200:
                    if 가격>500:
                        tickers.append(t)
                except Exception as e:
                    continue
            tickers, tickersDic=get_volumeOrder(tickers)
            tempT2=[]
            for i in range(int(len(tickers))):
                tempT2.append(tickers[i])

            tickers.clear()
            tickers=tempT2
            print(tempT2)
            체크=True
        account=upbit.get_balances()
        
        총액=0
        for ac in account:
            if ac['currency']=='KRW':
                총액+=float(ac['balance'])+float(ac['locked'])
            else:
                총액+=float(ac['avg_buy_price']) * (float(ac['balance'])+float(ac['locked']))
        사용가능금액=총액/지갑수
        매수티커리스트.clear()

        for ac in account:
            if ac['currency']!='KRW':
                매수티커리스트.append('KRW-'+ac['currency'])
        
        if len(account)>=2:
            #여기에 매수매도감시
            for ac in account:
                if ac['currency']=='KRW':
                    if float(ac['locked'])==0:
                        주문티커[ticker]=""
                if ac['currency']!='KRW':
                    ticker='KRW-'+ac['currency']
                    percent=0
                    for td in tickersDic:
                        if td['market']==ticker:
                            #print(td['signed_change_rate'])
                            percent=float(td['signed_change_rate'])*100

                    cd, bb, ma5=get_bb50(ticker, '3', '200', 100)

                    #매도걸기
                    orderbookList=pyupbit.get_orderbook(ticker)
                    매도차이=999999999
                    매도대기=0
                    for hoga in orderbookList['orderbook_units']:
                        if float(hoga['ask_price'])-매도대기<매도차이:
                            매도차이=float(hoga['ask_price'])-매도대기
                        매도대기=float(hoga['ask_price'])
                    
                    #손절점 계산으로 구하기
                    #(cd[0]['close']+매도차이*i) / float(ac['avg_buy_price']) > 1.003
                    #float(ac['avg_buy_price'])*ac['balance'] 매수한 총액
                    수익률=(cd[0]['close']-float(ac['avg_buy_price']))/float(ac['avg_buy_price'])*100
                    
                    매수한총액=float(ac['avg_buy_price']) * (float(ac['balance'])+float(ac['locked']))
                    krw=사용가능금액-매수한총액
                    임시총액=krw*0.9995
                    if ticker in 임시매수리스트:
                        임시매수리스트.remove(ticker)
                    if not ticker in 매도하한락:
                        매도하한락[ticker]=0
                    if not ticker in 최종체크:
                        최종체크[ticker]=False
                    if not ticker in 최고점:
                        최고점[ticker]=0
                    if not ticker in 예상고점돌파:
                        예상고점돌파[ticker]=False
                    if not ticker in 한시간예정고점:
                        예정고점=0
                        for i in range(20):
                            if cd[i]['open'] >= 예정고점:
                                예정고점=cd[i]['open']
                        한시간예정고점[ticker]=예정고점
                    if not ticker in 중간값:
                        중간값[ticker]=cd[1]['open'] + (한시간예정고점[ticker]-cd[1]['open'])/3
                    if 최고점[ticker]<cd[0]['high']:
                        최고점[ticker]=cd[0]['high']

                    if 수익률>0:
                        매도하한락[ticker]=최고점[ticker]-(매도차이*3)

                    if 최고점[ticker] >= 한시간예정고점[ticker]:
                        예상고점돌파[ticker]=True
                    '''
                    orderNumList=upbit.get_order(ticker)
                    if len(orderNumList)<=0:
                        if float(ac['balance'])>0:
                            매도가=한시간예정고점[ticker]
                            print("가격ccc", cd[0]['close'])
                            print("매도가ccc", 매도가)
                            print("avgccc", float(ac['avg_buy_price']))
                            bal = upbit.get_balance(ticker)
                            if bal > 0:
                                upbit.sell_limit_order(ticker, 매도가, bal)
                    '''

                    orderNumList=upbit.get_order(ticker)
                    if len(orderNumList)<=0:
                        차이간격=0
                        for i in range(1000):
                            if 한시간예정고점[ticker]-(매도차이*i) < 중간값[ticker]:
                                차이간격=i
                                break
                        추가필요간격=0
                        for i in range(1000):
                            if (cd[0]['open']+매도차이*i) / cd[0]['open'] > 1.002:
                                추가필요간격=i
                                break
                        차이간격=차이간격-1
                        if 차이간격>0:
                            중간가격=0
                            if cd[0]['close']<float(ac['avg_buy_price']):
                                for i in range(1000):
                                    if cd[0]['close']+매도차이*i >= 중간값[ticker]:
                                        중간가격=cd[0]['close']+매도차이*i
                                        break
                            if cd[0]['close']>=float(ac['avg_buy_price']):
                                for i in range(1000):
                                    if cd[0]['close']-매도차이*i <= 중간값[ticker]:
                                        중간가격=cd[0]['close']-매도차이*i
                                        break
                            bal = upbit.get_balance(ticker)
                            if (float(ac['avg_buy_price']) * bal)/차이간격<10000:
                                if bal > 0:
                                    매도가격 = 중간가격+(매도차이)+(매도차이*추가필요간격)
                                    upbit.sell_limit_order(ticker, 매도가격, bal)
                            else:
                                for i in range(0, 차이간격):
                                    매도가격 = 중간가격+(매도차이*(i+1))+(매도차이*추가필요간격)
                                    if bal > 0:
                                        if (float(ac['avg_buy_price']) * bal)/차이간격<10000:
                                            upbit.sell_limit_order(ticker, 매도가격, bal)
                                        else:
                                            if i==(차이간격-1):
                                                upbit.sell_limit_order(ticker, 매도가격, bal)
                                            else:
                                                upbit.sell_limit_order(ticker, 매도가격, bal/차이간격)
                        else:
                            bal = upbit.get_balance(ticker)
                            if bal > 0:
                                매도가격 = 중간가격+(매도차이)+(매도차이*추가필요간격)
                                upbit.sell_limit_order(ticker, 매도가격, bal)
                    if 매수한총액 < 사용가능금액/2 and 수익률 < 0.2:
                        print(매수한총액, 사용가능금액/2, ticker)
                        #전체 매도
                        #모든 예약 취소하고
                        orderNumList=upbit.get_order(ticker)
                        if len(orderNumList)>0:
                            for orderNum in orderNumList:
                                upbit.cancel_order(orderNum['uuid'])
                        #시장가매도 실행
                        bal = upbit.get_balance(ticker)
                        if bal > 0:
                            upbit.sell_market_order(ticker, bal)
                            print(pyupbit.get_current_price(ticker))
                            print("전매도", ticker)
                            break #잔고 for문


                    #if cd[0]['close']==손절점:
                    #    print(cd[0]['close'], 손절점)
                    if not ticker in 손절점:
                        low=999999999
                        for i in range(20):
                            if cd[i]['low'] < low:
                                low=cd[i]['low']
                        손절점[ticker]=low
                        #손절점[ticker]=float(ac['avg_buy_price'])

                    if cd[0]['open'] > cd[0]['close'] and (cd[1]['high']+cd[0]['low'])/2 <손절점[ticker]:
                        print(cd[0]['close'], 손절점[ticker], ticker)
                        #전체 매도
                        #모든 예약 취소하고
                        orderNumList=upbit.get_order(ticker)
                        if len(orderNumList)>0:
                            for orderNum in orderNumList:
                                upbit.cancel_order(orderNum['uuid'])
                        #시장가매도 실행
                        bal = upbit.get_balance(ticker)
                        if bal > 0:
                            upbit.sell_market_order(ticker, bal)
                            print(pyupbit.get_current_price(ticker))
                            print("손절", ticker)
                            print("손절점",손절점[ticker])
                            break #잔고 for문
        
        #여기에 첫매수감시
        for ticker in tickers:
            if not ticker in 주문티커:
                주문티커[ticker]=""
            if 주문티커[ticker]=="":

                percent=0
                for td in tickersDic:
                    if td['market']==ticker:
                        #print(td['signed_change_rate'])
                        percent=float(td['signed_change_rate'])*100
                        #print(ticker, percent)
                cd, bb, ma5=get_bb50(ticker, '3', '200', 100)
                if cd[3]['low']<bb[3]['BL'] and cd[1]['low']>cd[3]['low'] and cd[2]['open']<cd[2]['close'] and cd[2]['open']>bb[2]['BL'] and cd[2]['close']<bb[2]['BM']:
                    if cd[1]['open']<cd[1]['close']:
                        krw=0
                        if ticker in 매수티커리스트:
                            break


                        예정고점=0
                        for i in range(len(bb)):
                            if i>20:
                                break
                            if cd[i]['open'] >= 예정고점:
                                예정고점=cd[i]['open']
                        
                        #손절점찾기
                        low=999999999
                        진입=False
                        for j in range(1, len(bb)):
                            if 진입==False and cd[j]['low']<bb[j]['BL']:
                                진입=True
                            if 진입 and cd[j]['low']>bb[j]['BL']:
                                break
                            if cd[j]['low']<bb[j]['BL'] and 진입:
                                if low > cd[j]['low']:
                                    low=cd[j]['low']

                        #고점이 현재보다 높을때만 사기
                        if 예정고점/cd[1]['open'] < 1.011:
                            break
                        print('매수티커리스트', 매수티커리스트)
                        print('임시매수리스트', 임시매수리스트)
                        if len(매수티커리스트)+len(임시매수리스트)<지갑수:
                            if 사용가능금액 > 6000:
                                #print(upbit.buy_market_order(ticker, 6000))
                                매수봉시간[ticker]=cd[0]['time']
                                
                                print(upbit.buy_limit_order(ticker, cd[1]['open'], 사용가능금액*0.9995/cd[1]['open']))
                                t_now = datetime.now()
                                매수주문시간[ticker]=t_now
                                주문티커[ticker]=ticker
                                매수하한점=cd[2]['low']
                                print("첫매수:", ticker, cd[1]['open'])
                                #print("손절가", 손절점)
                                손절점[ticker]=low
                                한시간예정고점[ticker]=예정고점
                                중간값[ticker]= cd[1]['open'] + (예정고점-cd[1]['open'])/2
                                예상고점돌파[ticker]=False
                                매수티커리스트.append(ticker)
                                임시매수리스트.append(ticker)
                                매도하한락[ticker]=0
                                최고점[ticker]=0
                                최종체크[ticker]=False
                                break
                            else:
                                print("사용가능금액부족! 사용가능금액:", 사용가능금액)
        time.sleep(0.5)
    except Exception as e:
        print("에러", e)
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


