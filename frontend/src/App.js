import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [trades, setTrades] = useState([]);

  useEffect(() => {
    fetchTrades();
  }, []);

  const fetchTrades = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/trades');
      const data = await response.json();
      setTrades(data);
    } catch (error) {
      console.error("데이터 로딩 실패:", error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        {/* 닉네임을 삭제하고 깔끔하게 변경했습니다 */}
        <h1>📊 Trading Bot Dashboard</h1> 
        
        <div style={{ marginBottom: '20px' }}>
          <button onClick={fetchTrades} style={{ padding: '10px 20px', cursor: 'pointer' }}>
            새로고침
          </button>
        </div>

        <table style={{ width: '90%', borderCollapse: 'collapse', backgroundColor: '#282c34', color: 'white' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #61dafb' }}>
              <th>시간</th>
              <th>종목</th>
              <th>유형</th>
              <th>가격</th>
              <th>수익률</th>
              <th>사유</th>
            </tr>
          </thead>
          <tbody>
            {trades.length > 0 ? (
              trades.map((trade, index) => (
                <tr key={index} style={{ borderBottom: '1px solid #444' }}>
                  <td>{trade.timestamp}</td>
                  <td>{trade.symbol}</td>
                  <td style={{ color: trade.type === 'BUY' ? '#ff4d4d' : '#4d79ff', fontWeight: 'bold' }}>
                    {trade.type}
                  </td>
                  <td>{trade.price.toLocaleString()}</td>
                  <td style={{ color: trade.profit_rate > 0 ? '#ff4d4d' : '#4d79ff' }}>
                    {trade.profit_rate}%
                  </td>
                  <td>{trade.reason}</td>
                </tr>
              ))
            ) : (
              <tr><td colSpan="6" style={{ padding: '20px' }}>매매 기록을 불러오는 중이거나 기록이 없습니다.</td></tr>
            )}
          </tbody>
        </table>
      </header>
    </div>
  );
}

export default App;