"use client";

import { FormEvent, useState } from "react";
import { ArrowRight, Check } from "lucide-react";

type Role = "SENIOR" | "JUNIOR";
type RegisterPayload = { nombres: string; apellidos: string; email: string; password: string; rol: Role; moneda: string; ingreso_mensual_estimado?: string };

const CURRENCIES = ["COP", "USD", "MXN", "EUR", "PEN"];

export function PublicSite({
  error,
  onLogin,
  onRegister,
}: {
  error: string;
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (payload: RegisterPayload) => Promise<void>;
}) {
  const [screen, setScreen] = useState<"landing" | "login" | "register">("landing");
  const [demo, setDemo] = useState(false);
  if (screen === "landing") {
    return (
      <div className="min-h-screen bg-bg text-ink">
        <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Brand />
          <div className="flex items-center gap-2">
            <button className="h-10 rounded-xl px-4 text-sm text-[#F8FAFC]" type="button" onClick={() => setScreen("login")}>Iniciar sesión</button>
            <button className="h-10 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="button" onClick={() => setScreen("register")}>Crear cuenta</button>
          </div>
        </header>
        <main className="mx-auto grid max-w-6xl gap-10 px-6 pb-20 pt-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <section>
            <p className="inline-flex rounded-full border border-[#1E293B] bg-[#111726] px-3 py-1 text-xs text-[#94A3B8]">Finanzas personales claras y sin fricción</p>
            <h1 className="mt-5 max-w-xl text-4xl font-semibold tracking-tight md:text-5xl">Entiende tu dinero. Ahorra con intención.</h1>
            <p className="mt-4 max-w-lg text-sm leading-6 text-[#94A3B8]">BeHu ordena el saldo, las metas y el núcleo familiar en un solo lugar. Sandbox académico, con ledger de partida doble y BeHu Mini.</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button className="inline-flex h-11 items-center gap-2 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="button" onClick={() => setScreen("register")}>Empezar ahora <ArrowRight size={16} /></button>
              <button className="h-11 rounded-xl border border-[#334155] px-4 text-sm" type="button" onClick={() => setDemo(true)}>Probar cuenta demo</button>
            </div>
            {demo && (
              <div className="mt-4 flex gap-2">
                <button className="btn-secondary h-10 px-3 text-sm" type="button" onClick={() => onLogin("senior@behu.test", "BeHuSenior1!")}>Demo Senior</button>
                <button className="btn-secondary h-10 px-3 text-sm" type="button" onClick={() => onLogin("junior@behu.test", "BeHuJunior1!")}>Demo Junior</button>
              </div>
            )}
            {error && <p className="mt-4 text-sm text-danger">{error}</p>}
          </section>
          <DashboardMock />
        </main>
        <section className="mx-auto max-w-6xl px-6 pb-20">
          <h2 className="text-2xl font-semibold">Herramientas pensadas para tu control financiero</h2>
          <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["Registro en segundos", "Un gasto, un ingreso o una mesada salen del mismo gesto."],
              ["Semana vs. semana", "Ves el consumo contra tu límite antes de que se acabe el periodo."],
              ["Metas de ahorro", "El dinero apartado queda congelado y visible."],
              ["Control familiar y BeHu Mini IA", "El Senior lee alertas reales y el asistente responde con tus cifras."],
            ].map(([title, body]) => (
              <article key={title} className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
                <p className="font-semibold">{title}</p>
                <p className="mt-2 text-sm text-[#94A3B8]">{body}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    );
  }
  return <SplitAuth mode={screen} error={error} onMode={setScreen} onLogin={onLogin} onRegister={onRegister} />;
}

function Brand() {
  return (
    <span className="flex items-center gap-2 font-semibold">
      <span className="grid h-8 w-8 place-items-center rounded-xl bg-[#111726] shadow-[0_0_18px_rgba(59,130,246,0.35)]">
        <svg width="16" height="16" viewBox="0 0 22 22" aria-hidden="true"><rect x="2" y="3" width="6" height="16" rx="2" fill="#10B981" /><rect x="11" y="7" width="9" height="12" rx="2" fill="#3B82F6" /></svg>
      </span>
      BeHu
    </span>
  );
}

function DashboardMock() {
  return (
    <div className="overflow-hidden rounded-2xl border border-[#1E293B] bg-[#0F1422] shadow-[0_8px_32px_rgba(0,0,0,0.45)]">
      <div className="flex items-center gap-2 border-b border-[#1E293B] px-4 py-3 text-xs text-[#94A3B8]">
        <span className="h-2.5 w-2.5 rounded-full bg-[#F43F5E]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#F59E0B]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#10B981]" />
        <span className="ml-2">app.behu.com/dashboard</span>
      </div>
      <div className="grid gap-3 p-4 sm:grid-cols-3">
        <article className="rounded-xl border border-[#1E293B] bg-[#111726] p-3"><p className="text-xs text-[#94A3B8]">Saldo disponible</p><p className="mt-2 text-lg font-semibold">$1.000.000</p></article>
        <article className="rounded-xl border border-[#1E293B] bg-[#111726] p-3"><p className="text-xs text-[#94A3B8]">Consumo semanal</p><div className="mt-3 h-2 rounded-full bg-[#1A2338]"><div className="h-2 w-2/3 rounded-full bg-[#3B82F6]" /></div></article>
        <article className="rounded-xl border border-[#1E293B] bg-[#111726] p-3"><p className="text-xs text-[#94A3B8]">Score BeHu</p><p className="mt-2 text-lg font-semibold text-[#10B981]">88/100 Excelente</p></article>
      </div>
      <div className="px-4 pb-4">
        <p className="text-xs text-[#64748B]">Actividad reciente</p>
        {[["Mesada familiar", "+$200.000"], ["Almuerzo", "-$18.500"], ["Meta viaje", "-$50.000"]].map(([name, amount]) => (
          <div key={name} className="mt-2 flex justify-between rounded-xl border border-[#1E293B] bg-[#111726] px-3 py-2 text-sm"><span>{name}</span><span>{amount}</span></div>
        ))}
      </div>
    </div>
  );
}

function SplitAuth({
  mode,
  error,
  onMode,
  onLogin,
  onRegister,
}: {
  mode: "login" | "register";
  error: string;
  onMode: (mode: "landing" | "login" | "register") => void;
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (payload: RegisterPayload) => Promise<void>;
}) {
  const [email, setEmail] = useState(mode === "login" ? "senior@behu.test" : "");
  const [password, setPassword] = useState(mode === "login" ? "BeHuSenior1!" : "");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<Role>("SENIOR");
  const [moneda, setMoneda] = useState("COP");
  const [ingreso, setIngreso] = useState("");
  const [localError, setLocalError] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "login") {
      onLogin(email, password);
      return;
    }
    if (!(password.length >= 8 && /[A-Za-z]/.test(password) && /\d/.test(password))) {
      setLocalError("La contraseña necesita al menos 8 caracteres, letras y números.");
      return;
    }
    const [nombres, ...resto] = nombre.trim().split(/\s+/);
    onRegister({
      nombres: nombres || nombre,
      apellidos: resto.join(" ") || "BeHu",
      email,
      password,
      rol,
      moneda,
      ingreso_mensual_estimado: ingreso || undefined,
    });
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-between bg-[#0F1422] p-10 lg:flex">
        <Brand />
        <div>
          <h2 className="max-w-md text-4xl font-semibold tracking-tight">Cada peso cuenta. Toma el control de tus finanzas.</h2>
          <ul className="mt-6 space-y-3 text-sm text-[#94A3B8]">
            {["Compara tu consumo semana a semana", "Metas de ahorro con seguimiento visual", "Análisis y recomendaciones inteligentes"].map((item) => (
              <li key={item} className="flex items-center gap-2"><Check className="text-[#3B82F6]" size={16} />{item}</li>
            ))}
          </ul>
        </div>
        <article className="max-w-sm rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
          <p className="text-sm font-semibold">Resumen semanal</p>
          <p className="mt-1 text-xs text-[#94A3B8]">Meta de ahorro 64%</p>
          <div className="mt-3 h-2 rounded-full bg-[#1A2338]"><div className="h-2 w-[64%] rounded-full bg-[#10B981]" /></div>
        </article>
      </section>
      <section className="flex flex-col justify-center px-6 py-10 md:px-16">
        <button className="mb-6 text-left text-sm text-[#94A3B8] lg:hidden" type="button" onClick={() => onMode("landing")}>Volver</button>
        <h1 className="text-3xl font-semibold">{mode === "login" ? "Bienvenido de nuevo" : "Crea tu cuenta"}</h1>
        <form className="mt-8 space-y-3" onSubmit={submit}>
          {mode === "register" && (
            <>
              <div className="grid grid-cols-2 gap-2">
                {([["SENIOR", "Senior (Acudiente)"], ["JUNIOR", "Junior (Joven)"]] as const).map(([id, label]) => (
                  <button key={id} type="button" className={`rounded-2xl border p-3 text-left text-sm ${rol === id ? "border-[#3B82F6] bg-[#1A2338]" : "border-[#1E293B] bg-[#111726]"}`} onClick={() => setRol(id)}>{label}</button>
                ))}
              </div>
              <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#111726] px-3" placeholder="Nombre" value={nombre} onChange={(event) => setNombre(event.target.value)} required />
            </>
          )}
          <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#111726] px-3" type="email" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#111726] px-3" type="password" placeholder="Contraseña" value={password} onChange={(event) => setPassword(event.target.value)} required />
          {mode === "register" && (
            <>
              <select className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#111726] px-3" value={moneda} onChange={(event) => setMoneda(event.target.value)}>
                {CURRENCIES.map((code) => <option key={code}>{code}</option>)}
              </select>
              <input className="h-11 w-full rounded-xl border border-[#1E293B] bg-[#111726] px-3" placeholder="Ingreso mensual estimado (opcional)" value={ingreso} onChange={(event) => setIngreso(event.target.value.replace(/\D/g, ""))} />
            </>
          )}
          {(localError || error) && <p className="text-sm text-danger">{localError || error}</p>}
          <button className="h-11 w-full rounded-xl bg-white font-semibold text-[#090D16]" type="submit">{mode === "login" ? "Iniciar sesión" : "Crear cuenta"}</button>
        </form>
        {mode === "login" && (
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button className="btn-secondary h-10 text-sm" type="button" onClick={() => onLogin("senior@behu.test", "BeHuSenior1!")}>Demo Senior</button>
            <button className="btn-secondary h-10 text-sm" type="button" onClick={() => onLogin("junior@behu.test", "BeHuJunior1!")}>Demo Junior</button>
          </div>
        )}
        <button className="mt-4 text-sm text-[#94A3B8]" type="button" onClick={() => onMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "¿No tienes cuenta? Regístrate" : "¿Ya tienes cuenta? Inicia sesión"}
        </button>
      </section>
    </div>
  );
}
