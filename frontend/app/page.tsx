"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";

type User = { nombres: string; apellidos: string; email: string; rol: "SENIOR" | "JUNIOR" };
type Account = {
  saldo: string;
  moneda: string;
  tipo: string;
  limite_gasto_diario?: string | null;
  limite_gasto_semanal?: string | null;
};
type Goal = {
  id: string;
  nombre: string;
  monto_actual: string;
  monto_objetivo: string;
  porcentaje: string;
  estado: string;
};
type Junior = { cuenta_junior_id: string; nombres: string; apellidos: string; saldo: string };
type Advice = { resumen: string; recomendaciones: string[]; fuente: string };
type Score = {
  puntaje: number;
  nivel: string;
  color: string;
  consejos: string[];
  factores_positivos: { etiqueta: string; puntos: number }[];
  factores_negativos: { etiqueta: string; puntos: number }[];
};
type Lesson = {
  id: string;
  titulo: string;
  resumen: string;
  pregunta: string;
  opciones: string[];
  completado: boolean;
  insignia: string;
  insignia_obtenida: string | null;
};

function money(value: string | number) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(Number(value));
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
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.mensaje || detail?.code || "No se pudo completar la operación";
    const error = new Error(message) as Error & { payload?: unknown; status?: number };
    error.payload = detail;
    error.status = response.status;
    throw error;
  }
  return data as T;
}

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [juniors, setJuniors] = useState<Junior[]>([]);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("senior@behu.test");
  const [password, setPassword] = useState("BeHuSenior1!");
  const [busy, setBusy] = useState(false);

  async function refresh(activeToken: string, rol: User["rol"]) {
    const me = await api<{ account: Account }>(`/accounts/me`, activeToken);
    const metas = await api<Goal[]>(`/goals`, activeToken);
    const salud = await api<Score>(`/scoring/me`, activeToken);
    const academia = await api<Lesson[]>(`/education/modules`, activeToken);
    setAccount(me.account);
    setGoals(metas);
    setScore(salud);
    setLessons(academia);
    if (rol === "SENIOR") {
      setJuniors(await api<Junior[]>(`/supervision/juniors`, activeToken));
    }
  }

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => undefined);
    }
    const saved = localStorage.getItem("behu_session");
    if (!saved) return;
    const session = JSON.parse(saved) as { token: string; user: User };
    setToken(session.token);
    setUser(session.user);
    refresh(session.token, session.user.rol).catch(() => localStorage.removeItem("behu_session"));
  }, []);

  async function onLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const session = await api<{ access_token: string; user: User }>("/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      localStorage.setItem(
        "behu_session",
        JSON.stringify({ token: session.access_token, user: session.user }),
      );
      setToken(session.access_token);
      setUser(session.user);
      await refresh(session.access_token, session.user.rol);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de acceso");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    localStorage.removeItem("behu_session");
    setToken(null);
    setUser(null);
    setAccount(null);
    setAdvice(null);
  }

  async function run(action: () => Promise<void>) {
    if (!token || !user) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      await refresh(token, user.rol);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  if (!token || !user || !account) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-moss">BeHu sandbox</p>
        <h1 className="mt-2 text-4xl font-semibold">Entra a tu cuenta</h1>
        <p className="mt-2 text-sm text-ink/70">
          Senior: senior@behu.test · Junior: junior@behu.test
        </p>
        <form onSubmit={onLogin} className="mt-8 space-y-4 rounded-3xl bg-white p-6 shadow-sm">
          <label className="block text-sm">
            Correo
            <input
              className="mt-1 w-full rounded-xl border border-ink/10 px-3 py-2"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </label>
          <label className="block text-sm">
            Contraseña
            <input
              type="password"
              className="mt-1 w-full rounded-xl border border-ink/10 px-3 py-2"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && <p className="text-sm text-clay">{error}</p>}
          <button
            disabled={busy}
            className="w-full rounded-xl bg-moss px-4 py-3 font-medium text-white disabled:opacity-60"
          >
            Entrar
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-moss">{user.rol}</p>
          <h1 className="text-3xl font-semibold">
            {user.nombres} {user.apellidos}
          </h1>
        </div>
        <button onClick={logout} className="text-sm underline">
          Salir
        </button>
      </header>

      <section className="mt-6 rounded-3xl bg-ink px-6 py-7 text-sand">
        <p className="text-sm text-sand/70">Saldo disponible</p>
        <p className="mt-1 text-4xl font-semibold">{money(account.saldo)}</p>
        {user.rol === "JUNIOR" && (
          <p className="mt-3 text-sm text-sand/80">
            Límite diario {money(account.limite_gasto_diario || 0)} · semanal{" "}
            {money(account.limite_gasto_semanal || 0)}
          </p>
        )}
      </section>

      {score && (
        <section className="mt-4 rounded-3xl bg-white p-5">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-sm text-ink/60">Score BeHu</p>
              <p className="text-3xl font-semibold" style={{ color: score.color }}>
                {score.puntaje}
              </p>
            </div>
            <p className="text-sm font-medium" style={{ color: score.color }}>
              {score.nivel}
            </p>
          </div>
          <div className="mt-3 h-3 rounded-full bg-sand">
            <div
              className="h-3 rounded-full"
              style={{ width: `${score.puntaje}%`, backgroundColor: score.color }}
            />
          </div>
          <ul className="mt-3 space-y-1 text-sm text-ink/80">
            {score.consejos.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      )}

      {error && <p className="mt-4 rounded-2xl bg-clay/10 px-4 py-3 text-sm text-clay">{error}</p>}
      {notice && <p className="mt-4 rounded-2xl bg-moss/10 px-4 py-3 text-sm text-moss">{notice}</p>}

      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <article className="rounded-3xl bg-white p-5">
          <h2 className="font-semibold">Metas</h2>
          <ul className="mt-3 space-y-3 text-sm">
            {goals.length === 0 && <li className="text-ink/60">Aún no hay metas.</li>}
            {goals.map((goal) => (
              <li key={goal.id}>
                <div className="flex justify-between">
                  <span>{goal.nombre}</span>
                  <span>{goal.porcentaje}%</span>
                </div>
                <div className="mt-1 h-2 rounded-full bg-sand">
                  <div className="h-2 rounded-full bg-moss" style={{ width: `${Math.min(Number(goal.porcentaje), 100)}%` }} />
                </div>
              </li>
            ))}
          </ul>
          <form
            className="mt-4 space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              run(async () => {
                await api("/goals", token, {
                  method: "POST",
                  body: JSON.stringify({
                    nombre: form.get("nombre"),
                    monto_objetivo: form.get("monto"),
                    fecha_limite: form.get("fecha"),
                  }),
                });
                setNotice("Meta creada. El saldo se congela cuando abones.");
                event.currentTarget.reset();
              });
            }}
          >
            <input name="nombre" placeholder="Nombre de la meta" className="w-full rounded-xl border px-3 py-2 text-sm" required />
            <input name="monto" type="number" min="1" placeholder="Monto objetivo" className="w-full rounded-xl border px-3 py-2 text-sm" required />
            <input name="fecha" type="date" className="w-full rounded-xl border px-3 py-2 text-sm" required />
            <button className="rounded-xl bg-ink px-3 py-2 text-sm text-white">Crear meta</button>
          </form>
        </article>

        <article className="rounded-3xl bg-white p-5">
          <h2 className="font-semibold">{user.rol === "SENIOR" ? "Presupuesto Junior" : "Simular compra"}</h2>
          {user.rol === "SENIOR" ? (
            <form
              className="mt-4 space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                run(async () => {
                  await api("/transfers/budget", token, {
                    method: "POST",
                    body: JSON.stringify({
                      cuenta_junior_id: form.get("junior"),
                      monto: form.get("monto"),
                      descripcion: "Presupuesto desde la app",
                    }),
                  });
                  setNotice("Presupuesto acreditado con partida doble.");
                });
              }}
            >
              <select name="junior" className="w-full rounded-xl border px-3 py-2 text-sm" required>
                {juniors.map((junior) => (
                  <option key={junior.cuenta_junior_id} value={junior.cuenta_junior_id}>
                    {junior.nombres} {junior.apellidos} · {money(junior.saldo)}
                  </option>
                ))}
              </select>
              <input name="monto" type="number" min="1" defaultValue={50000} className="w-full rounded-xl border px-3 py-2 text-sm" />
              <button className="rounded-xl bg-moss px-3 py-2 text-sm text-white">Asignar</button>
            </form>
          ) : (
            <form
              className="mt-4 space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                const force = form.get("forzar") === "on";
                run(async () => {
                  try {
                    await api("/transactions/spend", token, {
                      method: "POST",
                      body: JSON.stringify({
                        monto: form.get("monto"),
                        categoria: form.get("categoria"),
                        comercio: form.get("comercio"),
                        forzar_confirmacion: force,
                      }),
                    });
                    setNotice(force ? "Compra confirmada pese a la alerta." : "Compra registrada.");
                  } catch (err) {
                    const payload = (err as Error & { payload?: { razones?: string[] } }).payload;
                    if (payload?.razones) {
                      setError(`${(err as Error).message} Motivos: ${payload.razones.join(", ")}. Marca confirmar y reintenta.`);
                      return;
                    }
                    throw err;
                  }
                });
              }}
            >
              <input name="comercio" defaultValue="Tienda del barrio" className="w-full rounded-xl border px-3 py-2 text-sm" />
              <select name="categoria" className="w-full rounded-xl border px-3 py-2 text-sm">
                <option value="COMIDA">Comida</option>
                <option value="ENTRETENIMIENTO">Entretenimiento</option>
                <option value="TRANSPORTE">Transporte</option>
                <option value="EDUCACION">Educación</option>
                <option value="ROPA">Ropa</option>
              </select>
              <input name="monto" type="number" min="1" defaultValue={45000} className="w-full rounded-xl border px-3 py-2 text-sm" />
              <label className="flex items-center gap-2 text-sm">
                <input name="forzar" type="checkbox" />
                Confirmar aunque BeHu Mini lo marque como impulsivo
              </label>
              <button className="rounded-xl bg-clay px-3 py-2 text-sm text-white">Pagar</button>
            </form>
          )}
        </article>
      </section>

      <section className="mt-4 rounded-3xl bg-white p-5">
        <h2 className="font-semibold">Academia BeHu</h2>
        <div className="mt-4 space-y-4">
          {lessons.map((lesson) => (
            <article key={lesson.id} className="rounded-2xl bg-sand p-4">
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-medium">{lesson.titulo}</h3>
                {lesson.completado && (
                  <span className="rounded-full bg-moss px-2 py-1 text-xs text-white">
                    {lesson.insignia_obtenida}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm text-ink/80">{lesson.resumen}</p>
              {!lesson.completado && (
                <form
                  className="mt-3 space-y-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const form = new FormData(event.currentTarget);
                    run(async () => {
                      const result = await api<{ mensaje: string }>(
                        `/education/modules/${lesson.id}/complete`,
                        token,
                        {
                          method: "POST",
                          body: JSON.stringify({ respuesta: form.get("respuesta") }),
                        },
                      );
                      setNotice(result.mensaje);
                    });
                  }}
                >
                  <p className="text-sm font-medium">{lesson.pregunta}</p>
                  {lesson.opciones.map((opcion, index) => (
                    <label key={opcion} className="flex items-center gap-2 text-sm">
                      <input type="radio" name="respuesta" value={String(index)} required />
                      {opcion}
                    </label>
                  ))}
                  <button className="rounded-xl bg-ink px-3 py-2 text-sm text-white">Responder</button>
                </form>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="mt-4 rounded-3xl bg-white p-5">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">BeHu Mini</h2>
          <button
            disabled={busy}
            className="rounded-xl bg-moss px-3 py-2 text-sm text-white disabled:opacity-60"
            onClick={() =>
              run(async () => {
                const result = await api<Advice>("/ai/consult", token, {
                  method: "POST",
                  body: JSON.stringify({ pregunta: "¿Qué hago con mi dinero esta semana?" }),
                });
                setAdvice(result);
              })
            }
          >
            Consultar
          </button>
        </div>
        {advice && (
          <ul className="mt-4 space-y-2 text-sm">
            {advice.recomendaciones.map((item) => (
              <li key={item} className="rounded-2xl bg-sand px-3 py-2">
                {item}
              </li>
            ))}
            <li className="text-xs text-ink/50">Fuente: {advice.fuente}</li>
          </ul>
        )}
      </section>
    </main>
  );
}
