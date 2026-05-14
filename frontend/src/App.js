import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  AreaChart, Area, CartesianGrid
} from 'recharts';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "./components/ui/card";
import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "./components/ui/tabs";
import {  Mail, Activity, TrendingUp, BarChart3, Settings } from "lucide-react";
import { FaGithub } from "react-icons/fa";
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState("1");
  const [aiComment, setAiComment] = useState("AI 분석 버튼을 눌러보세요.");
  const [loading, setLoading] = useState(false);
  const [equity, setEquity] = useState([]);
  const [trades, setTrades] = useState([]);
  const [prices, setPrices] = useState({ BTC: '0', ETH: '0', SOL: '0', XRP: '0' });
  const [botInfo, setBotInfo] = useState({
    botStatus: "연결 확인 중",
    currentSeed: 0,
    coinStats: []
  });

  // 데이터 페칭 로직 (기존 유지)
  useEffect(() => {
    document.title = "Trading Bot Dashboard";
    const updateAllData = () => {
      fetchTrades();
      fetchBotStatus();
      fetchPrices();
      fetchEquity();
    };
    updateAllData();
    const interval = setInterval(updateAllData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchAI = async (mode) => {
    setLoading(true);
    setAiComment("분석 중...");
    try {
      const response = await fetch(`http://localhost:8000/api/ai/${mode}`);
      console.log(response)
      const data = await response.json();
      setAiComment(data.result);
    } catch (error) {
      setAiComment("에러: 서버 연결을 확인하세요.");
    }
    setLoading(false);
  };

// 1. 자산 데이터 복구
const fetchEquity = async () => {
  try {
    const res = await fetch("http://localhost:8000/api/equity");
    const data = await res.json();
    setEquity(Array.isArray(data) ? data : []);
  } catch (e) {
    console.error("equity 로딩 실패", e);
  }
};

// 2. 매매 기록 데이터 복구
const fetchTrades = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/trades');
    const data = await response.json();
    setTrades(Array.isArray(data) ? data : []);
  } catch (error) {
    console.error("로그 로딩 실패:", error);
    setTrades([]);
  }
};

// 3. 봇 상태 데이터 복구
const fetchBotStatus = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/status');
    const data = await response.json();
    console.log(data)
    setBotInfo(prev => ({
      ...prev,
      ...data,
      coinStats: Array.isArray(data?.coinStats) ? data.coinStats : []
    }));
  } catch (error) {
    console.error("봇 상태 로딩 실패:", error);
  }
};

// 4. 시세 데이터 복구
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

  const reversedTrades = Array.isArray(trades) ? [...trades].reverse() : [];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/90 border border-white/10 p-3 rounded-lg shadow-xl backdrop-blur-sm text-[11px]">
          {payload.map((p, idx) => (
            <p key={idx} style={{ color: p.color }} className="m-0 font-medium font-mono">
              {p.name}: {activeTab === "2" ? `${p.value}%` : `$${Math.abs(p.value).toLocaleString()}`}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white p-6 font-sans selection:bg-white selection:text-black">
      
      {/* HEADER SECTION */}
      <header className="flex justify-between items-center mb-8 pb-4 border-b border-white/5">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold tracking-tighter text-white uppercase italic">Hojin_System v0.1</h1>
          <Badge className={`${botInfo?.botStatus === '운영중' ? 'bg-white text-black' : 'bg-zinc-800 text-zinc-400'} border-none px-3 font-bold`}>
            {botInfo?.botStatus || "OFFLINE"}
          </Badge>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] text-zinc-500 uppercase tracking-widest mb-1 font-bold">Total Equity</span>
          <span className="text-2xl font-mono font-bold tracking-tighter italic">
            ${(botInfo?.currentSeed || 0).toLocaleString()}
          </span>
        </div>
      </header>

      {/* MAIN LAYOUT: 7:5 Ratio */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-stretch">
        
        {/* LEFT PANEL: Table & Chart (col-span-7) */}
        <div className="xl:col-span-7 flex flex-col gap-6">
          <Card className="bg-zinc-900/50 border-white/5 shadow-2xl backdrop-blur-md overflow-hidden flex-1 flex flex-col">
            <CardHeader className="flex flex-row items-center justify-between pt-3 pb-3 border-b border-white/5 bg-white/[0.01]">
              <Tabs defaultValue="1" className="w-full" onValueChange={setActiveTab}>
                <div className="flex justify-between items-center">
                  <TabsList className="bg-black/40 border border-white/5">
                    <TabsTrigger value="1" className="data-[state=active]:bg-white data-[state=active]:text-black"><Activity size={14} className="mr-2"/>기록</TabsTrigger>
                    <TabsTrigger value="2" className="data-[state=active]:bg-white data-[state=active]:text-black"><TrendingUp size={14} className="mr-2"/>수익</TabsTrigger>
                    <TabsTrigger value="3" className="data-[state=active]:bg-white data-[state=active]:text-black"><BarChart3 size={14} className="mr-2"/>비교</TabsTrigger>
                    <TabsTrigger value="4" className="data-[state=active]:bg-white data-[state=active]:text-black"><Settings size={14} className="mr-2"/>자산</TabsTrigger>
                  </TabsList>
                  <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest hidden md:block italic">Analytical Archive</span>
                </div>
              </Tabs>
            </CardHeader>
            <CardContent className="p-0 flex-1 min-h-[300px] xl:h-[500px] overflow-hidden relative">
              <div className="absolute inset-0 overflow-auto custom-scrollbar pt-1">
                {activeTab === "1" ? (
                  <div className="px-4">
                    <Table>
                      <TableHeader className="bg-zinc-900 sticky top-0 z-10 backdrop-blur-md">
                        <TableRow className="border-white/5 hover:bg-transparent">
                          <TableHead className="text-[10px] font-bold text-zinc-400 uppercase">Timestamp</TableHead>
                          <TableHead className="text-[10px] font-bold text-zinc-400 uppercase text-center">Asset</TableHead>
                          <TableHead className="text-[10px] font-bold text-zinc-400 uppercase text-center">Action</TableHead>
                          <TableHead className="text-[10px] font-bold text-zinc-400 uppercase text-right">Price</TableHead>
                          <TableHead className="text-[10px] font-bold text-zinc-400 uppercase text-center">Profit</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {reversedTrades.map((t, i) => (
                          <TableRow key={i} className="border-white/5 hover:bg-white/[0.02] transition-colors">
                            <TableCell className="text-[10px] text-zinc-500 font-mono py-2">{t?.timestamp?.slice(5, 19)}</TableCell>
                            <TableCell className="text-center font-bold text-[12px] py-2 tracking-tight">{t?.symbol}</TableCell>
                            <TableCell className="text-center py-2">
                              <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${t?.type === 'BUY' ? 'bg-zinc-800 text-white border border-white/10' : 'bg-white text-black'}`}>
                                {t?.type}
                              </span>
                            </TableCell>
                            <TableCell className="text-right font-mono text-[11px] py-2">${(t?.price || 0).toLocaleString()}</TableCell>
                            <TableCell className={`text-center font-bold text-[11px] py-2 ${t?.profit_rate > 0 ? 'text-white' : 'text-zinc-600'}`}>
                              {t?.profit_rate}%
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="h-full px-4 pb-4">
                    <ResponsiveContainer width="100%" height="100%">
                    {activeTab === "2" ? (
                      <AreaChart data={trades}>
                        <defs>
                          <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#fff" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#fff" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                        <XAxis dataKey="timestamp" hide />
                        <YAxis stroke="#444" fontSize={10} tickLine={false} axisLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <Area type="monotone" dataKey="profit_rate" stroke="#fff" strokeWidth={2} fill="url(#colorProfit)" />
                      </AreaChart>
                    ) : activeTab === "3" ? (
                      <BarChart data={botInfo?.coinStats || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                        <XAxis dataKey="name" fontSize={10} stroke="#444" />
                        <YAxis stroke="#444" fontSize={10} />
                        <Tooltip cursor={{fill: '#222'}} content={<CustomTooltip />} />
                        <Bar dataKey="totalProfit" fill="#fff" radius={[2, 2, 0, 0]} barSize={12} />
                        <Bar dataKey="totalLoss" fill="#333" radius={[2, 2, 0, 0]} barSize={12} />
                      </BarChart>
                    ) : (
                      <LineChart data={equity.slice(-100)}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#222" vertical={false} />
                        <XAxis dataKey="timestamp" hide />
                        <YAxis yAxisId="left" domain={['auto', 'auto']} stroke="#fff" fontSize={10} />
                        <YAxis yAxisId="right" orientation="right" domain={['auto', 0]} stroke="#444" fontSize={10} />
                        <Tooltip content={<CustomTooltip />} />
                        <Line yAxisId="left" type="monotone" dataKey="equity" stroke="#fff" strokeWidth={3} dot={false} />
                        <Line yAxisId="right" type="stepAfter" dataKey="mdd" stroke="#444" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              )}
            </div>
            </CardContent>
          </Card>
        </div>

        {/* SIDEBAR ASSETS SECTION */}
        <div className="xl:col-span-5 flex flex-col">
          <div className="grid grid-cols-2 gap-4 overflow-y-auto max-h-[620px] pr-2 custom-scrollbar">
            {botInfo?.coinStats?.map((coin, idx) => (
              <Card key={idx} className="bg-zinc-900/50 border-white/5 hover:border-white/20 transition-all flex flex-col min-h-[200px]">
                <CardHeader className="p-3 border-b border-white/5 bg-white/[0.02]">
                  <div className="flex justify-between items-center">
                    <CardTitle className="text-[13px] font-bold italic text-white uppercase tracking-tighter leading-none">
                      {coin?.name}
                    </CardTitle>
                    <Badge className={`text-[8px] px-1.5 py-0 border-none leading-none ${coin?.status === '보유중' ? 'bg-white text-black' : 'bg-zinc-800 text-zinc-500'}`}>
                      {coin?.status || '분석중'}
                    </Badge>
                  </div>
                </CardHeader>
                
                <CardContent className="p-3 flex-1 flex flex-col justify-center gap-y-3">
                  {/* 2열 3행: 성과(왼쪽)와 설정(오른쪽)의 논리적 배치 */}
                  <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                    {[
                      { label: 'WIN', value: coin?.winRate },
                      { label: 'PROFIT', value: coin?.profit },
                      { label: 'LEV', value: coin?.lev },
                      { label: 'TS', value: coin?.ts },
                      { label: 'DIST', value: coin?.dist },
                      { label: 'VOL', value: coin?.vol }
                    ].map((item, i) => (
                      <div key={i} className="flex flex-col border-l border-white/10 pl-2">
                        <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-tighter leading-none mb-1">
                          {item.label}
                        </span>
                        <span className="text-[15px] font-mono font-bold italic text-white leading-none truncate">
                          {item.value || '0'}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>

      {/* FOOTER & AI INSIGHTS SECTION */}
      <footer className="mt-6 flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Market Prices Bar */}
          <div className="bg-zinc-900 border border-white/5 p-4 rounded-xl flex justify-between items-center font-mono text-[11px]">
            {['BTC', 'ETH', 'SOL', 'XRP'].map(sym => (
              <div key={sym} className="flex gap-2">
                <span className="text-zinc-500 font-bold tracking-widest uppercase">{sym}</span>
                <span className="text-white font-bold tracking-tighter italic">${prices[sym]}</span>
              </div>
            ))}
          </div>

          {/* AI Insights Bar */}
          <div className="bg-white text-black p-1 rounded-xl flex items-center shadow-lg">
            <div className="flex gap-2 p-2">
              <Button onClick={() => fetchAI('strategy')} disabled={loading} size="sm" className="bg-black text-white hover:bg-zinc-800 h-8 text-[11px] font-bold uppercase rounded-lg px-4">AI Strategy</Button>
              <Button onClick={() => fetchAI('market')} disabled={loading} size="sm" className="bg-zinc-100 text-black border border-black/10 h-8 text-[11px] font-bold uppercase rounded-lg px-4">AI Market</Button>
            </div>
            <div className="px-4 text-[12px] font-bold flex-1 truncate italic tracking-tight">
              "{aiComment}"
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center text-[10px] text-zinc-600 font-mono pt-4  tracking-widest border-t border-white/5">
          <div className="flex gap-6">
            <span className="flex uppercase items-center gap-1"> <FaGithub />github.com/hojin5035</span>
            <span className="flex items-center gap-1"><Mail size={12}/> hojin5035@naver.com</span>
          </div>
          <div>© 2026 HOJIN_LAB ARCHIVE v0.1.1</div>
        </div>
      </footer>
    </div>
  );
}

export default App; 