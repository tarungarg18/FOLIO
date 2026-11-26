"use client";

import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart as RechartsPieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowDownToLine, ArrowUpRight, BarChart3, CircleHelp, LayoutDashboard, Leaf, Menu, MessageCircle, PieChart, ShieldCheck, Sparkles, WalletCards } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Position = { instrument_id: string; name: string; symbol?: string; asset_type: string; quantity: number; unit_price: number; market_value: number; as_of?: string; average_cost: number };
type Summary = { name: string; total_value: number; positions: Position[]; exposure_coverage: number; is_illustrative: boolean; missing: string[]; asset_allocation: Record<string, number> };
type Company = { instrument_id: string; name: string; symbol?: string; direct_value: number; indirect_value: number; combined_value: number; portfolio_percentage: number; fund_sources: Array<{ fund_name: string; weight_percentage: number; reporting_date: string }> };
type Exposure = { companies: Company[]; coverage_percentage: number; eligible_exposure: number; unmapped_eligible_exposure: number };
type Insight = { id: string; severity: string; title: string; explanation: string; evidence?:Company; coverage_percentage?:number };
type Trend = { status: string; period: string; observations: number; label?: string; series: Array<{date:string;value:number;normalized_value:number}>; reason?: string; source_dates?: Array<{instrument:string;from:string;through:string}> };
type Risk = { status:string; observations?:number; period_start?:string; period_end?:string; annualized_volatility?:number; maximum_drawdown?:number; beta?:number; correlation?:number; health?:{status:string;score:number|null;components:Array<{key:string;weight:number;score:number}>}; drawdown_series?:Array<{date:string;drawdown:number}>; rolling_volatility_series?:Array<{date:string;volatility:number}> };
type Allocation = {asset_allocation:Record<string,number>;sector_allocation:Record<string,number>;eligible_exposure:number;mapped_exposure:number;unmapped_exposure:number;unassessed_fund_value:number};

function Empty({children}:{children:string}) { return <p className="mt-4 rounded-xl bg-ivory px-3 py-7 text-center text-sm text-muted">{children}</p>; }
function Metric({label,value}:{label:string;value:string}) { return <div className="rounded-lg bg-ivory p-3"><p className="text-xs text-muted">{label}</p><p className="mt-1 font-medium">{value}</p></div>; }
function MiniLine({title,data,keyName}:{title:string;data:Array<{date:string;[key:string]:any}>;keyName:string}) { return <div><p className="mb-1 text-xs text-muted">{title}</p><div className="h-24">{data.length?<ResponsiveContainer><LineChart data={data}><XAxis dataKey="date" hide/><YAxis hide/><Tooltip/><Line dataKey={keyName} stroke="#214E42" dot={false} strokeWidth={1.5}/></LineChart></ResponsiveContainer>:<p className="pt-7 text-center text-xs text-muted">Insufficient observations</p>}</div></div>; }

const menu = [
  { label: "Overview", target: "overview", icon: LayoutDashboard },
  { label: "Holdings", target: "holdings", icon: WalletCards },
  { label: "Diversification", target: "exposure", icon: PieChart },
  { label: "Risk", target: "risk", icon: ShieldCheck },
  { label: "Insights", target: "insights", icon: Sparkles },
  { label: "Ask Folio", target: "ask", icon: MessageCircle },
];
const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

export default function Home() {
  const [portfolioId, setPortfolioId] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [exposure, setExposure] = useState<Exposure | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [period, setPeriod] = useState("1Y");
  const [trend, setTrend] = useState<Trend|null>(null);
  const [risk, setRisk] = useState<Risk|null>(null);
  const [allocation, setAllocation] = useState<Allocation|null>(null);
  const [matrix, setMatrix] = useState<any>(null);
  const [benchmarkId, setBenchmarkId] = useState("nifty_50_tri");
  const [benchmarkData, setBenchmarkData] = useState<any>(null);
  const [notice, setNotice] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  async function request(path: string, init?: RequestInit) {
    const response = await fetch(`${API}${path}`, { ...init, credentials: "include" });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.code || body.error?.code || "Request failed");
    return body;
  }

  async function load(id: string) {
    setPortfolioId(id);
    const [s, e, i, a, m] = await Promise.all([
      request(`/api/v1/analytics/summary?portfolio_id=${encodeURIComponent(id)}`),
      request(`/api/v1/analytics/exposure?portfolio_id=${encodeURIComponent(id)}`),
      request(`/api/v1/insights?portfolio_id=${encodeURIComponent(id)}`),
      request(`/api/v1/analytics/allocation?portfolio_id=${encodeURIComponent(id)}`),
      request(`/api/v1/analytics/overlap-matrix?portfolio_id=${encodeURIComponent(id)}`),
    ]);
    setSummary(s.data);
    setExposure(e.data);
    setInsights(i.data);
    setAllocation(a.data);
    setMatrix(m.data);
  }

  useEffect(() => {
    let mounted = true;
    void request("/api/v1/demo/open", { method: "POST" })
      .then((result) => {
        if (mounted) return load(result.portfolio._id);
        return undefined;
      })
      .catch(() => {
        if (mounted) setNotice("Folio could not connect to its local services.");
      });
    return () => { mounted = false; };
  }, []);

  useEffect(() => {
    if (!portfolioId) return;
    Promise.all([
      request(`/api/v1/analytics/history?portfolio_id=${encodeURIComponent(portfolioId)}&period=${period}`),
      request(`/api/v1/analytics/risk?portfolio_id=${encodeURIComponent(portfolioId)}&period=${period}`),
    ]).then(([history, riskResult]) => { setTrend(history.data); setRisk(riskResult.data.risk); if (riskResult.data.health) setRisk((current) => ({ ...current, ...riskResult.data.risk, health: riskResult.data.health })); })
      .catch(() => { setTrend(null); setRisk(null); });
  }, [portfolioId, period]);

  useEffect(() => {
    if (!portfolioId) return;
    request(`/api/v1/analytics/benchmark?portfolio_id=${encodeURIComponent(portfolioId)}&benchmark_id=${benchmarkId}&period=${period}`)
      .then((result) => setBenchmarkData(result.data))
      .catch(() => setBenchmarkData(null));
  }, [portfolioId, period, benchmarkId]);

  const companies = exposure?.companies.slice(0, 10) || [];
  const assetData = Object.entries(allocation?.asset_allocation || {}).map(([name,value])=>({name:name.replace("_"," "),value}));
  const sectorData = Object.entries(allocation?.sector_allocation || {}).map(([name,value])=>({name,value})).sort((a,b)=>b.value-a.value).slice(0,8);

  function navigate(target: string) {
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
    setMenuOpen(false);
  }

  async function importFile(file?: File) {
    if (!file || !portfolioId) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const preview = await request(`/api/v1/portfolios/${portfolioId}/import/preview`, { method: "POST", body: form });
      setNotice(`${preview.rows.length} rows need instrument review; ${preview.errors.length} rows have validation issues. Nothing was saved.`);
    } catch (error) {
      setNotice(`Could not read CSV: ${error instanceof Error ? error.message : "Request failed"}`);
    } finally {
      setBusy(false);
    }
  }

  async function ask() {
    if (!question.trim() || !portfolioId || busy) return;
    setBusy(true);
    setAnswer("");
    try {
      const result = await request("/api/v1/copilot/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ portfolio_id: portfolioId, question }),
      });
      setAnswer(result.answer);
    } catch {
      setAnswer("Portfolio analysis is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen lg:flex">
      <aside className="hidden w-[248px] shrink-0 flex-col border-r border-line bg-white px-5 py-7 lg:flex">
        <div className="mb-10 flex items-center gap-3"><div className="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"><Leaf size={21} /></div><div><div className="font-editorial text-2xl">folio</div><div className="text-[10px] uppercase tracking-[.19em] text-muted">Your money, understood</div></div></div>
        <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[.16em] text-muted">Portfolio</p>
        <nav className="space-y-1">{menu.map((item) => <button key={item.label} onClick={() => navigate(item.target)} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-muted transition hover:bg-sage hover:text-forest"><item.icon size={17} />{item.label}</button>)}</nav>
        <div className="mt-auto rounded-xl bg-ivory p-4"><div className="mb-2 flex items-center gap-2 text-xs font-medium"><CircleHelp size={15} className="text-forest" />Data transparency</div><p className="text-xs leading-5 text-muted">See when portfolio and fund data was last reported.</p></div>
      </aside>

      <main className="min-w-0 flex-1 pb-16 lg:pb-0">
        <header className="sticky top-0 z-10 flex h-[72px] items-center justify-between border-b border-line bg-white/95 px-5 backdrop-blur sm:px-8 lg:px-10">
          <div className="flex items-center gap-3"><button className="lg:hidden" aria-label="Toggle menu" onClick={() => setMenuOpen(!menuOpen)}><Menu size={20} /></button><div><p className="text-xs text-muted">Illustrative portfolio</p><h1 className="font-editorial text-xl sm:text-2xl">Good morning</h1></div></div>
          <span className="rounded-full bg-sage px-3 py-1.5 text-xs text-forest">Demo workspace</span>
        </header>
        {menuOpen && <nav className="grid grid-cols-3 gap-1 border-b border-line bg-white p-3 lg:hidden">{menu.map((item) => <button key={item.label} onClick={() => navigate(item.target)} className="flex flex-col items-center gap-1 rounded-lg p-2 text-xs text-muted hover:bg-sage"><item.icon size={17} />{item.label}</button>)}</nav>}

        <div className="mx-auto max-w-[1440px] space-y-5 px-5 py-7 sm:px-8 lg:px-10" id="overview">
          {notice && <div className="rounded-lg border border-amber/50 bg-amber/10 px-4 py-2.5 text-sm text-ink">{notice}<button className="ml-3 text-muted" onClick={() => setNotice("")} aria-label="Dismiss">×</button></div>}
          <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="mb-1 text-sm text-muted">Your portfolio at a glance</p><h2 className="font-editorial text-3xl">A clearer view of what you own.</h2></div><label className="flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-white px-4 py-2.5 text-sm font-medium hover:border-forest"><ArrowDownToLine size={16} />{busy ? "Working…" : "Import CSV"}<input type="file" accept=".csv,text/csv" className="hidden" disabled={busy} onChange={(event) => void importFile(event.target.files?.[0])} /></label></div>

          {!summary?.positions.length && <div className="rounded-xl border border-line bg-white px-4 py-3 text-sm text-muted">Your portfolio is ready. Import holdings to see value and underlying exposure.</div>}
          <section className="grid scroll-mt-24 gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-forest p-6 text-white md:col-span-2"><p className="text-sm text-white/70">Portfolio value</p><p className="number mt-3 font-editorial text-4xl sm:text-5xl">{summary?.positions.length ? money(summary.total_value) : "—"}</p><p className="mt-2 text-xs text-white/65">Latest available closing prices and NAVs</p><div className="mt-6 flex gap-8 border-t border-white/15 pt-4"><div><p className="text-xs text-white/65">Positions</p><p className="mt-1 text-lg">{summary?.positions.length ?? "—"}</p></div><div><p className="text-xs text-white/65">Eligible look-through coverage</p><p className="mt-1 text-lg">{exposure?.eligible_exposure ? `${exposure.coverage_percentage.toFixed(1)}%` : "—"}</p></div></div></div>
            <div className="rounded-2xl border border-line bg-white p-6"><p className="text-sm text-muted">Portfolio health</p><p className="mt-5 font-editorial text-4xl text-forest">{risk?.health?.score ?? "—"}<span className="ml-1 text-base text-muted">{risk?.health?.score!==null&&risk?.health?.score!==undefined?"/100":""}</span></p><p className="mt-2 text-sm leading-6 text-muted">{risk?.health?.status==="heuristic"?"Internal educational score · see component breakdown below":"Shown when verified history and exposure coverage are available."}</p></div>
          </section>

          <section className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-editorial text-xl">Portfolio value trend</h3><p className="mt-1 text-xs text-muted">{trend?.status==="available"?`${trend.label} · ${trend.observations} observations`:"Historical series appears when all holdings have verified history."}</p></div><div className="flex gap-1 rounded-lg bg-ivory p-1">{["1M","3M","6M","1Y","3Y","5Y"].map(p=><button key={p} onClick={()=>setPeriod(p)} className={`rounded-md px-2 py-1 text-xs ${period===p?"bg-white text-forest shadow-sm":"text-muted"}`}>{p}</button>)}</div></div>{trend?.status==="available"?<div className="mt-4 h-[260px]"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend.series}><defs><linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#214E42" stopOpacity={.18}/><stop offset="100%" stopColor="#214E42" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#eeede7" vertical={false}/><XAxis dataKey="date" tick={{fontSize:10,fill:"#78817B"}} minTickGap={24}/><YAxis tickFormatter={v=>money(v)} tick={{fontSize:10,fill:"#78817B"}}/><Tooltip labelFormatter={v=>String(v)} formatter={v=>money(Number(v))}/><Area type="monotone" dataKey="value" stroke="#214E42" fill="url(#trendFill)"/></AreaChart></ResponsiveContainer></div>:<p className="mt-5 rounded-xl bg-ivory px-4 py-7 text-center text-sm text-muted">{trend?.reason || "No verified historical series available yet."}</p>}</section>

          <section className="grid gap-5 lg:grid-cols-3" id="exposure">
            <div className="rounded-2xl border border-line bg-white p-5"><h3 className="font-editorial text-lg">Asset allocation</h3>{assetData.length?<div className="mt-3 h-48"><ResponsiveContainer><RechartsPieChart><Pie data={assetData} dataKey="value" nameKey="name" innerRadius={48} outerRadius={76}>{assetData.map((_,i)=><Cell key={i} fill={["#214E42","#7fa18e","#E9B96C","#C9795B"][i%4]}/>)}</Pie><Tooltip formatter={v=>money(Number(v))}/><Legend/></RechartsPieChart></ResponsiveContainer></div>:<Empty>No allocation data</Empty>}</div>
            <div className="rounded-2xl border border-line bg-white p-5"><h3 className="font-editorial text-lg">Sector allocation</h3>{sectorData.length?<div className="mt-3 h-48"><ResponsiveContainer><BarChart data={sectorData} layout="vertical" margin={{left:8}}><XAxis type="number" hide/><YAxis type="category" dataKey="name" width={90} tick={{fontSize:10}}/><Tooltip formatter={v=>money(Number(v))}/><Bar dataKey="value" fill="#214E42" radius={[0,4,4,0]}/></BarChart></ResponsiveContainer></div>:<Empty>Sector data appears with mapped holdings</Empty>}</div>
            <div className="rounded-2xl border border-line bg-white p-5"><h3 className="font-editorial text-lg">Top 10 company exposure</h3>{companies.length?<div className="mt-3 h-[310px]"><ResponsiveContainer><BarChart data={companies} layout="vertical" margin={{left:4}}><XAxis type="number" hide/><YAxis type="category" dataKey="name" width={105} tick={{fontSize:10}}/><Tooltip formatter={v=>money(Number(v))}/><Legend/><Bar dataKey="direct_value" name="Direct" stackId="x" fill="#214E42"/><Bar dataKey="indirect_value" name="Through funds" stackId="x" fill="#E9B96C"/></BarChart></ResponsiveContainer></div>:<Empty>Mapped equity exposure appears here</Empty>}</div>
          </section>

          <section className="grid scroll-mt-24 gap-5 lg:grid-cols-2" id="holdings"><div className="rounded-2xl border border-line bg-white p-5"><h3 className="font-editorial text-lg">Portfolio health</h3>{risk?.health?.score!==null&&risk?.health?.score!==undefined?<><p className="mt-2 font-editorial text-4xl text-forest">{risk.health.score}<span className="ml-1 text-base text-muted">/100</span></p><div className="mt-3 space-y-2">{risk.health.components.map(c=><div key={c.key} className="flex items-center gap-3 text-xs"><span className="w-28 capitalize text-muted">{c.key}</span><div className="h-1.5 flex-1 rounded bg-ivory"><div className="h-full rounded bg-forest" style={{width:`${c.score}%`}}/></div><span>{Math.round(c.score)}</span></div>)}</div><p className="mt-2 text-[11px] text-muted">{risk.period_start} to {risk.period_end} · {risk.observations} observations · internal heuristic</p></>:<Empty>A score needs verified exposure and historical observations</Empty>}</div><div className="rounded-2xl border border-line bg-white p-5"><h3 className="font-editorial text-lg">Top insight</h3>{insights.length?<><p className="mt-3 text-sm font-medium">{insights[0].title}</p><p className="mt-2 text-sm leading-6 text-muted">{insights[0].explanation}</p>{insights[0].evidence&&<div className="mt-3 rounded-lg bg-ivory p-3 text-xs"><p>Contributing holding: {insights[0].evidence.name} · {insights[0].evidence.portfolio_percentage.toFixed(1)}% of portfolio</p>{insights[0].evidence.fund_sources.map((source,i)=><p key={i} className="mt-1 text-muted">{source.fund_name}: {source.weight_percentage}% · reported {source.reporting_date}</p>)}</div>}<p className="mt-2 text-xs text-muted">Severity: {insights[0].severity} · <button onClick={()=>navigate("exposure")} className="text-forest">Review exposure</button></p></>:<Empty>No evidence-backed insight for this portfolio yet</Empty>}</div></section>

          <section className="rounded-2xl border border-line bg-white p-5"><div className="flex items-center justify-between"><h3 className="font-editorial text-lg">Mutual fund overlap</h3><span className="text-xs text-muted">Common mapped companies</span></div>{matrix?.matrix?.length?<div className="mt-4 overflow-x-auto"><table className="min-w-full text-left text-xs"><thead><tr><th className="p-2">Fund</th>{matrix.schemes.map((s:any)=><th key={s.scheme_code} className="max-w-28 p-2">{s.name}</th>)}</tr></thead><tbody>{matrix.matrix.map((row:any)=><tr key={row.scheme_code} className="border-t border-line"><th className="p-2 font-medium">{row.name}<div className="font-normal text-muted">As of {row.reporting_date}</div></th>{matrix.schemes.map((s:any)=><td key={s.scheme_code} className="p-2"><span className="rounded px-2 py-1" style={{backgroundColor:`rgba(33,78,66,${Math.min(.08+row.values[s.scheme_code]/100,.65)})`}}>{row.values[s.scheme_code].toFixed(1)}%</span></td>)}</tr>)}</tbody></table></div>:<Empty>Overlap appears when dated fund disclosures are loaded and mapped</Empty>}<p className="mt-2 text-[11px] text-muted">Each cell sums the lower disclosed weight for companies mapped in both schemes.</p></section>

          <section className="grid scroll-mt-24 gap-5 lg:grid-cols-2" id="risk">
            <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-center gap-2"><ShieldCheck size={17} className="text-forest" /><h3 className="font-editorial text-xl">Risk analysis</h3></div>{risk?.status==="available"?<><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><Metric label="Annualized volatility" value={`${(risk.annualized_volatility!*100).toFixed(2)}%`}/><Metric label="Maximum drawdown" value={`${(risk.maximum_drawdown!*100).toFixed(2)}%`}/><Metric label="Beta" value={risk.beta?.toFixed(2)??"—"}/><Metric label="Correlation" value={risk.correlation?.toFixed(2)??"—"}/></div><p className="mt-3 text-[11px] text-muted">{risk.period_start} to {risk.period_end} · {risk.observations} daily observations</p><div className="mt-4 grid gap-4 sm:grid-cols-2"><MiniLine title="Drawdown" data={risk.drawdown_series||[]} keyName="drawdown"/><MiniLine title="Rolling volatility (21 sessions)" data={risk.rolling_volatility_series||[]} keyName="volatility"/></div></>:<Empty>Risk metrics appear when verified portfolio and benchmark history is available</Empty>}</div>
            <div className="rounded-2xl border border-line bg-white p-5 sm:p-6"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><BarChart3 size={17} className="text-forest"/><h3 className="font-editorial text-xl">Benchmark</h3></div><select aria-label="Benchmark" className="rounded-md border border-line bg-white px-2 py-1 text-xs" onChange={e=>setBenchmarkId(e.target.value)} value={benchmarkId}><option value="nifty_50_tri">NIFTY 50 TRI</option><option value="nifty_500_tri">NIFTY 500 TRI</option></select></div>{benchmarkData?.status==="available"?<><div className="mt-3 flex justify-between text-sm"><span>Relative difference</span><b>{benchmarkData.relative_return_percentage_points.toFixed(2)} pts</b></div><div className="mt-1 text-xs text-muted">{benchmarkData.start_date} to {benchmarkData.end_date} · {benchmarkData.observations} observations</div><div className="mt-3 h-[220px]"><ResponsiveContainer><LineChart data={benchmarkData.series}><CartesianGrid stroke="#eeede7"/><XAxis dataKey="date" minTickGap={30} tick={{fontSize:9}}/><YAxis domain={['auto','auto']} tick={{fontSize:9}}/><Tooltip/><Legend/><Line type="monotone" dataKey="portfolio" name="FOLIO hypothetical" stroke="#214E42" dot={false}/><Line type="monotone" dataKey="benchmark" name={benchmarkId==="nifty_50_tri"?"NIFTY 50 TRI":"NIFTY 500 TRI"} stroke="#C9795B" dot={false}/></LineChart></ResponsiveContainer></div><p className="text-[11px] text-muted">Both series rebased to ₹100 on the same first common date.</p></>:<Empty>Benchmark comparison appears when verified TRI data is loaded</Empty>}</div>
            <div className="scroll-mt-24 rounded-2xl border border-line bg-white p-5 sm:p-6" id="insights"><div className="flex items-center gap-2"><Sparkles size={17} className="text-forest" /><h3 className="font-editorial text-xl">Insights</h3></div>{insights.length ? <div className="mt-4 space-y-3">{insights.slice(0, 2).map((insight) => <div key={insight.id} className="rounded-xl bg-ivory p-4"><p className="text-sm font-medium">{insight.title}</p><p className="mt-1 text-xs leading-5 text-muted">{insight.explanation}</p></div>)}</div> : <p className="mt-2 text-sm text-muted">No portfolio observations yet.</p>}</div>
          </section>

          <section className="scroll-mt-24 rounded-2xl border border-line bg-white p-5 sm:p-6" id="ask"><div className="flex items-center gap-2"><MessageCircle size={17} className="text-forest" /><h3 className="font-editorial text-xl">Ask Folio</h3></div><p className="mt-1 text-xs text-muted">Answers use available portfolio calculations.</p><form className="mt-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); void ask(); }}><input value={question} onChange={(event) => setQuestion(event.target.value)} className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-forest" placeholder="Ask about your exposure" /><button disabled={busy || !portfolioId} className="rounded-lg bg-forest px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Ask</button></form>{answer && <p className="mt-3 rounded-lg bg-sage p-4 text-sm leading-6">{answer}</p>}</section>
          <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-line py-3 text-[11px] text-muted"><span>Illustrative positions · not investment advice</span><span>Data dates are shown with each value</span></footer>
        </div>
        <nav className="fixed inset-x-0 bottom-0 z-10 flex justify-around border-t border-line bg-white px-1 py-2 lg:hidden">{menu.map((item) => <button key={item.label} onClick={() => navigate(item.target)} className="flex flex-col items-center gap-1 px-1 py-1 text-[9px] text-muted"><item.icon size={16} />{item.label}</button>)}</nav>
      </main>
    </div>
  );
}
