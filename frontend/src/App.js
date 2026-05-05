import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid, Legend } from 'recharts';
import './App.css';

function App() {
  const [trades, setTrades] = useState([]);
  const [botInfo, setBotInfo] = useState({
    botStatus: "연결 확인 중",
    currentSeed: 0,
    coinStats: []
  });
  const [prices, setPrices] = useState({ BTC: '0', ETH: '0', SOL: '0', XRP: '0' });
  const [activeTab, setActiveTab] = useState(1);

  useEffect(() => {
    document.title = "Hojin's Trading Bot";
    
    const updateAllData = () => {
      fetchTrades();
      fetchBotStatus();
      fetchPrices();
    };

    updateAllData();
    const interval = setInterval(updateAllData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchTrades = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/trades');
      const data = await response.json();
      // 만약 데이터가 배열이 아니면 빈 배열로 강제 설정
      setTrades(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("로그 로딩 실패:", error);
      setTrades([]);
    }
  };

  const fetchBotStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/status');
      const data = await response.json();
      // 기존 botInfo 구조를 유지하면서 데이터 덮어쓰기
      setBotInfo(prev => ({
        ...prev,
        ...data,
        coinStats: Array.isArray(data?.coinStats) ? data.coinStats : []
      }));
    } catch (error) {
      console.error("봇 상태 로딩 실패:", error);
    }
  };

  const fetchPrices = async () => {
    try {
      const symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT'];
      const newPrices = {};
      for (const sym of symbols) {
        const res = await fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${sym}`);
        const data = await res.json();
        if (data.price) {
          newPrices[sym.replace('USDT', '')] = parseFloat(data.price).toLocaleString();
        }
      }
      setPrices(prev => ({ ...prev, ...newPrices }));
    } catch (error) {
      console.error("시세 갱신 실패:", error);
    }
  };

  // trades가 배열인지 한 번 더 확인 후 뒤집기
  const reversedTrades = Array.isArray(trades) ? [...trades].reverse() : [];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{ backgroundColor: '#1e1e24', border: '1px solid #61dafb', padding: '5px 8px', borderRadius: '4px', fontSize: '11px' }}>
          {payload.map((p, idx) => (
            <p key={idx} style={{ margin: 0, color: p.color }}>
              {p.name}: {activeTab === 2 ? `${(p.value || 0)}%` : `$${Math.abs(p.value || 0).toLocaleString()}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div style={{ backgroundColor: '#1e1e24', color: '#fff', minHeight: '100vh', padding: '20px', fontFamily: 'sans-serif', overflow: 'hidden' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #444', paddingBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <h2 style={{ margin: 0, color: '#61dafb', fontWeight: 'bold' }}>트레이딩 봇</h2>
          <span style={{ backgroundColor: '#2ecc71', color: '#000', padding: '2px 10px', borderRadius: '4px', fontSize: '13px', fontWeight: 'bold' }}>
            {botInfo?.botStatus || "상태 확인 중"}
          </span>
        </div>
        <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
          현재 자산: <span style={{ color: '#f1c40f' }}>${(botInfo?.currentSeed || 0).toLocaleString()}</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '20px', height: '480px' }}>
        <div style={{ flex: '0.6', backgroundColor: '#282c34', borderRadius: '12px', padding: '15px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px', marginBottom: '15px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              {[1, 2, 3].map(num => (
                <button key={num} onClick={() => setActiveTab(num)}
                  style={{
                    width: '35px', height: '35px', backgroundColor: activeTab === num ? '#61dafb' : '#1e1e24',
                    color: activeTab === num ? '#000' : '#fff', border: 'none', borderRadius: '8px',
                    cursor: 'pointer', fontWeight: 'bold', fontSize: '14px'
                  }}>{num}</button>
              ))}
            </div>
            <span style={{ fontSize: '12px', color: '#aaa', fontWeight: 'bold' }}>
              {activeTab === 1 ? "최근 매매 기록" : activeTab === 2 ? "수익률 추이" : "종목별 수익/손실 비교"}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: activeTab === 1 ? 'auto' : 'hidden' }}>
            {activeTab === 1 && (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead style={{ position: 'sticky', top: 0, backgroundColor: '#333', zIndex: 1 }}>
                  <tr>
                    <th style={{ padding: '10px' }}>날짜/시간</th>
                    <th>종목</th>
                    <th>유형</th>
                    <th>가격</th>
                    <th>수익률</th>
                    <th>사유</th>
                  </tr>
                </thead>
                <tbody>
                  {reversedTrades.length > 0 ? reversedTrades.map((t, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #3e4451', textAlign: 'center' }}>
                      <td style={{ padding: '10px', color: '#ccc' }}>{t?.timestamp || '-'}</td>
                      <td style={{ fontWeight: 'bold' }}>{t?.symbol || '-'}</td>
                      <td style={{ color: t?.type === 'BUY' ? '#ff4d4d' : '#4d79ff' }}>{t?.type || '-'}</td>
                      <td>{(t?.price || 0).toLocaleString()}</td>
                      <td style={{ color: (t?.profit_rate || 0) > 0 ? '#ff4d4d' : '#4d79ff' }}>{t?.profit_rate || 0}%</td>
                      <td style={{ fontSize: '12px', color: '#999' }}>{t?.reason || '-'}</td>
                    </tr>
                  )) : <tr><td colSpan="6" style={{padding:'20px'}}>데이터가 없습니다.</td></tr>}
                </tbody>
              </table>
            )}

            {(activeTab === 2 || activeTab === 3) && (
              <ResponsiveContainer width="100%" height="100%">
                {activeTab === 2 ? (
                  <LineChart data={trades}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" vertical={false} />
                    <XAxis dataKey="timestamp" hide />
                    <YAxis fontSize={12} stroke="#888" />
                    <Tooltip content={<CustomTooltip />} isAnimationActive={false} />
                    <ReferenceLine y={0} stroke="#ff4d4d" strokeDasharray="3 3" />
                    <Line type="linear" dataKey="profit_rate" name="수익률" stroke="#61dafb" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} isAnimationActive={false} />
                  </LineChart>
                ) : (
                  <BarChart data={botInfo?.coinStats || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" vertical={false} />
                    <XAxis dataKey="name" fontSize={12} stroke="#888" />
                    <YAxis fontSize={12} stroke="#888" />
                    <Tooltip cursor={false} content={<CustomTooltip />} isAnimationActive={false} />
                    <Legend verticalAlign="top" align="right" iconType="rect" wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} />
                    <Bar dataKey="totalProfit" fill="#ff4d4d" name="누적 수익" radius={[2, 2, 0, 0]} barSize={20} isAnimationActive={false} />
                    <Bar dataKey="totalLoss" fill="#4d79ff" name="누적 손실" radius={[2, 2, 0, 0]} barSize={20} isAnimationActive={false} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div style={{ flex: '0.4', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {botInfo?.coinStats?.length > 0 ? botInfo.coinStats.map((coin, idx) => (
            <div key={idx} style={{ 
              flex: 1, backgroundColor: '#282c34', borderRadius: '12px', padding: '12px', 
              display: 'flex', flexDirection: 'column', justifyContent: 'center',
              borderLeft: `4px solid ${coin?.status === '보유중' ? '#ff4d4d' : '#444'}` 
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '16px', fontWeight: 'bold', color: '#61dafb' }}>{coin?.name || '종목명'}</span>
                <span style={{ fontSize: '12px', color: coin?.status === '보유중' ? '#ff4d4d' : '#aaa' }}>{coin?.status || '분석중'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '13px', color: '#eee', marginBottom: '10px' }}>
                <div style={{ flex: 1 }}>승률 {coin?.winRate || '0%'}</div>
                <div style={{ flex: 1, textAlign: 'center' }}>레버리지 {coin?.lev || '1x'}</div>
                <div style={{ flex: 1, textAlign: 'right' }}>비중 {coin?.dist || '0%'}</div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#fff', borderTop: '1px solid #3e4451', paddingTop: '8px' }}>
                <div style={{ flex: 1 }}>변동성 {coin?.vol || '0'}</div>
                <div style={{ flex: 1, textAlign: 'center' }}>추적손절 {coin?.ts || '0'}</div>
                <div style={{ flex: 1, textAlign: 'right' }}>익절기준 {coin?.profit || '0'}</div>
              </div>
            </div>
          )) : <div style={{textAlign:'center', paddingTop:'50px'}}>전략 데이터를 불러오는 중...</div>}
        </div>
      </div>

      <div style={{ marginTop: '20px', display: 'flex', gap: '20px' }}>
        <div style={{ flex: '0.6', padding: '12px', backgroundColor: '#282c34', borderRadius: '10px', display: 'flex', justifyContent: 'space-around', fontSize: '13px', fontWeight: 'bold' }}>
          <span>BTC <span style={{color:'#ff4d4d', marginLeft:'5px'}}>${prices?.BTC || '0'}</span></span>
          <span>ETH <span style={{color:'#4d79ff', marginLeft:'5px'}}>${prices?.ETH || '0'}</span></span>
          <span>SOL <span style={{color:'#ff4d4d', marginLeft:'5px'}}>${prices?.SOL || '0'}</span></span>
          <span>XRP <span style={{color:'#aaa', marginLeft:'5px'}}>${prices?.XRP || '0'}</span></span>
        </div>
        <div style={{ flex: '0.4', padding: '12px', backgroundColor: '#282c34', borderRadius: '10px', display: 'flex', justifyContent: 'space-around', fontSize: '12px', color: '#aaa', alignItems: 'center' }}>
          <span>Github: <span style={{color: '#fff'}}>github.com/hojin5035</span></span>
          <span>Contact: <span style={{color: '#fff'}}>hojin5035@naver.com</span></span>
          <span style={{ borderLeft: '1px solid #444', paddingLeft: '15px' }}>v1.1.1 - 2026</span>
        </div>
      </div>
    </div>
  );
}

export default App;