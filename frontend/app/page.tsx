"use client";

import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, ArrowDownToLine, ArrowUpRight, BarChart3, CircleHelp, LayoutDashboard, Leaf, Menu, MessageCircle, PieChart, Search, ShieldCheck, Sparkles, WalletCards } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Summary = { name: string; total_value: number; positions: Array<{instrument_id:string;name:string;symbol?:string;asset_type:string;quantity:number;unit_price:number;market_value:number;as_of?:string;average_cost:number}>; exposure_coverage: number; is_illustrative: boolean; missing: string[]; asset_allocation: Record<string,number> };
type Exposure = { companies: Array<{instrument_id:string;name:string;symbol?:string;direct_value:number;indirect_value:number;combined_value:number;portfolio_percentage:number;fund_sources:Array<{fund_name:string;weight_percentage:number;reporting_date:string}>}>; coverage_percentage:number; unmapped_eligible_exposure:number };
type Insight = {id:string;severity:string;title:string;explanation:string;portfolio_percentage?:number;coverage_percentage?:number};

const nav = [{name:"Overview",icon:LayoutDashboard},{name:"Holdings",icon:WalletCards},{name:"Diversification",icon:PieChart},{name:"Risk analysis",icon:ShieldCheck},{name:"Benchmark",icon:BarChart3},{name:"Insights",icon:Sparkles},{name:"Ask Folio",icon:MessageCircle}];
const money = (n:number) => new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format(n || 0);

export default function Home() {
  const [portfolioId,setPortfolioId] = useState("");
  const [summary,setSummary] = useState<Summary|null>(null);
  const [exposure,setExposure] = useState<Exposure|null>(null);
  const [insights,setInsights] = useState<Insight[]>([]);
  const [tab,setTab] = useState("Overview");
  const [notice,setNotice] = useState("");
  const [question,setQuestion] = useState("");
  const [answer,setAnswer] = useState("");
  const [busy,setBusy] = useState(false);

  async function request(path:string, init?:RequestInit) {
    const response = await fetch(`${API}${path}`,{...init,credentials:"include"});
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.code || body.error?.code || "Request failed");
    return body;
  }
  async function load(id:string) {
    setPortfolioId(id);
    const [s,e,i] = await Promise.all([request(`/api/v1/analytics/summary?portfolio_id=${id}`),request(`/api/v1/analytics/exposure?portfolio_id=${id}`),request(`/api/v1/insights?portfolio_id=${id}`)]);
    setSummary(s.data); setExposure(e.data); setInsights(i.data);
  }
  async function openDemo() {
    try { const result = await request("/api/v1/demo/open",{method:"POST"}); await load(result.portfolio._id); setNotice("Illustrative positions. Market data appears only after verified source data is loaded."); }
    catch { setNotice("Start the local FastAPI and MongoDB services, then retry demo access."); }
  }
  useEffect(()=>{ void openDemo(); },[]);
  const chart = useMemo(()=> summary?.positions.map((p,i)=>({day:p.name.slice(0,12),value:p.market_value,order:i})) || [],[summary]);
  async function importFile(file?:File) {
    if (!file || !portfolioId) return;
    setBusy(true);
    try {
      const data = new FormData(); data.append("file",file);
      const preview = await request(`/api/v1/portfolios/${portfolioId}/import/preview`,{method:"POST",body:data});
      const accepted = preview.rows.filter((row:{identifier:string;status:string})=>row.status==="matched");
      if (!accepted.length) setNotice(`Import preview: ${preview.rows.length} rows need instrument review; ${preview.errors.length} rows have validation errors. No rows were saved.`);
      else setNotice(`Import preview: ${accepted.length} matched rows; confirmation is required before saving.`);
    } catch (error) { setNotice(`CSV preview failed: ${String(error)}`); }
    finally { setBusy(false); }
  }
  async function ask() {
    if (!question.trim() || !portfolioId) return;
    setBusy(true); setAnswer("");
    try { const result=await request("/api/v1/copilot/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({portfolio_id:portfolioId,question})});setAnswer(result.answer); }
    catch { setAnswer("Portfolio analysis is unavailable until the local API and verified market data are ready."); }
    finally { setBusy(false); }
  }
  const topCompanies=exposure?.companies.slice(0,5)||[];

  return <div className="min-h-screen lg:flex">
    <aside className="hidden w-[248px] shrink-0 border-r border-line bg-white px-5 py-7 lg:flex lg:flex-col">
      <div className="mb-10 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"><Leaf size={21}/></div><div><div className="font-editorial text-2xl tracking-tight">folio</div><div className="text-[10px] uppercase tracking-[.19em] text-muted">Your money, understood</div></div></div>
      <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[.16em] text-muted">Portfolio</div>
      <nav className="space-y-1">{nav.map(item=><button key={item.name} onClick={()=>setTab(item.name)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm ${tab===item.name?"bg-sage font-medium text-forest":"text-muted hover:bg-ivory hover:text-ink"}`}><item.icon size={17}/>{item.name}</button>)}</nav>
      <div className="mt-auto rounded-xl bg-ivory p-4"><div className="mb-2 flex items-center gap-2 text-xs font-medium"><CircleHelp size={15} className="text-forest"/>Data transparency</div><p className="text-xs leading-5 text-muted">Portfolio observations show their source dates and mapping coverage.</p><button onClick={()=>setTab("Ask Folio")} className="mt-3 text-xs font-semibold text-forest">Ask Folio <ArrowUpRight size={12} className="inline"/></button></div>
    </aside>
    <main className="min-w-0 flex-1">
      <header className="flex h-[76px] items-center justify-between border-b border-line bg-white px-5 sm:px-8 lg:px-10"><div className="flex items-center gap-3"><button className="lg:hidden" aria-label="Open navigation"><Menu size={20}/></button><div><p className="text-xs text-muted">Illustrative investor portfolio</p><h1 className="font-editorial text-xl sm:text-2xl">Good morning, investor</h1></div></div><div className="flex items-center gap-3"><div className="hidden items-center gap-2 rounded-full bg-sage px-3 py-1.5 text-xs text-forest sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-forest"/>Demo workspace</div><button className="grid h-9 w-9 place-items-center rounded-full bg-ivory text-sm font-semibold text-forest">DI</button></div></header>
      <div className="mx-auto max-w-[1440px] px-5 py-7 sm:px-8 lg:px-10">
        {notice&&<div className="mb-5 rounded-lg border border-amber/60 bg-amber/10 px-4 py-3 text-sm text-ink">{notice}</div>}
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><p className="mb-1 text-sm text-muted">Tuesday, your portfolio at a glance</p><h2 className="font-editorial text-3xl">A clearer view of what you own.</h2></div><label className="flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-white px-4 py-2.5 text-sm font-medium hover:border-forest"><ArrowDownToLine size={16}/>Import holdings<input type="file" accept=".csv,text/csv" className="hidden" onChange={e=>void importFile(e.target.files?.[0])}/></label></div>
        <section className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-forest p-6 text-white md:col-span-2"><div className="flex items-start justify-between"><div><p className="text-sm text-white/70">Total portfolio value</p><p className="number mt-3 font-editorial text-4xl sm:text-5xl">{summary?money(summary.total_value):"—"}</p><p className="mt-2 text-xs text-white/65">Current value uses latest valid unadjusted closes and NAVs.</p></div><div className="rounded-full bg-white/10 p-2"><WalletCards size={20}/></div></div><div className="mt-7 grid grid-cols-2 gap-4 border-t border-white/15 pt-4"><div><p className="text-xs text-white/65">Holdings</p><p className="mt-1 text-lg">{summary?.positions.length ?? "—"} positions</p></div><div><p className="text-xs text-white/65">Look-through coverage</p><p className="mt-1 text-lg">{exposure?`${exposure.coverage_percentage.toFixed(1)}%`:"—"}</p></div></div></div>
          <div className="rounded-2xl border border-line bg-white p-6"><div className="flex items-center justify-between"><p className="text-sm text-muted">Portfolio health</p><Activity size={18} className="text-forest"/></div><div className="mt-5 font-editorial text-4xl">—</div><p className="mt-2 text-sm text-muted">Health score will appear when the verified history and coverage support calculation.</p><div className="mt-5 rounded-lg bg-ivory p-3 text-xs leading-5 text-muted">Missing coverage is a confidence limitation, not a sign of lower risk.</div></div>
        </section>
        <section className="mt-5 grid gap-5 xl:grid-cols-[1.6fr_1fr]">
          <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-start justify-between"><div><h3 className="font-editorial text-xl">Portfolio composition</h3><p className="mt-1 text-xs text-muted">Current position values. Historical performance is shown separately when loaded.</p></div><button onClick={()=>setTab("Holdings")} className="text-xs font-medium text-forest">View holdings <ArrowUpRight size={13} className="inline"/></button></div>{chart.length?<div className="mt-4 h-[240px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chart}><defs><linearGradient id="valueFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#214E42" stopOpacity={0.2}/><stop offset="100%" stopColor="#214E42" stopOpacity={0.01}/></linearGradient></defs><CartesianGrid stroke="#eeede7" vertical={false}/><XAxis dataKey="day" tick={{fontSize:10,fill:"#78817B"}} axisLine={false} tickLine={false}/><YAxis tickFormatter={v=>`₹${Math.round(v/1000)}k`} tick={{fontSize:10,fill:"#78817B"}} axisLine={false} tickLine={false}/><Tooltip formatter={(v)=>money(Number(v))}/><Area type="monotone" dataKey="value" stroke="#214E42" strokeWidth={2} fill="url(#valueFill)"/></AreaChart></ResponsiveContainer></div>:<div className="mt-5 grid h-[210px] place-items-center rounded-xl bg-ivory text-center"><div><div className="mx-auto mb-2 grid h-10 w-10 place-items-center rounded-full bg-sage text-forest"><BarChart3 size={18}/></div><p className="text-sm font-medium">Your data will appear here</p><p className="mt-1 text-xs text-muted">Load verified market data and add portfolio holdings.</p></div></div>}</div>
          <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-center justify-between"><div><h3 className="font-editorial text-xl">What you really own</h3><p className="mt-1 text-xs text-muted">Direct and disclosed fund exposure</p></div><PieChart size={18} className="text-forest"/></div>{topCompanies.length?<div className="mt-4 space-y-4">{topCompanies.map(row=><div key={row.instrument_id}><div className="flex items-center justify-between gap-2 text-sm"><span className="truncate font-medium">{row.name}</span><span className="number shrink-0">{row.portfolio_percentage.toFixed(1)}%</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-ivory"><div className="h-full rounded-full bg-forest" style={{width:`${Math.min(row.portfolio_percentage,100)}%`}}/></div><p className="mt-1 text-[11px] text-muted">Direct {money(row.direct_value)} · via funds {money(row.indirect_value)}</p></div>)}</div>:<div className="mt-5 rounded-xl bg-ivory p-4 text-sm leading-6 text-muted">Company look-through appears after real fund disclosures are imported and mapped. Fund constituents are not added again to portfolio value.</div>}<button onClick={()=>setTab("Diversification")} className="mt-5 text-xs font-semibold text-forest">Explore diversification <ArrowUpRight size={13} className="inline"/></button></div>
        </section>
        <section className="mt-5 grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-center justify-between"><div><h3 className="font-editorial text-xl">Insights to consider</h3><p className="mt-1 text-xs text-muted">Observations based on available evidence</p></div><Sparkles size={18} className="text-forest"/></div>{insights.length?<div className="mt-4 space-y-3">{insights.slice(0,3).map(item=><div key={item.id} className="rounded-xl bg-ivory p-4"><div className="flex items-center gap-2"><span className={`h-2 w-2 rounded-full ${item.severity==="high"?"bg-terracotta":"bg-amber"}`}/><p className="text-sm font-medium">{item.title}</p></div><p className="mt-2 text-xs leading-5 text-muted">{item.explanation}</p></div>)}</div>:<div className="mt-4 rounded-xl bg-ivory p-4 text-sm text-muted">No evidence-backed observations are available yet. Missing source data will be shown clearly.</div>}</div>
          <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-center justify-between"><div><h3 className="font-editorial text-xl">Ask Folio</h3><p className="mt-1 text-xs text-muted">Answers use your portfolio calculations</p></div><MessageCircle size={18} className="text-forest"/></div><div className="mt-4 flex gap-2"><input value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>e.key==="Enter"&&void ask()} className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-forest" placeholder="Why is my exposure concentrated?"/><button disabled={busy} onClick={()=>void ask()} className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Ask</button></div>{answer&&<div className="mt-4 rounded-xl bg-sage p-4 text-sm leading-6">{answer}<p className="mt-2 text-[11px] text-muted">Educational portfolio analysis. Latest disclosure dates and coverage apply.</p></div>}<div className="mt-4 flex flex-wrap gap-2">{["Show my largest company exposures","Why might coverage be incomplete?"].map(q=><button key={q} onClick={()=>setQuestion(q)} className="rounded-full border border-line px-3 py-1.5 text-xs text-muted hover:text-forest">{q}</button>)}</div></div>
        </section>
        <footer className="mt-7 flex flex-wrap items-center justify-between gap-2 border-t border-line py-4 text-[11px] text-muted"><span>Illustrative investor positions · not investment advice</span><span><Search size={12} className="mr-1 inline"/>Data freshness and sources are available in the Data Health view</span></footer>
      </div>
      <nav className="fixed inset-x-0 bottom-0 z-10 flex justify-around border-t border-line bg-white px-1 py-2 lg:hidden">{nav.slice(0,5).map(item=><button key={item.name} onClick={()=>setTab(item.name)} className={`flex flex-col items-center gap-1 px-2 py-1 text-[10px] ${tab===item.name?"text-forest":"text-muted"}`}><item.icon size={17}/>{item.name.split(" ")[0]}</button>)}</nav>
    </main>
  </div>;
}
