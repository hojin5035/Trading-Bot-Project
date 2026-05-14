# 📈 Trading-Bot-Project
> **"수익 0원은 시스템의 침묵이지만, 손실 0원은 시스템의 승리다."**
> 리스크 관리(MDD) 최적화 및 3-Tier 아키텍처 기반의 안정 지향형 퀀트 시스템

## 💡 프로젝트 철학
단순한 고수익보다는 **'고통 없는 수익(Risk-Adjusted Return)'**을 지향합니다. 시장의 광기 속에서도 계좌를 보호하기 위해 통계적 지표($MDD$, $Sharpe\ Ratio$)를 기반으로 전략을 동적으로 최적화하며, 기술적 분석의 노이즈를 필터링합니다.

---

## 📅 개발 일지 (Evolution Log)

### 1단계: 노이즈 필터링 및 기초 모델
* **Issue:** 가짜 반등에 의한 잦은 손절 및 거래 수수료 손실 발생
* **Solution:** 거래량 폭증(Volume Spike) 3.6배 임계값 도입을 통한 진입 필터링 강화

### 2단계: 추세 추종 및 방어 체계 구축
* **Logic:** $EMA9$ 및 $RSI$ 지표 조합을 통한 추세 확증
* **Defense:** 0.5% 트레일링 스탑($Trailing\ Stop$) 및 최근 매매 결과에 따른 동적 레버리지 조절 로직 도입

### 3단계: 전략 최적화 엔진의 진화 (현재)
* **Strategy:** 단순 수익률 기반 채택에서 **리스크 지표 기반 최적화**로 전환
* **Optimization:** 
    * **$MDD$(최대 낙폭) 최소화**: 자산 고점 대비 하락 폭을 계산하여 파산 위험 방어
    * **칼마 비율($Calmar\ Ratio$)**: 고통 대비 수익 성능이 검증된 전략 우선 채택
    * **전진 분석(Walk-forward)**: 과거 데이터 오버피팅 방지를 위한 데이터 블렌딩 검증

### 4단계: 시스템 통합 및 실시간 모니터링
* **Architecture:** 
    * **Engine**: Python 기반 고성능 트레이딩 엔진
    * **Dashboard**: React 기반 실시간 자산 및 전략 변동성 시각화
    * **Backend**: Java/Spring Boot 기반 매매 로그 DB 아카이빙 및 스케줄링 동기화

---

## 🛠️ Tech Stack

### 🌀 Core Engine
- **Language:** Python 3.x
- **Library:** CCXT (Exchange API), Pandas (Data Analysis), FastAPI
- **Model:** Gemini 3.1 Flash (Market Analysis & Strategy Advice)

### 🖥️ Monitoring & Backend
- **Frontend:** React.js, Tailwind CSS, Recharts (Real-time Dashboard)
- **Backend:** Java 17, Spring Boot, Spring Data JPA
- **Database:** MySQL / MariaDB (Transaction Archiving)
- **Alert:** Discord Webhook

---

## 📊 Core Strategy Metrics
시스템의 안정성을 평가하기 위해 다음의 수식을 최적화 지표로 활용합니다.

* **최대 낙폭 (MDD):**
$$MDD = \frac{Trough\ Value - Peak\ Value}{Peak\ Value}$$

* **샤프 지수 (Sharpe Ratio):**
$$Sharpe = \frac{R_p - R_f}{\sigma_p}$$

---

## 🚀 시작하기
1. **Trading Engine**: `python main_bot.py` 실행 (CSV 로깅 시작)
2. **Analysis API**: `uvicorn main_api:app` 실행 (데이터 분석 및 AI 서빙)
3. **Data Backend**: IntelliJ에서 `TradingBackendApplication` 실행 (5분 주기 DB 동기화)
4. **Frontend**: `npm start` (대시보드 접속)

---

**개발자:** 김호진 (Computer Science & Engineering)  
**업데이트:** 2026. 05.