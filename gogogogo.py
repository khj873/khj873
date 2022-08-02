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
import pickle
import decimal

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
        if 가격>200:
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
나누는수=30
지갑수=3
매수티커리스트=[]
매도하한락={}
최고점={}
임시매수리스트=[]
매도걸은아이디=[]
한시간단위금액=0
매수딕셔너리={}
프린트회수=0
최저수익률=10000
시작시간=datetime.now().hour
try:
    with open('dictsave.p', 'rb') as file:
        매수딕셔너리=pickle.load(file)
        print(매수딕셔너리)
except Exception as e:
    print("에러", e)
for ticker in tickers:
    if ticker in 매수딕셔너리:
        for dic in 매수딕셔너리[ticker]:
            if dic[4]:
                print("제거", ticker, dic)
                매수딕셔너리[ticker].remove(dic)
while True:
    try:
        t_now = datetime.now()

        for ticker in tickers: #아직 사지 않은 티커체크하는 곳
            dddd=upbit.get_order(ticker, state="done", page=1)
            if len(dddd)>0:
                if dddd[0]['side']=='ask': #매도완료
                    if ticker in 매수딕셔너리:
                        for 리스트 in 매수딕셔너리[ticker]: #매수아이디, 매수가격, 매수금액, 매수량, 매도걸었는지 판단
                            if 리스트[4]==True: #([dddd[0]['uuid'], dddd[0]['price'], 0, dddd[0]['volume'], False])
                                지운매수가격 = float(리스트[1])
                                지운매도가격 = float(리스트[2])
                                지운매수수수료 = 지운매수가격 - (지운매수가격*0.9995)
                                지운매도수수료 = 지운매도가격 - (지운매도가격*0.9995)
                                uuid=리스트[0]
                                매수딕셔너리[ticker].remove(리스트)
                                #리스트에서 제거하고, 남아있는 리스트에서 최소값을 찾아 매수가격 차감하기
                                if len(매수딕셔너리[ticker])>=1:
                                    최소가격=매수딕셔너리[ticker][0][1]
                                    for 리스트2 in 매수딕셔너리[ticker]:#딕셔너리 내 최소가격찾기
                                        if float(리스트2[1]) <= 최소가격:
                                            최소가격=float(리스트2[1])
                                            uuid=리스트2[0]
                                    for 리스트2 in 매수딕셔너리[ticker]:#최소가격 해당 uid찾기
                                        if 리스트2[0]==uuid:
                                            print("변경 전 리스트:", 리스트2)
                                            리스트2[1] = float(리스트2[1]) - ( 지운매도가격 - 지운매수가격 - 지운매수수수료 - 지운매도수수료) #이득금액을 다음 가격에서 빼줌
                                            print("변경 후 리스트:", 리스트2)
                                            break
                                with open('dictsave.p', 'wb') as file:
                                    pickle.dump( 매수딕셔너리,file)
                                break

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
                    if 가격>200:
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
        남은금액=0
        걸려있는금액=0
        수익률가장낮은티커=''
        for ac in account:
            if ac['currency']=='KRW':
                총액+=float(ac['balance'])+float(ac['locked'])
                남은금액=float(ac['balance'])+float(ac['locked'])
            else:
                총액+=float(ac['avg_buy_price']) * (float(ac['balance'])+float(ac['locked']))
                걸려있는금액+=float(ac['avg_buy_price']) * (float(ac['balance'])+float(ac['locked']))
        사용가능금액=총액
        매수티커리스트.clear()
        if 한시간단위금액==0:
            한시간단위금액=총액

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
                    if 최저수익률>수익률:
                        최저수익률=수익률
                        수익률가장낮은티커=ticker
                    매수한총액=float(ac['avg_buy_price']) * (float(ac['balance'])+float(ac['locked']))
                    krw=사용가능금액-매수한총액
                    임시총액=krw*0.9995
                    if not ticker in 매도하한락:
                        매도하한락[ticker]=0
                    if not ticker in 최고점:
                        최고점[ticker]=0
                    if 최고점[ticker]<cd[0]['high']:
                        최고점[ticker]=cd[0]['high']
                

                    #매수가격 알아내기
                    dddd=upbit.get_order(ticker, state="done", page=1)
                    for dd in dddd:
                        if dd['side']=='bid':
                            if not ticker in 매수딕셔너리: #매수딕셔너리ticker가 아예 없다면
                                매수리스트=[]
                                매수리스트.append([dd['uuid'], float(dd['price']), 0,  decimal.Decimal(dd['executed_volume']), False]) #매수아이디, 매수가격, 매도가격, 매수량, 매도걸었는지 판단
                                매수딕셔너리[ticker]=매수리스트
                                최고점[ticker]=cd[0]['close']
                                #매수딕셔너리 저장
                                with open('dictsave.p', 'wb') as file:
                                    pickle.dump( 매수딕셔너리,file)
                                print(ticker,매수딕셔너리[ticker])
                            else:
                                같은게있는가=False
                                for dict in 매수딕셔너리[ticker]: #매수딕셔너리는 있다면 중복되는지 검사
                                    if dict[0]==dd['uuid']:
                                        같은게있는가=True
                                if not 같은게있는가:
                                    매수리스트=매수딕셔너리[ticker]
                                    매수리스트.append([dd['uuid'], float(dd['price']), 0, decimal.Decimal(dd['executed_volume']), False]) #매수아이디, 매수가격, 매도가격, 매수량, 매도걸었는지 판단
                                    매수딕셔너리[ticker]=매수리스트
                                    최고점[ticker]=cd[0]['close']
                                    #매수딕셔너리 저장
                                    with open('dictsave.p', 'wb') as file:
                                        pickle.dump( 매수딕셔너리,file)
                                    print('------------------')
                                    for a in 매수딕셔너리[ticker]:
                                        print(ticker, a)
                                    print('------------------')
                            break

                    if not ticker in 매수딕셔너리: #매수딕셔너리ticker가 아예 없다면
                        print(ticker, '??이상하다')
                        print(매수딕셔너리)
                        break

                    uuid=''
                    최소가격=float(매수딕셔너리[ticker][0][1])
                    for 리스트 in 매수딕셔너리[ticker]:#딕셔너리 내 최소가격찾기
                        if float(리스트[1]) <= 최소가격:
                            최소가격=float(리스트[1])
                            uuid=리스트[0]
                    
                    for 리스트 in 매수딕셔너리[ticker]:#최소가격 해당 uid찾기
                        if 리스트[0]==uuid:
                            매수가격=float(리스트[1])
                            이득발생가격 = cd[0]['close']-매수가격-(매수가격-(매수가격*0.9995)) - (cd[0]['close']- (cd[0]['close']*0.9995))
                            최소이득가 = 매수가격 + (매수가격 - (매수가격*0.9995)) +  (cd[0]['close'] - (cd[0]['close']*0.9995)) + (매수가격*0.002)
                            이득도달선 = 매수가격 + (매수가격 - (매수가격*0.9995)) +  (cd[0]['close'] - (cd[0]['close']*0.9995)) + (매수가격*0.004)

                            #매도조건입력 - 최소이득가 이상이고, 최근 양봉에서 거래량 가장 높은 양봉의 저가 미만으로 내려가면 일반매도걸기. 최소이득가 아래로 내려가면 시장가매도
                            
                            #먼저, 최소이득가 호가찾기
                            최소이득호가=0
                            for i in range(1000):
                                if cd[0]['close'] < 최소이득가:
                                    if cd[0]['close'] + (매도차이*i) > 최소이득가:
                                        최소이득호가 = cd[0]['close'] + (매도차이*(i))
                                        break
                                else:
                                    if cd[0]['close'] - (매도차이*i) < 최소이득가:
                                        최소이득호가 = cd[0]['close'] - (매도차이*(i))
                                        break
                            최소이득선=0
                            for i in range(1000):
                                if cd[0]['close'] < 이득도달선:
                                    if cd[0]['close'] + (매도차이*i) > 이득도달선:
                                        최소이득선 = cd[0]['close'] + (매도차이*(i))
                                        break
                                else:
                                    if cd[0]['close'] - (매도차이*i) < 이득도달선:
                                        최소이득선 = cd[0]['close'] - (매도차이*(i))
                                        break
                            if not 리스트[4]:
                                print( ticker,"최소이득선", 최소이득선,"최소이득호가", 최소이득호가, "최고점",최고점[ticker], "매수가격",매수가격, "현재가격", cd[0]['close'])
                            
                            if 리스트[4] == False:
                                if 수익률<-1.5:
                                    if cd[0]['close'] < 최소이득호가:
                                        #걸려있는 모든 매도 취소
                                        orderNumList=upbit.get_order(ticker)
                                        if len(orderNumList)>0:
                                            for orderNum in orderNumList:
                                                upbit.cancel_order(orderNum['uuid'])
                                        #시장가매도 실행
                                        print("시장가매도", ticker, decimal.Decimal(리스트[3]))
                                        if 매수한총액 - cd[0]['close']*float(리스트[3])<5500:
                                            bal=upbit.get_balance(ticker)
                                            upbit.sell_market_order(ticker, bal)
                                        else:
                                            upbit.sell_market_order(ticker, decimal.Decimal(리스트[3]))
                                        for 전체리스트 in 매수딕셔너리[ticker]:
                                            전체리스트[2] = cd[0]['close']
                                            전체리스트[4] = True
                                        del 최고점[ticker]

                                if 최고점[ticker] > 최소이득선 and 최소이득호가!=0:
                                    #매도걸은 거래인지 확인해야함

                                    if cd[0]['close'] < 최소이득호가:
                                        #걸려있는 모든 매도 취소
                                        orderNumList=upbit.get_order(ticker)
                                        if len(orderNumList)>0:
                                            for orderNum in orderNumList:
                                                upbit.cancel_order(orderNum['uuid'])
                                        #시장가매도 실행
                                        print("시장가매도", ticker, decimal.Decimal(리스트[3]))
                                        if 매수한총액 - cd[0]['close']*float(리스트[3])<5500:
                                            bal=upbit.get_balance(ticker)
                                            upbit.sell_market_order(ticker, bal)
                                        else:
                                            upbit.sell_market_order(ticker, decimal.Decimal(리스트[3]))
                                        리스트[2] = cd[0]['close']
                                        리스트[4] = True
                                        del 최고점[ticker]

                                    #손해매도
                                    if cd[0]['low'] == 최소이득호가:
                                        print("매도실행1", ticker, 리스트)
                                        if 매수한총액 - cd[0]['close']*float(리스트[3])<5500:
                                            bal=upbit.get_balance(ticker)
                                            upbit.sell_limit_order(ticker, 최소이득호가, bal)
                                        else:
                                            upbit.sell_limit_order(ticker, 최소이득호가, decimal.Decimal(리스트[3]))
                                        리스트[2] = 최소이득호가
                                        리스트[4] = True
                                        del 최고점[ticker]
                                    #이득매도
                                    if cd[0]['close'] > 최소이득호가:
                                        거래량최고봉=0
                                        for i in range(1, len(cd)):
                                            if cd[i]['open'] < cd[i]['close']: #양봉검색됨
                                                양봉거래량=cd[i]['vol']
                                                거래량최고봉=i
                                                for j in range(i+1, len(cd)):
                                                    if cd[j]['open'] > cd[j]['close']: #음봉이면 검색종료
                                                        break
                                                    if cd[j]['open'] < cd[j]['close']: #양봉거래량 비교
                                                        if 양봉거래량 < cd[j]['vol']:
                                                            양봉거래량 = cd[j]['vol']
                                                            거래량최고봉=j
                                                break
                                        if cd[거래량최고봉]['low'] > cd[0]['close']:
                                            print("매도실행2", ticker, cd[0]['close'], 리스트)
                                            if 매수한총액 - cd[0]['close']*float(리스트[3])<5500:
                                                bal=upbit.get_balance(ticker)
                                                upbit.sell_limit_order(ticker, cd[0]['close'], bal)
                                            else:
                                                upbit.sell_limit_order(ticker, cd[0]['close'], decimal.Decimal(리스트[3]))
                                            리스트[2] = cd[0]['close']
                                            리스트[4] = True
                                            del 최고점[ticker]
                                            
                            break


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

                매수선=0
                매수제한봉=0
                for i in range(1, len(bb)):
                    if cd[i]['open']>cd[i]['close']: #음봉 발견
                        if cd[i]['low']<bb[i]['BL']:
                            거래량=cd[i]['vol']
                            매수선=cd[i]['high']
                            매수제한봉=i
                            for j in range(i+1, len(bb)): #음봉 무리 중에 가장 큰 거래량 찾기
                                if cd[j]['low'] > bb[j]['BL']:
                                    break
                                if cd[j]['open']<cd[j]['close']: #양봉이면 검색 종료
                                    break
                                else:
                                    if 거래량<cd[j]['vol']:
                                        거래량=cd[j]['vol']
                                        매수선=cd[j]['high']
                                        매수제한봉=j
                                    else:
                                        break
                            break
                        else:
                            break

                if cd[2]['low'] > ma5[2] and cd[1]['low'] < ma5[1] and cd[1]['close'] < cd[1]['open'] and cd[1]['open'] > ma5[1] and cd[0]['close'] > ma5[0] and ma5[4] < ma5[2]:
                    if 사용가능금액/나누는수 > 6000:
                        if not ticker in 매수봉시간:
                            매수봉시간[ticker]=0
                        if 매수봉시간[ticker] != cd[0]['time']:
                            if 남은금액<사용가능금액/나누는수*0.9995:
                                for 리스트 in 매수딕셔너리[수익률가장낮은티커]:
                                    upbit.sell_market_order(ticker, decimal.Decimal(리스트[3]))
                                    리스트[2] = cd[0]['close']
                                    리스트[4] = True
                                    del 최고점[ticker]


                            upbit.buy_limit_order(ticker, cd[0]['close'], 사용가능금액/나누는수*0.9995/cd[0]['close'])
                            매수봉시간[ticker]=cd[0]['time']
                            print("매수실행", ticker, cd[0]['close'])
                    else:
                        print("사용가능금액부족! 사용가능금액/15:", 사용가능금액/나누는수)

                if cd[0]['low'] > 매수선 and 매수선!=0:
                    if 사용가능금액/나누는수 > 6000:
                        if not ticker in 매수봉시간:
                            매수봉시간[ticker]=0
                        if 매수봉시간[ticker] != cd[0]['time']:
                            if 남은금액<사용가능금액/나누는수*0.9995:
                                for 리스트 in 매수딕셔너리[수익률가장낮은티커]:
                                    upbit.sell_market_order(ticker, decimal.Decimal(리스트[3]))
                                    리스트[2] = cd[0]['close']
                                    리스트[4] = True
                                    del 최고점[ticker]

                            upbit.buy_limit_order(ticker, cd[0]['close'], 사용가능금액/나누는수*0.9995/cd[0]['close'])
                            매수봉시간[ticker]=cd[0]['time']
                            print("매수실행", ticker, cd[0]['close'])
                    else:
                        print("사용가능금액부족! 사용가능금액/15:", 사용가능금액/나누는수)
        수익률가장낮은티커=''
        최저수익률=10000
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


