"use client";

import { useEffect, useMemo, useState } from "react";

import { Academy } from "./academy";
import { MovementDesk, QuickActions, type Draft } from "./flow";
import { PublicSite } from "./landing";
import { Donut, ScoreGauge, Skeleton, Toasts, VirtualCard, labelCategory, type Toast } from "./ui";
import { Bell, BookOpen, Home, LogOut, PieChart, Settings as SettingsIcon, Sparkles, Target, Users, Wallet } from "lucide-react";

const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  (process.env.NODE_ENV === "production" ? "/api/v1" : "http://127.0.0.1:8000/api/v1");

type Role = "SENIOR" | "JUNIOR";
type View = "inicio" | "movimientos" | "presupuesto" | "metas" | "familia" | "aprende" | "mini" | "ajustes";
type User = { nombres: string; apellidos: string; email: string; rol: Role; moneda_preferida?: string; kyc_status?: string; ingreso_mensual_estimado?: string | null };
type Note = { id: string; tipo: string; severity: string; titulo: string; detalle: string; sugerencia: string; leida: boolean };
type Category = { codigo: string; nombre: string; origen: string };
type Account = {
  account_id?: string;
  saldo: string;
  saldo_congelado?: string;
  saldo_disponible?: string;
  moneda: string;
  tipo: string;
  limite_gasto_diario?: string | null;
  limite_gasto_semanal?: string | null;
  limite_gasto_mensual?: string | null;
  tarjeta_bloqueada?: boolean;
};
type Move = {
  id: string;
  tipo: string;
  monto: string;
  categoria?: string | null;
  comercio?: string | null;
  descripcion?: string | null;
  created_at: string;
  is_impulsive?: boolean;
  metodo_pago?: string | null;
  bucket?: string | null;
};
type Goal = { id: string; nombre: string; monto_actual: string; monto_objetivo: string; porcentaje: string };
type Junior = {
  supervision_id: string;
  cuenta_junior_id: string;
  nombres: string;
  apellidos: string;
  saldo: string;
  email: string;
  limite_gasto_diario?: string | null;
  limite_gasto_semanal?: string | null;
  limite_gasto_mensual?: string | null;
  tarjeta_bloqueada?: boolean;
};
type Invite = {
  id: string;
  senior_nombre: string;
  junior_nombre?: string;
  junior_email?: string;
  initial_budget: string;
  daily_limit: string;
  weekly_limit: string;
  monthly_limit: string;
  estado: string;
};
type Score = { puntaje: number; nivel: string; factores_positivos?: { etiqueta: string; puntos: number }[]; factores_negativos?: { etiqueta: string; puntos: number }[] };
type Lesson = { id: string; titulo: string; resumen: string; pregunta: string; opciones: string[]; completado: boolean; insignia: string; categoria?: string; duracion_min?: number };
type Advice = { resumen: string; recomendaciones?: string[]; reply?: string; response?: string; insights?: string[] };
type Alert = { tipo: string; junior_nombre: string; mensaje: string; sugerencia: string; severity?: string; badge?: string | null };
type Activity = { id: string; categoria?: string | null; metodo_pago?: string | null; fecha: string; monto: string; is_impulsive: boolean; es_hormiga: boolean; descripcion?: string | null };
type Budget = {
  ingresos: string;
  necesidades: { objetivo: string; real: string };
  deseos: { objetivo: string; real: string };
  ahorro: { objetivo: string; real: string };
};
type Nudge = { mensaje: string; draft: Draft };

const NAV: { id: View; label: string; seniorOnly?: boolean; icon: typeof Home }[] = [
  { id: "inicio", label: "Inicio", icon: Home },
  { id: "movimientos", label: "Movimientos", icon: Wallet },
  { id: "presupuesto", label: "50/30/20", icon: PieChart },
  { id: "metas", label: "Metas", icon: Target },
  { id: "familia", label: "Familia", seniorOnly: true, icon: Users },
  { id: "aprende", label: "Aprende", icon: BookOpen },
  { id: "mini", label: "BeHu Mini", icon: Sparkles },
  { id: "ajustes", label: "Ajustes", icon: SettingsIcon },
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
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
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

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<View>("inicio");
  const [error, setError] = useState("");
  const [account, setAccount] = useState<Account | null>(null);
  const [moves, setMoves] = useState<Move[]>([]);
  const [score, setScore] = useState<Score | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [juniors, setJuniors] = useState<Junior[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [sent, setSent] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [unlink, setUnlink] = useState<Junior | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [budget, setBudget] = useState<Budget | null>(null);
  const [nudge, setNudge] = useState<Nudge | null>(null);
  const [pattern, setPattern] = useState<Nudge | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [moveTab, setMoveTab] = useState("Historial");
  const [llave, setLlave] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [bellOpen, setBellOpen] = useState(false);
  const [deskRequest, setDeskRequest] = useState<{ action: "gasto" | "ingreso" | "enviar" | "qr"; id: number } | null>(null);

  const currency = account?.moneda || user?.moneda_preferida || "COP";
  const nav = NAV.filter((item) => user?.rol === "SENIOR" || !item.seniorOnly);

  function toast(tone: Toast["tone"], text: string) {
    const id = Date.now() + Math.random();
    setToasts((items) => [...items, { id, tone, text }]);
    setTimeout(() => setToasts((items) => items.filter((item) => item.id !== id)), 3200);
  }

  async function refresh(nextToken: string, nextUser: User) {
    setLoading(true);
    try {
    const me = await api<{ account: Account; movimientos: Move[]; llave?: string }>("/accounts/me", nextToken);
    setAccount(me.account);
    setMoves(me.movimientos);
    setLlave(me.llave || "");
    setScore(await api<Score>("/scoring/me", nextToken).catch(() => null));
    setGoals(await api<Goal[]>("/goals", nextToken).catch(() => []));
    setBudget(await api<Budget>("/budgets/50-30-20", nextToken).catch(() => null));
    setLessons(await api<Lesson[]>("/education/modules", nextToken).catch(() => []));
    if (nextUser.rol === "JUNIOR") {
      setInvites(await api<Invite[]>("/supervision/invitations", nextToken).catch(() => []));
      setJuniors([]);
      setAlerts([]);
      setSent([]);
    } else {
      setJuniors(await api<Junior[]>("/supervision/juniors", nextToken).catch(() => []));
      setAlerts(await api<Alert[]>("/ai/parental-alerts", nextToken).catch(() => []));
      setSent(await api<Invite[]>("/supervision/invitations/sent", nextToken).catch(() => []));
      setInvites([]);
    }
    setNotes(await api<Note[]>("/notifications", nextToken).catch(() => []));
    setCategories(await api<Category[]>("/categories", nextToken).catch(() => []));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (token && user) {
      refresh(token, user).catch((err: Error) => setError(err.message));
    }
  }, [token, user]);

  useEffect(() => {
    const saved = window.localStorage.getItem("behu-theme");
    const next = saved === "light" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
  }, []);

  function switchTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    window.localStorage.setItem("behu-theme", next);
    document.documentElement.dataset.theme = next;
  }

  async function enter(email: string, password: string) {
    setError("");
    try {
      const session = await api<{ access_token: string; user: User }>("/auth/login", null, { method: "POST", body: JSON.stringify({ email, password }) });
      setToken(session.access_token);
      setUser(session.user);
      setView("inicio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo entrar");
    }
  }

  async function join(payload: { nombres: string; apellidos: string; email: string; password: string; rol: Role; moneda: string; ingreso_mensual_estimado?: string }) {
    setError("");
    try {
      const session = await api<{ access_token: string; user: User }>("/auth/register", null, { method: "POST", body: JSON.stringify(payload) });
      setToken(session.access_token);
      setUser(session.user);
      setView("inicio");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta");
    }
  }

  async function sendMovement(kind: "GASTO" | "INGRESO", draft: Draft, force = false) {
    try {
      const result = await api<{ redondeo?: string; meta_redondeo?: string | null }>("/transactions", token, {
        method: "POST",
        body: JSON.stringify({
          tipo: kind,
          monto: draft.monto,
          categoria: draft.categoria,
          metodo_pago: draft.metodo,
          bucket: draft.bucket,
          notas: draft.notas,
          recurrencia: "UNICA",
          forzar_confirmacion: force,
          redondear_ahorro: draft.redondear,
        }),
      });
      setNudge(null);
      setPattern(null);
      const extra = Number(result.redondeo) > 0 ? ` + ${money(result.redondeo || 0, currency)} enviados a ${result.meta_redondeo} por redondeo automático` : "";
      toast("ok", (kind === "GASTO" ? "Compra registrada" : "Ingreso simulado registrado") + extra);
      if (token && user) {
        await refresh(token, user);
        const incoming = await api<Note[]>("/notifications", token).catch(() => []);
        const fresh = incoming.find((note) => !note.leida && note.severity === "high" && !notes.some((item) => item.id === note.id));
        if (fresh) toast("danger", `${fresh.titulo}. ${fresh.detalle}`);
        setNotes(incoming);
      }
      return result;
    } catch (err) {
      const payload = (err as Error & { payload?: { code?: string; mensaje?: string } }).payload;
      if (payload?.code === "GASTO_IMPULSIVO") {
        setNudge({ mensaje: payload.mensaje || "Gasto impulsivo", draft });
        return;
      }
      if (payload?.code === "PATRON_ANOMALO") {
        setPattern({ mensaje: payload.mensaje || "Patrón de gasto", draft });
        if (token && user) {
          const incoming = await api<Note[]>("/notifications", token).catch(() => []);
          setNotes(incoming);
        }
        return;
      }
      toast("danger", err instanceof Error ? err.message : "No se pudo registrar");
    }
  }

  const categorias = useMemo(() => {
    const totals = new Map<string, number>();
    for (const move of moves) {
      if (move.tipo !== "COMPRA" || move.created_at.slice(0, 7) !== new Date().toISOString().slice(0, 7)) continue;
      const key = labelCategory(move.categoria || "OTRO");
      totals.set(key, (totals.get(key) || 0) + Number(move.monto));
    }
    return [...totals.entries()].map(([label, value]) => ({ label, value }));
  }, [moves]);

  const week = useMemo(() => {
    const labels = ["D", "L", "M", "X", "J", "V", "S"];
    const limit = Number(account?.limite_gasto_diario || 0);
    return labels.map((label, day) => {
      const sameDay = moves.filter((move) => move.tipo === "COMPRA" && new Date(move.created_at).getDay() === day);
      return {
        label,
        spent: sameDay.reduce((sum, move) => sum + Number(move.monto), 0),
        limit,
        impulsive: sameDay.some((move) => move.is_impulsive),
      };
    });
  }, [moves, account?.limite_gasto_diario]);

  const monthMoves = moves.filter((move) => move.created_at.slice(0, 7) === new Date().toISOString().slice(0, 7));
  const ingresosMes = monthMoves.filter((move) => move.tipo === "INGRESO" || move.tipo === "ASIGNACION_PRESUPUESTO").reduce((sum, move) => sum + Number(move.monto), 0);
  const gastosMes = monthMoves.filter((move) => move.tipo === "COMPRA").reduce((sum, move) => sum + Number(move.monto), 0);
  const scoreTone = !score ? "text-muted" : score.puntaje >= 80 ? "text-success" : score.puntaje >= 60 ? "text-primary" : "text-danger";

  if (!token || !user) {
    return <PublicSite error={error} onLogin={enter} onRegister={join} />;
  }

  const unread = notes.filter((note) => !note.leida).length;

  const pendingInvites = invites.filter((invite) => invite.estado === "PENDING").length;
  const attention = (id: View) => (id === "familia" && alerts.length > 0 ? alerts.length : id === "inicio" && pendingInvites > 0 ? pendingInvites : 0);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[288px_minmax(0,1fr)]">
      <aside className="hidden lg:block">
        <div className="nav-dock m-4 flex h-[calc(100vh-2rem)] w-[256px] flex-col rounded-[24px] border border-[#1E293B] bg-[#0F1422]/85 shadow-[0_8px_32px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <div className="flex items-center gap-3 px-4 pb-2 pt-4">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-[#111726] shadow-[0_0_24px_rgba(59,130,246,0.35)]">
              <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
                <rect x="2" y="3" width="6" height="16" rx="2" fill="#10B981" />
                <rect x="11" y="7" width="9" height="12" rx="2" fill="#3B82F6" />
              </svg>
            </span>
            <div>
              <p className="text-base font-semibold tracking-tight">BeHu</p>
              <p className="text-[10px] font-semibold tracking-[0.16em] text-[#64748B]">{user.rol === "SENIOR" ? "NEOBANK" : "PERSONAL"}</p>
            </div>
            <button className="ml-auto text-[10px] text-[#94A3B8]" type="button" onClick={switchTheme}>{theme === "dark" ? "Claro" : "Oscuro"}</button>
            <button className="relative grid h-9 w-9 place-items-center rounded-xl text-[#94A3B8]" type="button" onClick={() => setBellOpen(true)} aria-label="Notificaciones">
              <Bell size={16} />
              {unread > 0 && <span className="absolute right-1 top-1 grid h-4 min-w-4 place-items-center rounded-full bg-[#F43F5E] px-1 text-[9px] text-white">{unread}</span>}
            </button>
          </div>
          <nav className="mt-3 flex-1 space-y-1 overflow-y-auto px-3">
            {nav.map((item) => {
              const active = view === item.id;
              const count = attention(item.id);
              return (
                <button
                  key={item.id}
                  className={`flex h-11 w-full items-center gap-3 rounded-2xl px-3 text-left text-sm transition duration-200 hover:translate-x-0.5 ${active ? "bg-[#1A2338] text-white shadow-[inset_3px_0_0_#3B82F6]" : "text-[#94A3B8] hover:bg-[#161E31]"}`}
                  onClick={() => setView(item.id)}
                  type="button"
                >
                  <item.icon size={16} className={active ? "text-[#3B82F6]" : ""} />
                  <span className="flex-1">{item.label}</span>
                  {count > 0 && <span className="grid h-5 min-w-5 place-items-center rounded-full bg-[#F43F5E] px-1 text-[10px] font-semibold text-white">{count}</span>}
                  {active && <span className="h-1.5 w-1.5 rounded-full bg-[#3B82F6]" />}
                </button>
              );
            })}
          </nav>
          <div className="m-3 rounded-2xl border border-[#1E293B] bg-[#111726] p-3">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-[#3B82F6] to-[#10B981] text-sm font-semibold text-white">{user.nombres.slice(0, 1)}{user.apellidos.slice(0, 1)}</span>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.nombres} {user.apellidos}</p>
                <button className="truncate text-xs text-[#94A3B8]" type="button" onClick={() => { if (!llave) return; navigator.clipboard.writeText(`@${llave}`); toast("ok", "Llave copiada"); }}>{llave ? `@${llave}` : "Sin llave"}</button>
              </div>
            </div>
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-[10px] text-[#94A3B8]"><span>Score BeHu</span><span className={scoreTone}>{score?.puntaje ?? "—"}</span></div>
              <div className="h-1.5 rounded-full bg-[#1A2338]"><div className="h-1.5 rounded-full bg-[#3B82F6]" style={{ width: `${Math.min(100, score?.puntaje ?? 0)}%` }} /></div>
            </div>
            <button className="mt-3 flex h-9 w-full items-center justify-center gap-2 rounded-xl text-sm text-[#94A3B8] transition duration-200 hover:bg-[#1A2338] hover:text-white" type="button" onClick={() => { setToken(null); setUser(null); }}><LogOut size={14} />Cerrar sesión</button>
          </div>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-app px-4 pb-28 pt-6 md:px-8">
        <div className="mb-4 flex justify-end lg:hidden">
          <button className="h-10 rounded-xl border border-[#1E293B] bg-[#111726] px-3 text-xs" type="button" onClick={switchTheme}>{theme === "dark" ? "Modo claro" : "Modo oscuro"}</button>
          <button className="relative grid h-10 w-10 place-items-center rounded-xl border border-[#1E293B] bg-[#111726]" type="button" onClick={() => setBellOpen(true)} aria-label="Notificaciones">
            <Bell size={16} />
            {unread > 0 && <span className="absolute -right-1 -top-1 grid h-4 min-w-4 place-items-center rounded-full bg-[#F43F5E] px-1 text-[9px] text-white">{unread}</span>}
          </button>
        </div>
        {error && <p className="mb-4 text-sm text-danger">{error}</p>}
        {loading && view === "inicio" ? <Skeleton /> : null}
        {view === "inicio" && !loading && (
          <section className="space-y-4">
            <PageHead title={`Hola, ${user.nombres}`} subtitle={`Disponible ${money(account?.saldo_disponible || account?.saldo || 0, currency)} · @${llave || "behu"}`} action="Nuevo movimiento" onAction={() => { setDeskRequest({ action: "gasto", id: Date.now() }); setView("movimientos"); }} />
            <QuickActions onOpen={(action) => { setDeskRequest({ action, id: Date.now() }); setView("movimientos"); }} />
            {invites.map((invite) => (
              <div key={invite.id} className="panel border-primary p-4">
                <p className="text-sm font-semibold">Solicitud familiar de {invite.senior_nombre}</p>
                <p className="mt-1 text-sm text-muted">Mesada {money(invite.initial_budget, currency)}. Límites diario {money(invite.daily_limit, currency)}, semanal {money(invite.weekly_limit, currency)} y mensual {money(invite.monthly_limit, currency)}.</p>
                <div className="mt-3 flex gap-2">
                  <button className="btn-primary h-9 px-3 text-sm" type="button" onClick={() => api(`/supervision/invitations/${invite.id}/respond`, token, { method: "POST", body: JSON.stringify({ accept: true }) }).then(() => { toast("ok", "Invitación aceptada"); return refresh(token, user); })}>Aceptar invitación</button>
                  <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={() => api(`/supervision/invitations/${invite.id}/respond`, token, { method: "POST", body: JSON.stringify({ accept: false }) }).then(() => { toast("warn", "Invitación rechazada"); return refresh(token, user); })}>Rechazar</button>
                </div>
              </div>
            ))}
            <div className="grid gap-3 lg:grid-cols-[280px_1fr]">
              <VirtualCard holder={`${user.nombres} ${user.apellidos}`} accountId={account?.account_id || user.email} frozen={Boolean(account?.tarjeta_bloqueada)} />
              <Kpi label="Saldo disponible" value={money(account?.saldo_disponible || account?.saldo || 0, currency)} hint={`Reservado en metas ${money(account?.saldo_congelado || 0, currency)}`} />
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              <ScoreGauge score={score?.puntaje ?? 0} level={score?.nivel || "Sin datos"} factors={[...(score?.factores_positivos || []), ...(score?.factores_negativos || [])]} />
              <article className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
                <p className="font-semibold">Límites</p>
                <LimitBar label="Semana" real={week.reduce((sum, day) => sum + day.spent, 0)} goal={Number(account?.limite_gasto_semanal || 0)} />
                <LimitBar label="Mes" real={gastosMes} goal={Number(account?.limite_gasto_mensual || 0)} />
              </article>
            </div>
            <div className="grid gap-3 xl:grid-cols-2">
              <Donut slices={categorias} totalLabel={money(gastosMes, currency)} />
              <article className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
                <p className="font-semibold">Últimos movimientos</p>
                {moves.slice(0, 4).map((move) => (
                  <p key={move.id} className="mt-2 flex justify-between text-sm"><span>{move.descripcion || move.comercio || move.tipo}</span><span>{money(move.monto, currency)}</span></p>
                ))}
                {moves.length === 0 && <p className="mt-2 text-sm text-muted">Todavía no hay movimientos.</p>}
              </article>
            </div>
          </section>
        )}
        {view === "movimientos" && (
          <section className="space-y-4">
            <div className="grid gap-2 md:grid-cols-3">
              {[
                ["Historial", "Lista, filtros y registro rápido"],
                ["50/30/20", "Necesidades, deseos y ahorro del mes"],
                ["Extractos", "CSV y comprobante con sello"],
              ].map(([id, copy]) => (
                <button key={id} className={moveTab === id ? "rounded-2xl bg-white p-3 text-left text-[#090D16]" : "rounded-2xl border border-[#1E293B] bg-[#111726] p-3 text-left"} type="button" onClick={() => setMoveTab(id)}>
                  <p className="text-sm font-semibold">{id}</p>
                  <p className="mt-1 text-xs opacity-70">{copy}</p>
                </button>
              ))}
            </div>
            {moveTab === "50/30/20" && budget && (
              <div className="space-y-3">
                <Bar label="Necesidades 50%" real={budget.necesidades.real} goal={budget.necesidades.objetivo} />
                <Bar label="Deseos 30%" real={budget.deseos.real} goal={budget.deseos.objetivo} />
                <Bar label="Ahorro 20%" real={budget.ahorro.real} goal={budget.ahorro.objetivo} />
              </div>
            )}
            {moveTab !== "50/30/20" && (
          <MovementDesk
            moves={moves}
            currency={currency}
            llave={llave}
            juniors={juniors}
            onSpend={(draft, force) => sendMovement("GASTO", draft, Boolean(force))}
            onIncome={(monto) => sendMovement("INGRESO", { monto, categoria: "COMIDA", metodo: "TRANSFERENCIA", bucket: "AHORRO", notas: "Ingreso", redondear: false })}
            onSendBudget={async (cuentaId, monto) => {
              await api("/transfers/budget", token, { method: "POST", body: JSON.stringify({ cuenta_junior_id: cuentaId, monto, descripcion: "Mesada rápida" }) });
              toast("ok", "Mesada enviada");
              if (user) await refresh(token, user);
            }}
            onSendKey={async (destino, monto) => {
              await api("/transfers/key", token, { method: "POST", body: JSON.stringify({ llave: destino, monto, descripcion: "Envío por llave BeHu" }) });
              toast("ok", "Envío por llave registrado");
              if (user) await refresh(token, user);
            }}
            categories={categories.map((item) => ({ codigo: item.codigo, nombre: item.nombre }))}
            onReceipt={(id) => api(`/transactions/${id}/receipt`, token)}
            onCopy={(text) => { navigator.clipboard.writeText(text); toast("ok", "Llave copiada"); }}
            request={deskRequest}
          />
            )}
          </section>
        )}
        {view === "ajustes" && (
          <Settings
            token={token}
            user={user}
            account={account}
            juniors={juniors}
            currency={currency}
            categories={categories}
            onUser={(next) => setUser(next)}
            onDone={async (message) => {
              toast("ok", message);
              await refresh(token, user);
            }}
          />
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
          <Goals token={token} goals={goals} currency={currency} onDone={async () => { toast("ok", "Meta actualizada"); await refresh(token, user); }} />
        )}
        {view === "familia" && user.rol === "SENIOR" && (
          <Family
            token={token}
            juniors={juniors}
            alerts={alerts}
            sent={sent}
            onUnlink={setUnlink}
            onToast={toast}
            onDone={() => refresh(token, user)}
          />
        )}
        {view === "aprende" && <Academy token={token} lessons={lessons} currency={currency} api={api} onDone={async (message) => { toast(message.startsWith("Insignia") ? "ok" : "warn", message); await refresh(token, user); }} />}
        {view === "mini" && (
          <Mini
            role={user.rol}
            currency={currency}
            saldo={money(account?.saldo_disponible || account?.saldo || 0, currency)}
            score={score?.puntaje ?? 0}
            onAsk={async (pregunta) => api<Advice>("/ai/consult", token, { method: "POST", body: JSON.stringify({ message: pregunta }) })}
          />
        )}
      </main>
      <nav className="nav-dock-mobile fixed inset-x-0 bottom-4 z-30 mx-4 grid grid-cols-4 rounded-2xl border border-[#1E293B] bg-[#0F1422]/90 shadow-2xl backdrop-blur-xl lg:hidden" style={{ marginBottom: "env(safe-area-inset-bottom)" }}>
        {nav.slice(0, 4).map((item) => {
          const active = view === item.id;
          const count = attention(item.id);
          return (
            <button key={item.id} className={`relative flex h-14 flex-col items-center justify-center gap-1 text-[10px] transition duration-200 ${active ? "text-[#3B82F6]" : "text-[#94A3B8]"}`} type="button" onClick={() => setView(item.id)}>
              <item.icon size={16} />
              {item.label}
              {count > 0 && <span className="absolute right-3 top-2 h-2 w-2 animate-pulse rounded-full bg-[#F43F5E]" />}
            </button>
          );
        })}
      </nav>
      {bellOpen && (
        <div className="fixed inset-0 z-40 bg-black/50" onClick={() => setBellOpen(false)}>
          <aside className="absolute right-0 top-0 h-full w-full max-w-md overflow-auto border-l border-[#1E293B] bg-[#0F1422] p-5" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Alertas financieras</h2><button className="text-sm text-[#94A3B8]" type="button" onClick={() => setBellOpen(false)}>Cerrar</button></div>
            <div className="mt-4 space-y-3">
              {notes.length === 0 && <p className="text-sm text-[#94A3B8]">No hay alertas abiertas.</p>}
              {notes.map((note) => (
                <article key={note.id} className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4 text-sm">
                  <p className={note.severity === "high" ? "font-semibold text-[#F43F5E]" : note.severity === "medium" ? "font-semibold text-[#F59E0B]" : "font-semibold text-[#3B82F6]"}>{note.titulo}</p>
                  <p className="mt-1">{note.detalle}</p>
                  <p className="mt-1 text-[#94A3B8]">{note.sugerencia}</p>
                  <div className="mt-3 flex gap-2">
                    <button className="btn-secondary h-8 px-3 text-xs" type="button" onClick={async () => { await api(`/notifications/${note.id}/read`, token, { method: "PATCH" }); setNotes((items) => items.map((item) => item.id === note.id ? { ...item, leida: true } : item)); }}>Marcar leída</button>
                    <button className="btn-secondary h-8 px-3 text-xs" type="button" onClick={() => { setBellOpen(false); setView(note.tipo === "INVITACION" || user.rol === "SENIOR" ? "familia" : "mini"); }}>{user.rol === "SENIOR" ? "Gestionar límites" : "Consultar a BeHu Mini"}</button>
                  </div>
                </article>
              ))}
            </div>
          </aside>
        </div>
      )}
      <Toasts items={toasts} />
      {unlink && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/60 px-4">
          <div className="panel w-full max-w-md p-5">
            <p className="font-semibold">Desvincular a {unlink.nombres}</p>
            <p className="mt-2 text-sm text-muted">Esta acción cierra el núcleo familiar. La cuenta Junior sigue existiendo, pero deja de recibir tu supervisión.</p>
            <div className="mt-4 flex gap-2">
              <button className="btn-secondary h-10 flex-1" type="button" onClick={() => setUnlink(null)}>Cancelar</button>
              <button className="h-10 flex-1 rounded-card bg-danger font-semibold text-white" type="button" onClick={async () => {
                await api(`/supervision/link/${unlink.supervision_id}?confirmacion=true`, token, { method: "DELETE" });
                setUnlink(null);
                toast("warn", "Junior desvinculado");
                await refresh(token, user);
              }}>Confirmar desvínculo</button>
            </div>
          </div>
        </div>
      )}
      {pattern && (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/60 px-4">
          <div className="panel w-full max-w-md border-warning p-5">
            <p className="text-sm font-semibold text-warning">Pausa consciente</p>
            <p className="mt-2 text-sm text-muted">{pattern.mensaje}</p>
            <div className="mt-4 flex gap-2">
              <button className="btn-secondary h-10 flex-1" type="button" onClick={() => setPattern(null)}>Pensarlo mejor</button>
              <button className="h-10 flex-1 rounded-card bg-warning font-semibold text-bg" type="button" onClick={() => sendMovement("GASTO", pattern.draft, true)}>Continuar con la compra</button>
            </div>
          </div>
        </div>
      )}
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
                onClick={() => sendMovement("GASTO", nudge.draft, true)}
              >Confirmar de todas formas</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
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

function Family({ token, juniors, alerts, sent, onUnlink, onToast, onDone }: { token: string; juniors: Junior[]; alerts: Alert[]; sent: Invite[]; onUnlink: (junior: Junior) => void; onToast: (tone: Toast["tone"], text: string) => void; onDone: () => Promise<void> }) {
  const [activity, setActivity] = useState<Activity[]>([]);
  const [openJunior, setOpenJunior] = useState("");
  const [email, setEmail] = useState("");
  const [mesada, setMesada] = useState("20000");
  const [nombre, setNombre] = useState("");
  const [clave, setClave] = useState("BeHuJunior2!");
  const [tab, setTab] = useState("Cuentas");
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Familia</h1>
      <div className="grid gap-2 md:grid-cols-3">
        {[
          ["Cuentas", "Juniors, mesada y límites"],
          ["Alertas", "Hormiga, impulso y gastos no pertinentes"],
          ["Invitar", "Alta o vínculo con consentimiento"],
        ].map(([id, copy]) => (
          <button key={id} className={tab === id ? "rounded-2xl bg-white p-3 text-left text-[#090D16]" : "rounded-2xl border border-[#1E293B] bg-[#111726] p-3 text-left"} type="button" onClick={() => setTab(id)}>
            <p className="text-sm font-semibold">{id}</p>
            <p className="mt-1 text-xs opacity-70">{copy}</p>
          </button>
        ))}
      </div>
      {tab === "Invitar" && <form className="panel space-y-2 p-4" onSubmit={async (event) => {
        event.preventDefault();
        const body = { email, initial_budget: mesada, daily_limit: "50000", weekly_limit: "200000", monthly_limit: "500000" };
        try {
          await api("/supervision/invite", token, { method: "POST", body: JSON.stringify(body) });
          onToast("ok", "Invitación enviada");
        } catch (err) {
          const message = err instanceof Error ? err.message : "";
          if (!message.toLowerCase().includes("no existe")) throw err;
          await api("/supervision/create-junior", token, { method: "POST", body: JSON.stringify({ ...body, nombres: nombre || "Junior", password: clave }) });
          onToast("ok", "Junior creado y vinculado");
        }
        await onDone();
      }}>
        <p className="text-sm text-muted">Invita por correo. Si no existe, se crea y queda vinculado.</p>
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="correo@behu.test" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Nombre si hay que crearlo" value={nombre} onChange={(event) => setNombre(event.target.value)} />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Mesada" value={mesada} onChange={(event) => setMesada(event.target.value)} />
        <input className="h-11 w-full rounded-card border border-line bg-bg px-3" placeholder="Clave temporal" value={clave} onChange={(event) => setClave(event.target.value)} />
        <button className="btn-primary h-11 w-full" type="submit">Enviar invitación o crear</button>
      </form>}
      {tab === "Invitar" && <div className="space-y-2">
        <h2 className="text-sm font-semibold text-muted">Pendientes de respuesta</h2>
        {sent.length === 0 && <p className="panel p-4 text-sm text-muted">No hay invitaciones esperando al Junior.</p>}
        {sent.map((invite) => (
          <article key={invite.id} className="panel p-4 text-sm">
            <p className="font-semibold">{invite.junior_nombre || invite.junior_email}</p>
            <p className="text-muted">PENDING · mesada {money(invite.initial_budget)}</p>
          </article>
        ))}
      </div>}
      {tab === "Alertas" && alerts.map((alert) => (
        <article key={alert.tipo + alert.junior_nombre} className={`panel p-4 text-sm ${alert.severity === "high" ? "border-[#F43F5E]" : "border-warning"}`}>
          <p className={`font-semibold ${alert.severity === "high" ? "text-[#F43F5E]" : "text-warning"}`}>{alert.badge || alert.tipo}</p>
          <p className="mt-1">{alert.mensaje}</p>
          <p className="mt-1 text-muted">{alert.sugerencia}</p>
        </article>
      ))}
      {tab === "Cuentas" && juniors.length === 0 && <p className="panel p-4 text-sm text-muted">Todavía no hay Juniors activos.</p>}
      {tab === "Cuentas" && juniors.map((junior) => (
        <article key={junior.cuenta_junior_id} className="panel space-y-3 p-4">
          <VirtualCard
            holder={`${junior.nombres} ${junior.apellidos}`}
            accountId={junior.cuenta_junior_id}
            frozen={Boolean(junior.tarjeta_bloqueada)}
            onToggle={async (next) => {
              await api(`/supervision/juniors/${junior.cuenta_junior_id}/card-status`, token, { method: "PATCH", body: JSON.stringify({ bloqueada: next }) });
              onToast(next ? "warn" : "ok", next ? "Tarjeta congelada" : "Tarjeta activa");
              await onDone();
            }}
          />
          <p className="text-sm text-muted">{junior.email} · {money(junior.saldo)} · ACTIVO</p>
          <div className="flex flex-wrap gap-2">
            <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={async () => { await api("/transfers/budget", token, { method: "POST", body: JSON.stringify({ cuenta_junior_id: junior.cuenta_junior_id, monto: "10000", descripcion: "Mesada" }) }); onToast("ok", "Mesada transferida"); await onDone(); }}>Mesada 10.000</button>
            <button className="btn-secondary h-9 px-3 text-sm" type="button" onClick={async () => { setOpenJunior(junior.cuenta_junior_id); setActivity(await api<Activity[]>(`/supervision/juniors/${junior.cuenta_junior_id}/activity`, token)); }}>Ver movimientos</button>
            <button className="h-9 rounded-card border border-danger px-3 text-sm text-danger" type="button" onClick={() => onUnlink(junior)}>Desvincular</button>
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

function PageHead({ title, subtitle, action, onAction }: { title: string; subtitle: string; action?: string; onAction?: () => void }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-[#94A3B8]">{subtitle}</p>
      </div>
      {action && <button className="h-10 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="button" onClick={onAction}>+ {action}</button>}
    </div>
  );
}

function LimitBar({ label, real, goal }: { label: string; real: number; goal: number }) {
  const width = goal > 0 ? Math.min(100, (real / goal) * 100) : 0;
  return (
    <div className="mt-3">
      <div className="mb-1 flex justify-between text-xs text-[#94A3B8]"><span>{label}</span><span>{goal ? `${Math.round(width)}%` : "Sin tope"}</span></div>
      <div className="h-2 rounded-full bg-[#1A2338]"><div className="h-2 rounded-full bg-[#3B82F6]" style={{ width: `${width}%` }} /></div>
    </div>
  );
}

function Learn({ token, lessons, onDone }: { token: string; lessons: Lesson[]; onDone: (message: string) => Promise<void> }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");
  const [tab, setTab] = useState("Lecciones");
  const badges = lessons.filter((lesson) => lesson.completado);
  return (
    <section className="space-y-3">
      <PageHead title="Educación financiera" subtitle="Cada lección completada suma puntos a tu Score BeHu." />
      <Tabs items={["Lecciones", "Insignias"]} value={tab} onChange={setTab} />
      <article className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
        <p className="font-semibold">Tus insignias financieras ({badges.length})</p>
        <p className="mt-1 text-sm text-[#94A3B8]">Cada lección completada suma +5 puntos a tu Score BeHu.</p>
      </article>
      {note && <p className="text-sm text-warning">{note}</p>}
      {tab === "Insignias" && badges.map((lesson) => <p key={lesson.id} className="rounded-full border border-[#1E293B] px-3 py-1 text-sm">Insignia: {lesson.insignia}</p>)}
      {tab === "Lecciones" && lessons.map((lesson) => (
        <article key={lesson.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
          <div>
            <p className="text-xs text-[#94A3B8]">{lesson.categoria || "Finanzas"} · {lesson.duracion_min || 2} min</p>
            <p className="mt-1 font-semibold">{lesson.titulo}</p>
            <p className="mt-1 text-sm text-[#94A3B8]">{lesson.resumen}</p>
          </div>
          <p className="rounded-full border border-[#334155] px-3 py-1 text-xs">Insignia: {lesson.insignia}</p>
          <div className="w-full">
          <p className="mt-3 text-sm">{lesson.pregunta}</p>
          <div className="mt-2 space-y-1">
            {lesson.opciones.map((opcion, index) => (
              <label key={opcion} className="block text-sm"><input type="radio" name={lesson.id} className="mr-2" onChange={() => setAnswers({ ...answers, [lesson.id]: String(index) })} />{opcion}</label>
            ))}
          </div>
          <button className="btn-primary mt-3 h-9 px-3 text-sm" type="button" disabled={lesson.completado} onClick={async () => {
            try {
              await api(`/education/modules/${lesson.id}/complete`, token, { method: "POST", body: JSON.stringify({ respuesta: answers[lesson.id] || "1" }) });
              const message = `Insignia ${lesson.insignia}. El score sube 8 puntos.`;
              setNote(message);
              await onDone(message);
            } catch (err) {
              const message = err instanceof Error ? err.message : "Respuesta incorrecta";
              setNote(message);
              await onDone(message);
            }
          }}>{lesson.completado ? "Completada" : "Iniciar lección + Quiz >"}</button>
          </div>
        </article>
      ))}
    </section>
  );
}

function Settings({
  token,
  user,
  account,
  juniors,
  currency,
  categories,
  onUser,
  onDone,
}: {
  token: string;
  user: User;
  account: Account | null;
  juniors: Junior[];
  currency: string;
  categories: Category[];
  onUser: (user: User) => void;
  onDone: (message: string) => Promise<void>;
}) {
  const [tab, setTab] = useState("Perfil");
  const [nombre, setNombre] = useState(`${user.nombres} ${user.apellidos}`);
  const [moneda, setMoneda] = useState(user.moneda_preferida || currency);
  const [ingreso, setIngreso] = useState(user.ingreso_mensual_estimado || "");
  const [nueva, setNueva] = useState("");
  return (
    <section className="space-y-4">
      <PageHead title="Ajustes y configuración" subtitle="Perfil, moneda y las categorías con las que registras movimientos." />
      <Tabs items={["Perfil", "Categorías", "Seguridad"]} value={tab} onChange={setTab} />
      {tab === "Perfil" && <form className="space-y-2 rounded-2xl border border-[#1E293B] bg-[#111726] p-4" onSubmit={async (event) => {
        event.preventDefault();
        const [nombres, ...resto] = nombre.trim().split(/\s+/);
        const next = await api<User>("/users/me", token, { method: "PATCH", body: JSON.stringify({ nombres, apellidos: resto.join(" ") || "BeHu", moneda, ingreso_mensual_estimado: ingreso || null }) });
        onUser(next);
        await onDone("Perfil actualizado");
      }}>
        <p className="font-semibold">Perfil y preferencias</p>
        <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#090D16] px-3" value={nombre} onChange={(event) => setNombre(event.target.value)} />
        <p className="text-sm text-[#94A3B8]">{user.email}</p>
        <select className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#090D16] px-3" value={moneda} onChange={(event) => setMoneda(event.target.value)}>{["COP", "USD", "MXN", "EUR", "PEN"].map((code) => <option key={code}>{code}</option>)}</select>
        <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#090D16] px-3" placeholder="Ingreso mensual estimado" value={ingreso || ""} onChange={(event) => setIngreso(event.target.value)} />
        <button className="h-10 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="submit">Guardar cambios</button>
      </form>}
      {tab === "Categorías" && (
        <div className="space-y-3">
          <form className="flex gap-2" onSubmit={async (event) => { event.preventDefault(); await api("/categories", token, { method: "POST", body: JSON.stringify({ nombre: nueva }) }); setNueva(""); await onDone("Categoría creada"); }}>
            <input className="h-11 flex-1 rounded-xl border border-[#1E293B] bg-[#111726] px-3" placeholder="Mascotas, Cursos, Gimnasio" value={nueva} onChange={(event) => setNueva(event.target.value)} required />
            <button className="h-11 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="submit">Crear</button>
          </form>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            {categories.map((item) => <p key={item.codigo} className="rounded-xl border border-[#1E293B] bg-[#111726] px-3 py-2 text-sm">{item.nombre}<span className="ml-2 text-xs text-[#64748B]">{item.origen}</span></p>)}
          </div>
        </div>
      )}
      {tab === "Seguridad" && <>
      <article className="panel space-y-1 p-4 text-sm">
        <p className="font-semibold">{user.nombres} {user.apellidos}</p>
        <p className="text-muted">{user.email}</p>
        <p>KYC {user.kyc_status === "VERIFIED" ? "Verificado · Cifrado AES-256" : user.kyc_status === "IN_REVIEW" ? "En revisión · Cifrado AES-256" : "Pendiente"}</p>
        <button className="btn-secondary mt-3 h-10 px-3" type="button" onClick={async () => {
          const data = await api<{ sha256: string; modo: string; snapshot: unknown }>("/system/backup", token, { method: "POST" });
          const blob = new Blob([JSON.stringify(data.snapshot, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `behu-backup-${data.sha256.slice(0, 8)}.json`;
          link.click();
          URL.revokeObjectURL(url);
          await onDone(`Backup ${data.modo}. Sello ${data.sha256.slice(0, 12)}`);
        }}>Descargar backup firmado</button>
        <label className="btn-secondary mt-3 inline-flex h-10 cursor-pointer items-center px-3">
          Simular documento
          <input className="hidden" type="file" onChange={async (event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            const body = new FormData();
            body.set("archivo", file);
            const result = await api<{ kyc_status?: string }>("/kyc/document", token, { method: "POST", body });
            onUser({ ...user, kyc_status: result.kyc_status || "IN_REVIEW" });
            await onDone("Documento enviado a revisión");
          }} />
        </label>
      </article>
      {tab === "Seguridad" && user.rol === "JUNIOR" && (
        <article className="panel p-4 text-sm">
          <p className="font-semibold">Límites de tu acudiente</p>
          <p className="mt-2 text-muted">Diario {money(account?.limite_gasto_diario || 0, currency)} · Semanal {money(account?.limite_gasto_semanal || 0, currency)} · Mensual {money(account?.limite_gasto_mensual || 0, currency)}</p>
          <p className="mt-2 text-dim">Estos topes tienen candado: solo tu Senior puede cambiarlos.</p>
        </article>
      )}
      {tab === "Seguridad" && user.rol === "SENIOR" && juniors.map((junior) => (
        <form key={junior.cuenta_junior_id} className="panel space-y-2 p-4" onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          await api(`/supervision/juniors/${junior.cuenta_junior_id}/limits`, token, {
            method: "PATCH",
            body: JSON.stringify({
              daily_limit: form.get("daily"),
              weekly_limit: form.get("weekly"),
              monthly_limit: form.get("monthly"),
            }),
          });
          await onDone(`Límites de ${junior.nombres} actualizados`);
        }}>
          <p className="font-semibold">{junior.nombres} {junior.apellidos}</p>
          <div className="grid gap-2 sm:grid-cols-3">
            <input name="daily" className="h-10 rounded-card border border-line bg-bg px-3" defaultValue={junior.limite_gasto_diario || "0"} />
            <input name="weekly" className="h-10 rounded-card border border-line bg-bg px-3" defaultValue={junior.limite_gasto_semanal || "0"} />
            <input name="monthly" className="h-10 rounded-card border border-line bg-bg px-3" defaultValue={junior.limite_gasto_mensual || "0"} />
          </div>
          <button className="btn-primary h-10 px-4 text-sm" type="submit">Guardar límites</button>
        </form>
      ))}
      </>}
    </section>
  );
}

function Tabs({ items, value, onChange }: { items: string[]; value: string; onChange: (value: string) => void }) {
  return (
    <div className="flex gap-2 overflow-auto">
      {items.map((item) => (
        <button key={item} className={value === item ? "h-9 rounded-full bg-white px-3 text-sm font-semibold text-[#090D16]" : "h-9 rounded-full border border-[#1E293B] px-3 text-sm text-[#94A3B8]"} type="button" onClick={() => onChange(item)}>{item}</button>
      ))}
    </div>
  );
}

function Mini({ role, currency, saldo, score, onAsk }: { role: Role; currency: string; saldo: string; score: number; onAsk: (pregunta: string) => Promise<Advice> }) {
  const [text, setText] = useState("");
  const [typing, setTyping] = useState(false);
  const [chat, setChat] = useState<{ role: "user" | "mini"; text: string; points?: string[] }[]>([]);
  const prompts = role === "SENIOR"
    ? ["¿Puedo invertir en un CDT?", "¿Cómo ahorro esta semana?", "¿Cómo evito gastos innecesarios?"]
    : ["¿Cuánto puedo gastar hoy?", "¿Cómo ahorro esta semana?", "¿Cómo evito gastos innecesarios?"];

  async function ask(pregunta: string) {
    setChat((items) => [...items, { role: "user", text: pregunta }]);
    setTyping(true);
    try {
      const data = await onAsk(pregunta);
      const reply = data.reply || data.response || data.resumen || "BeHu Mini no devolvió texto.";
      setChat((items) => [...items, { role: "mini", text: reply, points: data.insights || data.recomendaciones }]);
    } catch (err) {
      const detail = err instanceof Error ? err.message : "No pude responder ahora.";
      setChat((items) => [...items, { role: "mini", text: detail }]);
    } finally {
      setTyping(false);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3 rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#3B82F6] text-lg">🤖</span>
        <div className="flex-1">
          <p className="font-semibold">BeHu Mini</p>
          <p className="text-xs text-[#94A3B8]">{role === "SENIOR" ? "Modo Inversión & Familia" : "Modo Ahorro & Hábitos"}</p>
        </div>
        <p className="text-sm font-semibold">{score}/100</p>
      </div>
      <div className="flex gap-2 overflow-auto">
        {prompts.map((prompt) => (
          <button key={prompt} className="shrink-0 rounded-full border border-[#1E293B] px-3 py-2 text-xs" type="button" onClick={() => ask(prompt)}>{prompt}</button>
        ))}
      </div>
      <div className="min-h-48 space-y-3 rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
        {chat.length === 0 && <p className="text-sm text-[#94A3B8]">Hola. Tu saldo disponible es {saldo}. Pregunta en {currency}.</p>}
        {chat.map((item, index) => (
          <div key={index} className={item.role === "user" ? "ml-8 rounded-2xl bg-[#1A2338] p-3 text-sm" : "mr-8 rounded-2xl border border-[#1E293B] p-3 text-sm"}>
            <p>{item.text}</p>
            {item.points && <ul className="mt-2 list-disc space-y-1 pl-4 text-[#94A3B8]">{item.points.map((point) => <li key={point}>{point}</li>)}</ul>}
          </div>
        ))}
        {typing && <p className="text-sm text-[#3B82F6]">BeHu Mini está escribiendo…</p>}
      </div>
      <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); if (!text.trim()) return; ask(text.trim()); setText(""); }}>
        <input className="h-11 flex-1 rounded-card border border-line bg-surface px-3" value={text} onChange={(event) => setText(event.target.value)} placeholder="Escribe tu pregunta" />
        <button className="btn-primary h-11 px-4" type="submit">Enviar</button>
      </form>
    </section>
  );
}
