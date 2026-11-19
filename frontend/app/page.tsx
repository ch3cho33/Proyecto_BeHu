"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  (process.env.NODE_ENV === "production" ? "/api/v1" : "http://127.0.0.1:8000/api/v1");

type Role = "SENIOR" | "JUNIOR";
type View = "inicio" | "movimientos" | "presupuesto" | "metas" | "familia" | "aprende" | "mini";
type User = { nombres: string; apellidos: string; email: string; rol: Role; moneda_preferida?: string };
type Account = {
  saldo: string;
  saldo_congelado?: string;
  saldo_disponible?: string;
  moneda: string;
  tipo: string;
  limite_gasto_diario?: string | null;
  tarjeta_bloqueada?: boolean;
};
type Move = {
  id: string;
  tipo: string;
  monto: string;
  categoria?: string | null;
  descripcion?: string | null;
  created_at: string;
  is_impulsive?: boolean;
  metodo_pago?: string | null;
  bucket?: string | null;
};
type Goal = { id: string; nombre: string; monto_actual: string; monto_objetivo: string; porcentaje: string };
type Junior = { cuenta_junior_id: string; nombres: string; apellidos: string; saldo: string; email: string };
type Invite = { id: string; senior_nombre: string; initial_budget: string; estado: string };
type Score = { puntaje: number; nivel: string };
type Lesson = { id: string; titulo: string; resumen: string; pregunta: string; opciones: string[]; completado: boolean; insignia: string };
type Advice = { resumen: string; recomendaciones: string[] };
type Alert = { tipo: string; junior_nombre: string; mensaje: string; sugerencia: string };
type Activity = { id: string; categoria?: string | null; metodo_pago?: string | null; fecha: string; monto: string; is_impulsive: boolean; es_hormiga: boolean; descripcion?: string | null };
type Budget = {
  ingresos: string;
  necesidades: { objetivo: string; real: string };
  deseos: { objetivo: string; real: string };
  ahorro: { objetivo: string; real: string };
};
type Nudge = { mensaje: string; monto: string; categoria: string; metodo: string; bucket: string; notas: string };

const NAV: { id: View; label: string; seniorOnly?: boolean }[] = [
  { id: "inicio", label: "Inicio" },
  { id: "movimientos", label: "Movimientos" },
  { id: "presupuesto", label: "50/30/20" },
  { id: "metas", label: "Metas" },
  { id: "familia", label: "Familia", seniorOnly: true },
  { id: "aprende", label: "Aprende" },
  { id: "mini", label: "BeHu Mini" },
];

function money(value: string | number, currency = "COP") {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value) || 0);
}

function errorMessage(status: number, body: string): string {
  let detail: unknown = body;
  try {
    detail = body ? (JSON.parse(body).detail ?? JSON.parse(body)) : body;
  } catch {
    detail = body;
  }
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const record = detail as { mensaje?: string; code?: string };
    return record.mensaje || record.code || JSON.stringify(detail);
  }
  return `HTTP ${status}`;
}

async function api<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.text();
  if (!response.ok) {
    const error = new Error(errorMessage(response.status, body)) as Error & { payload?: unknown; status?: number };
    error.status = response.status;
    try {
      error.payload = body ? JSON.parse(body).detail : undefined;
    } catch {
      error.payload = body;
    }
    throw error;
  }
  return (body ? JSON.parse(body) : {}) as T;
}

function securePassword(value: string) {
  return value.length >= 8 && /[A-Z]/.test(value) && /[a-z]/.test(value) && /\d/.test(value);
}

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [view, setView] = useState<View>("inicio");
  const [email, setEmail] = useState("senior@behu.test");
  const [password, setPassword] = useState("BeHuSenior1!");
  const [nombres, setNombres] = useState("");
  const [apellidos, setApellidos] = useState("");
  const [rol, setRol] = useState<Role>("SENIOR");
  const [moneda, setMoneda] = useState("COP");
  const [error, setError] = useState("");
  const [account, setAccount] = useState<Account | null>(null);
  const [moves, setMoves] = useState<Move[]>([]);
  const [score, setScore] = useState<Score | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [juniors, setJuniors] = useState<Junior[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [nudge, setNudge] = useState<Nudge | null>(null);
  const [chat, setChat] = useState<{ role: "user" | "mini"; text: string }[]>([]);

  const currency = account?.moneda || user?.moneda_preferida || "COP";
  const nav = NAV.filter((item) => user?.rol === "SENIOR" || !item.seniorOnly);

  async function refresh(nextToken: string, nextUser: User) {
    const me = await api<{ account: Account; movimientos: Move[] }>("/accounts/me", nextToken);
    setAccount(me.account);
    setMoves(me.movimientos);
    setScore(await api<Score>("/scoring/me", nextToken).catch(() => null));
    setGoals(await api<Goal[]>("/goals", nextToken).catch(() => []));
    setBudget(await api<Budget>("/budgets/50-30-20", nextToken).catch(() => null));
    setLessons(await api<Lesson[]>("/education/modules", nextToken).catch(() => []));
    if (nextUser.rol === "JUNIOR") {
      setInvites(await api<Invite[]>("/supervision/invitations", nextToken).catch(() => []));
      setJuniors([]);
      setAlerts([]);
    } else {
      setJuniors(await api<Junior[]>("/supervision/juniors", nextToken).catch(() => []));
      setAlerts(await api<Alert[]>("/ai/parental-alerts", nextToken).catch(() => []));
      setInvites([]);
    }
  }

  useEffect(() => {
    if (token && user) {
      refresh(token, user).catch((err: Error) => setError(err.message));
    }
  }, [token, user]);

  async function onAuth(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (mode === "register" && !securePassword(password)) {
      setError("La contraseña necesita 8 caracteres, mayúscula, minúscula y un número.");
      return;
    }
    try {
      const path = mode === "login" ? "/auth/login" : "/auth/register";
      const payload =
        mode === "login"
          ? { email, password }
          : { email, password, nombres, apellidos, rol, moneda };
      const session = await api<{ access_token: string; user: User }>(path, null, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setToken(session.access_token);
      setUser(session.user);
      setView("inicio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo entrar");
    }
  }

  async function sendMovement(kind: "GASTO" | "INGRESO", form: FormData, force = false) {
    const monto = String(form.get("monto") || "");
    const categoria = String(form.get("categoria") || "COMIDA");
    const metodo = String(form.get("metodo") || "EFECTIVO");
    const bucket = String(form.get("bucket") || "DESEOS");
    const notas = String(form.get("notas") || "");
    try {
      await api("/transactions", token, {
        method: "POST",
        body: JSON.stringify({
          tipo: kind,
          monto,
          categoria,
          metodo_pago: metodo,
          bucket,
          notas,
          recurrencia: "UNICA",
          forzar_confirmacion: force,
        }),
      });
      setNudge(null);
      if (token && user) await refresh(token, user);
    } catch (err) {
      const payload = (err as Error & { payload?: { code?: string; mensaje?: string } }).payload;
      if (payload?.code === "GASTO_IMPULSIVO") {
        setNudge({ mensaje: payload.mensaje || "Gasto impulsivo", monto, categoria, metodo, bucket, notas });
        return;
      }
      setError(err instanceof Error ? err.message : "No se pudo registrar");
    }
  }

  const categorias = useMemo(() => {
    const totals = new Map<string, number>();
    for (const move of moves) {
      if (move.tipo !== "COMPRA") continue;
      const key = move.categoria || "OTRO";
      totals.set(key, (totals.get(key) || 0) + Number(move.monto));
    }
    return [...totals.entries()];
  }, [moves]);

  const donut = categorias.length
    ? `conic-gradient(${categorias
        .map(([_, value], index) => {
          const total = categorias.reduce((sum, item) => sum + item[1], 0) || 1;
          const start = categorias.slice(0, index).reduce((sum, item) => sum + item[1], 0) / total;
          const end = start + value / total;
          const colors = ["#3B82F6", "#10B981", "#F59E0B", "#F43F5E", "#94A3B8"];
          return `${colors[index % colors.length]} ${start * 100}% ${end * 100}%`;
        })
        .join(",")})`
    : "conic-gradient(#1A2338 0 100%)";

  const monthMoves = moves.filter((move) => move.created_at.slice(0, 7) === new Date().toISOString().slice(0, 7));
  const ingresosMes = monthMoves.filter((move) => move.tipo === "INGRESO" || move.tipo === "ASIGNACION_PRESUPUESTO").reduce((sum, move) => sum + Number(move.monto), 0);
  const gastosMes = monthMoves.filter((move) => move.tipo === "COMPRA").reduce((sum, move) => sum + Number(move.monto), 0);
  const scoreTone = !score ? "text-muted" : score.puntaje >= 80 ? "text-success" : score.puntaje >= 60 ? "text-primary" : "text-danger";

  if (!token || !user) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
        <p className="text-sm text-muted">BeHu</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Entra a tu núcleo familiar</h1>
        <p className="mt-2 text-sm text-muted">Behavior & Human Finance. Sandbox, sin cargos reales.</p>
        <form className="mt-8 space-y-3" onSubmit={onAuth}>
          <div className="grid grid-cols-2 gap-2">
            <button type="button" className={mode === "login" ? "btn-primary h-10" : "btn-secondary h-10"} onClick={() => setMode("login")}>Entrar</button>
            <button type="button" className={mode === "register" ? "btn-primary h-10" : "btn-secondary h-10"} onClick={() => setMode("register")}>Crear cuenta</button>
          </div>
          {mode === "register" && (
            <>
              <input className="h-11 w-full rounded-card border border-line bg-surface px-3" placeholder="Nombres" value={nombres} onChange={(event) => setNombres(event.target.value)} required />
              <input className="h-11 w-full rounded-card border border-line bg-surface px-3" placeholder="Apellidos" value={apellidos} onChange={(event) => setApellidos(event.target.value)} required />
              <div className="grid grid-cols-2 gap-2">
                <select className="h-11 rounded-card border border-line bg-surface px-3" value={rol} onChange={(event) => setRol(event.target.value as Role)}>
                  <option value="SENIOR">Senior</option>
                  <option value="JUNIOR">Junior</option>
                </select>
                <select className="h-11 rounded-card border border-line bg-surface px-3" value={moneda} onChange={(event) => setMoneda(event.target.value)}>
                  {["COP", "USD", "EUR", "MXN", "PEN"].map((code) => <option key={code}>{code}</option>)}
                </select>
              </div>
            </>
          )}
          <input className="h-11 w-full rounded-card border border-line bg-surface px-3" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <input className="h-11 w-full rounded-card border border-line bg-surface px-3" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          {error && <p className="text-sm text-danger">{error}</p>}
          <button className="btn-primary h-11 w-full" type="submit">{mode === "login" ? "Entrar" : "Crear cuenta"}</button>
        </form>
        <div className="mt-6 grid grid-cols-2 gap-2">
          <button className="btn-secondary h-10 text-sm" type="button" onClick={() => { setMode("login"); setEmail("senior@behu.test"); setPassword("BeHuSenior1!"); }}>Sandbox Senior</button>
          <button className="btn-secondary h-10 text-sm" type="button" onClick={() => { setMode("login"); setEmail("junior@behu.test"); setPassword("BeHuJunior1!"); }}>Sandbox Junior</button>
        </div>
      </main>
    );
  }

  return (
    <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
      <aside className="hidden border-r border-line bg-elevated md:flex md:flex-col md:px-4 md:py-6">
        <p className="px-3 text-lg font-semibold">BeHu</p>
        <nav className="mt-8 space-y-1">
          {nav.map((item) => (
            <button key={item.id} className={`h-10 w-full rounded-card px-3 text-left text-sm ${view === item.id ? "bg-surface-strong" : "text-muted hover:bg-surface-hover"}`} onClick={() => setView(item.id)} type="button">{item.label}</button>
          ))}
        </nav>
        <div className="mt-auto panel p-3">
          <p className="text-sm font-semibold">{user.nombres.slice(0, 1)}{user.apellidos.slice(0, 1)} · {user.rol}</p>
          <p className={`mt-1 text-sm ${scoreTone}`}>Score {score?.puntaje ?? "—"} {score?.nivel}</p>
          <button className="btn-secondary mt-3 h-9 w-full text-sm" type="button" onClick={() => { setToken(null); setUser(null); }}>Salir</button>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-app px-4 pb-24 pt-6 md:px-8">
        {error && <p className="mb-4 text-sm text-danger">{error}</p>}
        {view === "inicio" && (
          <section className="space-y-4">
            <h1 className="text-2xl font-semibold">Hola, {user.nombres}</h1>
            {invites[0] && (
              <div className="panel flex flex-wrap items-center justify-between gap-3 p-4">
                <p className="text-sm">{invites[0].senior_nombre} te invita. Mesada {money(invites[0].initial_budget, currency)}.</p>
                <div className="flex gap-2">
                  <button className="btn-primary h-9 px-3 text-sm" type="button" onClick={() => api(`/supervision/invitations/${invites[0].id}/respond`, token, { method: "POST", body: JSON.stringify({ accept: true }) }).then(() => refresh(token, user))}>Aceptar</button>
                  <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={() => api(`/supervision/invitations/${invites[0].id}/respond`, token, { method: "POST", body: JSON.stringify({ accept: false }) }).then(() => refresh(token, user))}>Rechazar</button>
                </div>
              </div>
            )}
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Kpi label="Saldo disponible" value={money(account?.saldo_disponible || account?.saldo || 0, currency)} hint={`Congelado ${money(account?.saldo_congelado || 0, currency)}`} />
              <Kpi label="Ingresos del mes" value={money(ingresosMes, currency)} />
              <Kpi label="Gastos del mes" value={money(gastosMes, currency)} />
              <Kpi label="Score BeHu" value={String(score?.puntaje ?? "—")} hint={score?.nivel} tone={scoreTone} />
            </div>
            <div className="grid gap-3 lg:grid-cols-[220px_1fr]">
              <div className="panel flex items-center gap-4 p-4">
                <div className="h-28 w-28 rounded-full" style={{ background: donut }} />
                <div className="text-sm text-muted">{categorias.map(([name]) => name).join(" · ") || "Sin gastos"}</div>
              </div>
              <div className="panel p-4">
                <p className="text-sm text-muted">Tendencia de la semana</p>
                <div className="mt-4 flex h-28 items-end gap-2">
                  {Array.from({ length: 7 }, (_, day) => {
                    const total = moves.filter((move) => move.tipo === "COMPRA" && new Date(move.created_at).getDay() === day).reduce((sum, move) => sum + Number(move.monto), 0);
                    const max = Math.max(...Array.from({ length: 7 }, (_, index) => moves.filter((move) => move.tipo === "COMPRA" && new Date(move.created_at).getDay() === index).reduce((sum, move) => sum + Number(move.monto), 0)), 1);
                    return <div key={day} className="flex-1 rounded-t-behu bg-primary" style={{ height: `${Math.max(8, (total / max) * 100)}%` }} />;
                  })}
                </div>
              </div>
            </div>
          </section>
        )}
        {view === "movimientos" && (
          <MovementForm currency={currency} onSubmit={sendMovement} moves={moves} />
        )}
        {view === "presupuesto" && budget && (
          <section className="space-y-3">
            <h1 className="text-2xl font-semibold">Regla 50/30/20</h1>
            <Bar label="Necesidades 50%" real={budget.necesidades.real} goal={budget.necesidades.objetivo} />
            <Bar label="Deseos 30%" real={budget.deseos.real} goal={budget.deseos.objetivo} />
            <Bar label="Ahorro 20%" real={budget.ahorro.real} goal={budget.ahorro.objetivo} />
            <p className="text-sm text-muted">Ingresos del mes {money(budget.ingresos, currency)}</p>
          </section>
        )}
        {view === "metas" && (
          <Goals token={token} goals={goals} currency={currency} onDone={() => refresh(token, user)} />
        )}
        {view === "familia" && user.rol === "SENIOR" && (
          <Family token={token} juniors={juniors} alerts={alerts} onDone={() => refresh(token, user)} />
        )}
        {view === "aprende" && <Learn token={token} lessons={lessons} onDone={() => refresh(token, user)} />}
        {view === "mini" && (
          <Mini
            role={user.rol}
            advice={advice}
            chat={chat}
            onAsk={async (pregunta) => {
              setChat((items) => [...items, { role: "user", text: pregunta }]);
              const result = await api<Advice>("/ai/consult", token, { method: "POST", body: JSON.stringify({ pregunta }) });
              setAdvice(result);
              setChat((items) => [...items, { role: "mini", text: result.recomendaciones.join(" ") }]);
            }}
          />
        )}
      </main>
      <nav className="fixed inset-x-0 bottom-0 grid grid-cols-4 border-t border-line bg-elevated md:hidden">
        {nav.slice(0, 4).map((item) => (
          <button key={item.id} className="h-14 text-xs text-muted" type="button" onClick={() => setView(item.id)}>{item.label}</button>
        ))}
      </nav>
      {nudge && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/60 px-4">
          <div className="panel w-full max-w-md border-warning p-5">
            <p className="text-sm font-semibold text-warning">BeHu Mini pausó esta compra</p>
            <p className="mt-2 text-sm text-muted">{nudge.mensaje}</p>
            <div className="mt-4 flex gap-2">
              <button className="btn-secondary h-10 flex-1" type="button" onClick={() => setNudge(null)}>Cancelar compra</button>
              <button
                className="h-10 flex-1 rounded-card bg-warning font-semibold text-bg"
                type="button"
                onClick={() => sendMovement("GASTO", formDataFrom(nudge), true)}
              >Confirmar de todas formas</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formDataFrom(nudge: Nudge) {
  const form = new FormData();
  form.set("monto", nudge.monto);
  form.set("categoria", nudge.categoria);
  form.set("metodo", nudge.metodo);
  form.set("bucket", nudge.bucket);
  form.set("notas", nudge.notas);
  return form;
}

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: string }) {
  return (
    <article className="panel p-4">
      <p className="text-xs uppercase tracking-wide text-dim">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone || ""}`}>{value}</p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </article>
  );
}

function Bar({ label, real, goal }: { label: string; real: string; goal: string }) {
  const width = Math.min(100, (Number(real) / Math.max(Number(goal), 1)) * 100);
  return (
    <article className="panel p-4">
      <div className="flex justify-between text-sm"><span>{label}</span><span className="text-muted">{real} / {goal}</span></div>
      <div className="mt-3 h-2 rounded-full bg-surface-strong"><div className="h-2 rounded-full bg-primary" style={{ width: `${width}%` }} /></div>
    </article>
  );
}

function MovementForm({ currency, moves, onSubmit }: { currency: string; moves: Move[]; onSubmit: (kind: "GASTO" | "INGRESO", form: FormData) => void }) {
  const [kind, setKind] = useState<"GASTO" | "INGRESO">("GASTO");
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Movimientos</h1>
      <form className="panel space-y-3 p-4" onSubmit={(event) => { event.preventDefault(); onSubmit(kind, new FormData(event.currentTarget)); }}>
        <div className="grid grid-cols-2 gap-2">
          <button className={kind === "GASTO" ? "btn-primary h-10" : "btn-secondary h-10"} type="button" onClick={() => setKind("GASTO")}>Gasto</button>
          <button className={kind === "INGRESO" ? "btn-primary h-10" : "btn-secondary h-10"} type="button" onClick={() => setKind("INGRESO")}>Ingreso</button>
        </div>
        <input name="monto" className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder={`Monto ${currency}`} required />
        <div className="flex flex-wrap gap-2 text-sm">
          {["COMIDA", "ENTRETENIMIENTO", "TRANSPORTE", "EDUCACION", "ROPA"].map((item) => (
            <label key={item} className="rounded-card border border-line px-3 py-2"><input className="mr-2" type="radio" name="categoria" value={item} defaultChecked={item === "COMIDA"} />{item}</label>
          ))}
        </div>
        <select name="metodo" className="h-11 w-full rounded-card border border-line bg-bg px-3">
          {["EFECTIVO", "TARJETA_DEBITO", "TARJETA_CREDITO", "TRANSFERENCIA"].map((item) => <option key={item}>{item}</option>)}
        </select>
        <select name="bucket" className="h-11 w-full rounded-card border border-line bg-bg px-3">
          <option value="NECESIDADES">Necesidades</option>
          <option value="DESEOS">Deseos</option>
          <option value="AHORRO">Ahorro</option>
        </select>
        <input name="notas" className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Nota" />
        <button className="btn-primary h-11 w-full" type="submit">Registrar</button>
      </form>
      <ul className="space-y-2">
        {moves.slice(0, 8).map((move) => (
          <li key={move.id} className="panel flex items-center justify-between p-3 text-sm">
            <span>{move.descripcion || move.tipo}{move.is_impulsive ? " · impulsivo" : ""}</span>
            <span>{money(move.monto, currency)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Goals({ token, goals, currency, onDone }: { token: string; goals: Goal[]; currency: string; onDone: () => Promise<void> }) {
  const [nombre, setNombre] = useState("Meta");
  const [monto, setMonto] = useState("50000");
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">Saldo congelado</h1>
      <form className="panel grid gap-2 p-4 sm:grid-cols-[1fr_140px_auto]" onSubmit={async (event) => {
        event.preventDefault();
        const limite = new Date();
        limite.setDate(limite.getDate() + 45);
        await api("/goals", token, { method: "POST", body: JSON.stringify({ nombre, monto_objetivo: monto, fecha_limite: limite.toISOString().slice(0, 10) }) });
        await onDone();
      }}>
        <input className="h-11 rounded-card border border-line bg-bg px-3" value={nombre} onChange={(event) => setNombre(event.target.value)} />
        <input className="h-11 rounded-card border border-line bg-bg px-3" value={monto} onChange={(event) => setMonto(event.target.value)} />
        <button className="btn-primary h-11 px-4" type="submit">Crear</button>
      </form>
      {goals.map((goal) => (
        <article key={goal.id} className="panel p-4">
          <p className="font-semibold">🎯 {goal.nombre}</p>
          <p className="mt-1 text-sm text-muted">{money(goal.monto_actual, currency)} de {money(goal.monto_objetivo, currency)} protegidos</p>
          <div className="mt-3 h-2 rounded-full bg-surface-strong"><div className="h-2 rounded-full bg-success" style={{ width: `${Math.min(100, Number(goal.porcentaje))}%` }} /></div>
          <button className="btn-secondary mt-3 h-9 px-3 text-sm" type="button" onClick={async () => { await api(`/goals/${goal.id}/deposit`, token, { method: "POST", body: JSON.stringify({ monto: "5000" }) }); await onDone(); }}>Abonar 5.000</button>
        </article>
      ))}
    </section>
  );
}

function Family({ token, juniors, alerts, onDone }: { token: string; juniors: Junior[]; alerts: Alert[]; onDone: () => Promise<void> }) {
  const [activity, setActivity] = useState<Activity[]>([]);
  const [openJunior, setOpenJunior] = useState("");
  const [email, setEmail] = useState("");
  const [mesada, setMesada] = useState("20000");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("BeHuJunior2!");
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Gestión familiar</h1>
      <form className="panel space-y-2 p-4" onSubmit={async (event) => {
        event.preventDefault();
        const body = { email, initial_budget: mesada, daily_limit: "50000", weekly_limit: "200000", monthly_limit: "500000" };
        try {
          await api("/supervision/invite", token, { method: "POST", body: JSON.stringify(body) });
        } catch (err) {
          const message = err instanceof Error ? err.message : "";
          if (!message.toLowerCase().includes("no existe")) throw err;
          await api("/supervision/create-junior", token, { method: "POST", body: JSON.stringify({ ...body, nombres: nombre || "Junior", password: clave }) });
        }
        await onDone();
      }}>
        <p className="text-sm text-muted">Invita por correo. Si no existe, se crea y queda vinculado.</p>
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="correo@behu.test" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Nombre si hay que crearlo" value={nombre} onChange={(event) => setNombre(event.target.value)} />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Mesada" value={mesada} onChange={(event) => setMesada(event.target.value)} />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Clave temporal" value={clave} onChange={(event) => setClave(event.target.value)} />
        <button className="btn-primary h-11 w-full" type="submit">Enviar invitación o crear</button>
      </form>
      {alerts.map((alert) => (
        <article key={alert.tipo + alert.junior_nombre} className="panel border-warning p-4 text-sm">
          <p className="font-semibold text-warning">{alert.tipo}</p>
          <p className="mt-1">{alert.mensaje}</p>
          <p className="mt-1 text-muted">{alert.sugerencia}</p>
        </article>
      ))}
      {juniors.map((junior) => (
        <article key={junior.cuenta_junior_id} className="panel space-y-2 p-4">
          <p className="font-semibold">{junior.nombres} {junior.apellidos}</p>
          <p className="text-sm text-muted">{junior.email} · {money(junior.saldo)}</p>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={async () => { await api("/transfers/budget", token, { method: "POST", body: JSON.stringify({ cuenta_junior_id: junior.cuenta_junior_id, monto: "10000", descripcion: "Mesada" }) }); await onDone(); }}>Mesada 10.000</button>
            <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={() => api(`/supervision/juniors/${junior.cuenta_junior_id}/card-status`, token, { method: "PATCH", body: JSON.stringify({ bloqueada: true }) })}>Bloquear tarjeta</button>
            <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={async () => { setOpenJunior(junior.cuenta_junior_id); setActivity(await api<Activity[]>(`/supervision/juniors/${junior.cuenta_junior_id}/activity`, token)); }}>Ver movimientos</button>
          </div>
          {openJunior === junior.cuenta_junior_id && activity.length > 0 && (
            <ul className="space-y-1 text-sm text-muted">
              {activity.slice(0, 5).map((item) => (
                <li key={item.id}>{item.categoria || "Movimiento"} · {item.metodo_pago || "sin método"} · {item.is_impulsive ? "impulsivo" : "ok"}{item.es_hormiga ? " · hormiga" : ""}</li>
              ))}
            </ul>
          )}
        </article>
      ))}
    </section>
  );
}

function Learn({ token, lessons, onDone }: { token: string; lessons: Lesson[]; onDone: () => Promise<void> }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">Aprende</h1>
      {note && <p className="text-sm text-warning">{note}</p>}
      {lessons.map((lesson) => (
        <article key={lesson.id} className="panel p-4">
          <p className="font-semibold">{lesson.titulo}</p>
          <p className="mt-1 text-sm text-muted">{lesson.resumen}</p>
          <p className="mt-3 text-sm">{lesson.pregunta}</p>
          <div className="mt-2 space-y-1">
            {lesson.opciones.map((opcion, index) => (
              <label key={opcion} className="block text-sm"><input type="radio" name={lesson.id} className="mr-2" onChange={() => setAnswers({ ...answers, [lesson.id]: String(index) })} />{opcion}</label>
            ))}
          </div>
          <button className="btn-primary mt-3 h-9 px-3 text-sm" type="button" disabled={lesson.completado} onClick={async () => {
            try {
              await api(`/education/modules/${lesson.id}/complete`, token, { method: "POST", body: JSON.stringify({ respuesta: answers[lesson.id] || "1" }) });
              setNote(`Insignia ${lesson.insignia}. El score sube 8 puntos.`);
              await onDone();
            } catch (err) {
              setNote(err instanceof Error ? err.message : "Respuesta incorrecta");
            }
          }}>{lesson.completado ? "Completada" : "Responder"}</button>
        </article>
      ))}
    </section>
  );
}

function Mini({ role, advice, chat, onAsk }: { role: Role; advice: Advice | null; chat: { role: "user" | "mini"; text: string }[]; onAsk: (pregunta: string) => Promise<void> }) {
  const chips = role === "SENIOR"
    ? ["¿Cuánto fondo de emergencia necesito?", "¿Me alcanza para un CDT?", "¿Cómo va la regla 50/30/20?"]
    : ["¿Cuánto abono a mi meta?", "¿Tengo gastos hormiga?", "¿Cómo subo el Score?"];
  const [text, setText] = useState("");
  return (
    <section className="space-y-3">
      <h1 className="text-2xl font-semibold">BeHu Mini</h1>
      <div className="flex flex-wrap gap-2">
        {chips.map((chip) => <button key={chip} className="btn-secondary h-9 px-3 text-sm" type="button" onClick={() => onAsk(chip)}>{chip}</button>)}
      </div>
      <div className="panel min-h-48 space-y-3 p-4">
        {chat.length === 0 && <p className="text-sm text-muted">{advice?.resumen || "Pregunta con tus números reales: saldo, metas y límites."}</p>}
        {chat.map((item, index) => <p key={index} className={item.role === "user" ? "text-sm" : "text-sm text-muted"}>{item.text}</p>)}
      </div>
      <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); if (text.trim()) onAsk(text.trim()); setText(""); }}>
        <input className="h-11 flex-1 rounded-card border border-line bg-surface px-3" value={text} onChange={(event) => setText(event.target.value)} placeholder="Escribe tu pregunta" />
        <button className="btn-primary h-11 px-4" type="submit">Enviar</button>
      </form>
    </section>
  );
}
