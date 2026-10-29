import { useEffect, useMemo, useState } from "react";
import { apiRequest, getToken } from "./api";

const money = (value, currency = "NGN") => {
  const amount = Number(value ?? 0);
  try {
    return new Intl.NumberFormat("en-NG", {
      style: "currency", currency, maximumFractionDigits: 2
    }).format(amount);
  } catch {
    return `${currency} ${amount.toLocaleString()}`;
  }
};

function App() {
  const [token, setToken] = useState(getToken());
  const [page, setPage] = useState("dashboard");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [registerMode, setRegisterMode] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [offset, setOffset] = useState(0);
  const [pageSize] = useState(20);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [file, setFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [editing, setEditing] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [insights, setInsights] = useState(null);

  const authHeaders = useMemo(() => ({
    Authorization: `Bearer ${token}`
  }), [token]);

  async function authenticate(event) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      if (registerMode) {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });
      }
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Login failed");
      localStorage.setItem("access_token", data.access_token);
      setToken(data.access_token);
      setNotice(registerMode ? "Account created successfully." : "Welcome back.");
    } catch (e) { setError(e.message || "Could not authenticate."); }
    finally { setBusy(false); }
  }

  function logout() {
    localStorage.removeItem("access_token");
    setToken(null); setSummary(null); setExpenses([]);
    setPage("dashboard"); setNotice(""); setError("");
  }

  async function loadSummary() {
    const params = new URLSearchParams();
    if (categoryFilter) params.set("category", categoryFilter);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    const query = params.toString();
    setSummary(await apiRequest(`/analytics/summary${query ? `?${query}` : ""}`));
  }

  async function loadExpenses(nextOffset = offset) {
    const params = new URLSearchParams({ offset: String(nextOffset), page_size: String(pageSize) });
    if (categoryFilter) params.set("category", categoryFilter);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    setExpenses(await apiRequest(`/expenses/?${params.toString()}`));
    setOffset(nextOffset);
  }

  async function loadInsights() {
    // Existing working endpoint/component uses /analytics/insights.
    setInsights(await apiRequest("/analytics/insights"));
  }

  async function refreshAll() {
    setBusy(true); setError("");
    try {
      await Promise.all([loadSummary(), loadExpenses(0)]);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!token) return;
    refreshAll();
  // Reload data when authenticated; filters are applied by the Apply button.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function navigate(next) {
    setPage(next); setError(""); setNotice("");
    if (!token) return;
    setBusy(true);
    try {
      if (next === "dashboard") await refreshAll();
      if (next === "expenses") await loadExpenses(0);
      if (next === "insights") await loadInsights();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function uploadReceipt(event) {
    event.preventDefault();
    if (!file) { setError("Choose a receipt image or PDF first."); return; }
    setBusy(true); setError(""); setNotice(""); setUploadResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await apiRequest("/expenses/upload", { method: "POST", body: form });
      setUploadResult(result);
      setNotice(result.message || "Receipt processed.");
      setFile(null);
      await refreshAll();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  function startEdit(item) {
    setEditing(item.id);
    setEditForm({
      description: item.description || "",
      category: item.category || "other",
      quantity: item.quantity ?? 1,
      unit_price: item.unit_price ?? ""
    });
  }

  async function saveEdit(id) {
    setBusy(true); setError(""); setNotice("");
    try {
      const payload = {};
      if (editForm.description !== "") payload.description = editForm.description;
      if (editForm.category !== "") payload.category = editForm.category;
      payload.quantity = Number(editForm.quantity);
      payload.unit_price = Number(editForm.unit_price);
      await apiRequest(`/expenses/${id}`, {
        method: "PATCH", body: JSON.stringify(payload)
      });
      setEditing(null);
      await refreshAll();
      setNotice("Expense updated.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function deleteExpense(id) {
    if (!window.confirm("Delete this expense item? This cannot be undone.")) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await apiRequest(`/expenses/${id}`, { method: "DELETE" });
      await refreshAll();
      setNotice("Expense deleted.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function completeReceipt(receiptId) {
    const date = window.prompt("Enter the purchase date (YYYY-MM-DD):");
    if (!date) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await apiRequest(`/expenses/${receiptId}/complete`, {
        method: "POST", body: JSON.stringify({ purchase_date: date })
      });
      await refreshAll();
      setNotice("Receipt completed.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  if (!token) {
    return <div className="auth-shell">
      <div className="auth-brand"><div className="brand-mark">R</div><span>Receipt Intelligence</span></div>
      <form className="auth-card" onSubmit={authenticate}>
        <div className="eyebrow">YOUR FINANCES, CLEARER</div>
        <h1>{registerMode ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">{registerMode ? "Create an account to start tracking your spending." : "Sign in to see your expenses and spending patterns."}</p>
        <label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} autoComplete="email" required /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} autoComplete={registerMode ? "new-password" : "current-password"} minLength={registerMode ? 8 : undefined} required /></label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary full" disabled={busy}>{busy ? "Please wait…" : registerMode ? "Create account" : "Log in"}</button>
        <p className="auth-switch">{registerMode ? "Already registered?" : "New to Receipt Intelligence?"} <button type="button" className="text-button" onClick={() => { setRegisterMode(!registerMode); setError(""); }}>{registerMode ? "Log in" : "Create an account"}</button></p>
      </form>
      <p className="auth-foot">Your receipts. Your data. Your clarity.</p>
    </div>;
  }

  const byCategory = summary?.by_category || [];
  const byMonth = [...(summary?.by_month || [])].reverse();
  const maxCategory = Math.max(1, ...byCategory.map(x => Number(x.total || 0)));
  const maxMonth = Math.max(1, ...byMonth.map(x => Number(x.total || 0)));

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark">R</div><div><strong>Receipt</strong><span>INTELLIGENCE</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>
        {[
          ["dashboard", "◫", "Dashboard"],
          ["expenses", "≡", "Expenses"],
          ["upload", "↑", "Upload receipt"],
          ["insights", "⌁", "Spending insights"]
        ].map(([id, icon, label]) => <button key={id} className={`nav-item ${page === id ? "active" : ""}`} onClick={() => navigate(id)}><span className="nav-icon">{icon}</span>{label}</button>)}
      </nav>
      <div className="sidebar-bottom"><div className="user-avatar">{(email || "U").slice(0,1).toUpperCase()}</div><div className="user-info"><strong>{email || "Your account"}</strong><span>Personal workspace</span></div><button className="icon-button" title="Log out" onClick={logout}>↪</button></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div><span className="breadcrumb">Workspace</span><span className="crumb-sep">/</span><strong>{({dashboard:"Dashboard", expenses:"Expenses", upload:"Upload receipt", insights:"Spending insights"})[page]}</strong></div><div className="topbar-right"><span className="status-dot"></span><span>Connected</span><button className="secondary small" onClick={refreshAll} disabled={busy}>↻ Refresh</button></div></header>
      <div className="page-content">
        {error && <div className="alert error"><span>{error}</span><button onClick={() => setError("")}>×</button></div>}
        {notice && <div className="alert success"><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>}

        {page === "dashboard" && <>
          <div className="page-heading"><div><div className="eyebrow">OVERVIEW</div><h1>Your money at a glance</h1><p className="muted">A clear picture of where your spending is going.</p></div><button className="primary" onClick={() => navigate("upload")}>＋ Upload receipt</button></div>
          <FilterBar category={categoryFilter} setCategory={setCategoryFilter} startDate={startDate} setStartDate={setStartDate} endDate={endDate} setEndDate={setEndDate} apply={refreshAll} busy={busy}/>
          <div className="stat-grid">
            <StatCard label="Total spending" value={money(summary?.total_spend)} detail="For selected filters" icon="₦" />
            <StatCard label="Expense items" value={Number(summary?.expense_count || 0).toLocaleString()} detail="Individual items recorded" icon="▤" />
            <StatCard label="Categories used" value={byCategory.length} detail="Across your expenses" icon="◷" />
            <StatCard label="Recent items loaded" value={expenses.length} detail={`Showing up to ${pageSize}`} icon="↗" />
          </div>
          <div className="content-grid">
            <section className="panel"><div className="panel-heading"><div><h2>Spending by category</h2><p className="muted">Where your money goes</p></div><button className="text-button" onClick={() => navigate("insights")}>More insights ↗</button></div>
              {byCategory.length ? <div className="bars">{byCategory.slice(0,6).map((item, i) => <div className="bar-row" key={item.category || i}><div className="bar-meta"><span>{item.category || "Uncategorized"}</span><strong>{money(item.total)}</strong></div><div className="bar-track"><div className={`bar-fill tone-${i%5}`} style={{width:`${Math.max(2,Number(item.total||0)/maxCategory*100)}%`}} /></div></div>)}</div> : <Empty title="No spending to summarize yet" text="Upload a receipt to begin building your spending overview."/>}
            </section>
            <section className="panel"><div className="panel-heading"><div><h2>Monthly spending</h2><p className="muted">Recorded purchase dates</p></div></div>
              {byMonth.length ? <div className="bars">{byMonth.slice(-6).map((item,i) => <div className="bar-row" key={`${item.year}-${item.month}`}><div className="bar-meta"><span>{new Date(Number(item.year),Number(item.month)-1,1).toLocaleDateString("en",{month:"short",year:"2-digit"})}</span><strong>{money(item.total)}</strong></div><div className="bar-track"><div className={`bar-fill tone-${i%5}`} style={{width:`${Math.max(2,Number(item.total||0)/maxMonth*100)}%`}} /></div></div>)}</div> : <Empty title="No monthly data yet" text="Expenses with purchase dates will appear here."/>}
            </section>
          </div>
          <section className="panel"><div className="panel-heading"><div><h2>Recent expenses</h2><p className="muted">Your latest recorded items</p></div><button className="secondary small" onClick={() => navigate("expenses")}>View all expenses</button></div><ExpenseTable expenses={expenses.slice(0,6)} editing={editing} editForm={editForm} setEditForm={setEditForm} startEdit={startEdit} saveEdit={saveEdit} deleteExpense={deleteExpense} completeReceipt={completeReceipt} /></section>
        </>}

        {page === "expenses" && <>
          <div className="page-heading"><div><div className="eyebrow">RECORDS</div><h1>Expenses</h1><p className="muted">Review and manage your individual expense items.</p></div><button className="primary" onClick={() => navigate("upload")}>＋ Upload receipt</button></div>
          <FilterBar category={categoryFilter} setCategory={setCategoryFilter} startDate={startDate} setStartDate={setStartDate} endDate={endDate} setEndDate={setEndDate} apply={refreshAll} busy={busy}/>
          <section className="panel"><ExpenseTable expenses={expenses} editing={editing} editForm={editForm} setEditForm={setEditForm} startEdit={startEdit} saveEdit={saveEdit} deleteExpense={deleteExpense} completeReceipt={completeReceipt}/><div className="pagination"><span>Showing {expenses.length ? offset+1 : 0}–{offset+expenses.length} items</span><div><button className="secondary small" disabled={offset===0||busy} onClick={() => loadExpenses(Math.max(0,offset-pageSize))}>← Previous</button><button className="secondary small" disabled={expenses.length<pageSize||busy} onClick={() => loadExpenses(offset+pageSize)}>Next →</button></div></div></section>
        </>}

        {page === "upload" && <>
          <div className="page-heading"><div><div className="eyebrow">AUTOMATED CAPTURE</div><h1>Upload a receipt</h1><p className="muted">Let Receipt Intelligence extract the details and classify each line item.</p></div></div>
          <div className="upload-layout"><section className="panel upload-panel"><div className="upload-symbol">↑</div><h2>Choose a receipt file</h2><p className="muted">JPEG, PNG or PDF · Maximum 5 MB</p><form onSubmit={uploadReceipt}><label className="file-drop"><input type="file" accept="image/jpeg,image/png,application/pdf" onChange={e => setFile(e.target.files?.[0] || null)}/><span className="file-icon">▧</span><strong>{file ? file.name : "Click to select a file"}</strong><span className="muted">{file ? `${(file.size/1024/1024).toFixed(2)} MB` : "or use the file picker"}</span></label>{file && <button type="button" className="text-button" onClick={() => setFile(null)}>Remove file</button>}<button className="primary full" disabled={busy||!file}>{busy ? "Processing receipt…" : "Upload and process"}</button></form></section><section className="panel"><h2>What happens next?</h2><div className="step-list"><Step n="01" title="Receipt extraction" text="The receipt reader extracts merchant, date, total and line items."/><Step n="02" title="Automatic categorization" text="Each valid line item is passed through your classification model."/><Step n="03" title="Save and analyze" text="Items are saved to your account and included in spending analytics."/></div></section></div>
          {uploadResult && <section className="panel result-panel"><h2>Processing result</h2><pre>{JSON.stringify(uploadResult,null,2)}</pre>{uploadResult.status==="pending_date" && <button className="primary" onClick={() => completeReceipt(uploadResult.receipt_id)}>Add purchase date</button>}</section>}
        </>}

        {page === "insights" && <>
          <div className="page-heading"><div><div className="eyebrow">PATTERNS & TRENDS</div><h1>Spending insights</h1><p className="muted">Explore your spending patterns.</p></div><button className="secondary" onClick={async()=>{setBusy(true);try{await loadInsights()}catch(e){setError(e.message)}finally{setBusy(false)}}}>↻ Refresh insights</button></div>
          {insights ? <InsightsView data={insights}/> : <section className="panel"><Empty title="Insights not loaded" text="Select refresh to request your analytics insights."/></section>}
          <section className="panel"><div className="panel-heading"><div><h2>Category breakdown</h2><p className="muted">From your analytics summary</p></div></div>{byCategory.length ? <div className="bars">{byCategory.map((item,i)=><div className="bar-row" key={item.category||i}><div className="bar-meta"><span>{item.category||"Uncategorized"}</span><strong>{money(item.total)} · {item.count} items</strong></div><div className="bar-track"><div className={`bar-fill tone-${i%5}`} style={{width:`${Math.max(2,Number(item.total||0)/maxCategory*100)}%`}}/></div></div>)}</div>:<Empty title="No category data" text="Upload receipts to populate your analytics."/ >}</section>
        </>}
      </div>
    </main>
  </div>;
}

function StatCard({label,value,detail,icon}) { return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></div>; }
function Empty({title,text}) { return <div className="empty-state"><div className="empty-icon">◌</div><strong>{title}</strong><p>{text}</p></div>; }
function Step({n,title,text}) { return <div className="step"><span>{n}</span><div><strong>{title}</strong><p className="muted">{text}</p></div></div>; }

function FilterBar({category,setCategory,startDate,setStartDate,endDate,setEndDate,apply,busy}) {
  return <div className="filter-bar"><label>Category<input value={category} onChange={e=>setCategory(e.target.value)} placeholder="All categories"/></label><label>From<input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)}/></label><label>To<input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)}/></label><button className="secondary apply-filter" onClick={apply} disabled={busy}>Apply filters</button></div>;
}

function ExpenseTable({expenses,editing,editForm,setEditForm,startEdit,saveEdit,deleteExpense,completeReceipt}) {
  if (!expenses.length) return <Empty title="No expenses found" text="Upload a receipt or adjust your filters to see expense items."/>;
  return <div className="table-wrap"><table><thead><tr><th>Item</th><th>Category</th><th>Purchase date</th><th>Qty</th><th>Total</th><th>Actions</th></tr></thead><tbody>{expenses.map(item=><tr key={item.id}><td><div className="item-title">{item.description || item.merchant || `Expense #${item.id}`}</div><div className="item-sub">{item.merchant || `Item ID ${item.id}`}</div>{editing===item.id && <div className="edit-fields"><input aria-label="Description" value={editForm.description} onChange={e=>setEditForm({...editForm,description:e.target.value})}/><input aria-label="Quantity" type="number" min="1" value={editForm.quantity} onChange={e=>setEditForm({...editForm,quantity:e.target.value})}/><input aria-label="Unit price" type="number" min="0" step="0.01" value={editForm.unit_price} onChange={e=>setEditForm({...editForm,unit_price:e.target.value})}/><input aria-label="Category" value={editForm.category} onChange={e=>setEditForm({...editForm,category:e.target.value})}/><button className="primary tiny" onClick={()=>saveEdit(item.id)}>Save</button><button className="secondary tiny" onClick={()=>setEditing(null)}>Cancel</button></div>}</td><td><span className="category-pill">{item.category || "other"}</span></td><td>{item.purchase_date ? new Date(item.purchase_date).toLocaleDateString() : <span className="muted">Not set</span>}</td><td>{item.quantity ?? "—"}</td><td className="amount">{new Intl.NumberFormat("en-NG",{style:"currency",currency:item.currency||"NGN",maximumFractionDigits:2}).format(Number(item.total_price ?? item.total ?? 0))}</td><td><div className="row-actions">{item.status==="pending_date" && item.receipt_id && <button className="text-button" onClick={()=>completeReceipt(item.receipt_id)}>Add date</button>}{editing===item.id ? null : <button className="text-button" onClick={()=>startEdit(item)}>Edit</button>}<button className="danger-button" onClick={()=>deleteExpense(item.id)}>Delete</button></div></td></tr>)}</tbody></table></div>;
}

function InsightsView({data}) {
  if (Array.isArray(data)) return <section className="panel"><pre>{JSON.stringify(data,null,2)}</pre></section>;
  if (!data || typeof data !== "object") return <Empty title="No insight data" text="The API did not return a recognized insight object."/>;
  const entries = Object.entries(data).filter(([,v]) => v === null || ["string","number","boolean"].includes(typeof v));
  const lists = Object.entries(data).filter(([,v]) => Array.isArray(v));
  return <div className="insights-grid">{entries.map(([key,value])=><div className="stat-card" key={key}><div className="stat-top"><span>{key.replaceAll("_"," ")}</span><span className="stat-icon">✦</span></div><div className="insight-value">{value === null ? "—" : String(value)}</div></div>)}{lists.map(([key,value])=><section className="panel" key={key}><h2>{key.replaceAll("_"," ")}</h2><pre>{JSON.stringify(value,null,2)}</pre></section>)}{!entries.length&&!lists.length&&<section className="panel"><pre>{JSON.stringify(data,null,2)}</pre></section>}</div>;
}

export default App;