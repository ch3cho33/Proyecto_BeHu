"use client";

import { useEffect, useState } from "react";

type Lesson = { id: string; titulo: string; resumen: string; pregunta: string; opciones: string[]; completado: boolean; insignia: string; categoria?: string; duracion_min?: number };

const RUTAS = [
  { slug: "regla", titulo: "La Regla 50/30/20 en la Vida Real", guia: "De cada 100.000, 50.000 cubren necesidades, 30.000 gustos y 20.000 se congelan en una meta." },
  { slug: "hormiga", titulo: "Cómo Matar los Gastos Hormiga", guia: "Tres snacks de 8.000 suman 24.000. Ese monto, apartado, es una semana de la meta." },
  { slug: "cdt", titulo: "Interés Compuesto, CDTs y Primeras Inversiones", guia: "100.000 al 1% mensual llegan cerca de 103.000 en 3 meses y de 112.700 en 12 si se reinvierten." },
  { slug: "score", titulo: "Uso Inteligente de Tarjetas y Score Crediticio", guia: "Pagar a tiempo y no usar más del 40% del saldo disponible sostiene el Score." },
  { slug: "impulso", titulo: "Defensa contra Compras Impulsivas y Apuestas", guia: "Si ya hubo dos compras en tres horas, la pausa consciente evita la tercera automática." },
];

const FLASH = [
  ["50/30/20", "Parte el ingreso en necesidades, gustos y ahorro. El 20% es el que BeHu puede congelar."],
  ["Gasto hormiga", "Es pequeño y se repite. El daño está en la suma, no en el ticket."],
  ["CDT", "Depósito a plazo. Si reinviertes los intereses, el capital crece sobre sí mismo."],
  ["Score", "Resume hábitos: metas, pagos y compras forzadas. Sube cuando el ahorro es visible."],
  ["Pausa consciente", "Dos compras seguidas o un monto 1,5 veces tu promedio merecen un segundo de espera."],
];

const QUIZ = [
  { q: "En 50/30/20, ¿qué porción se aparta?", options: ["50% gustos", "20% ahorro", "30% deuda", "10% ocio"], ok: 1, why: "El 20% es ahorro o metas. Lo demás cubre necesidades y gustos." },
  { q: "Un gasto hormiga se reconoce porque…", options: ["Ocurre una vez al año", "Es pequeño y frecuente", "Siempre es una apuesta", "Congela saldo"], ok: 1, why: "La frecuencia convierte montos chicos en un hueco mensual." },
  { q: "El interés compuesto ocurre cuando…", options: ["El banco borra el saldo", "Los intereses generan intereses", "Solo aplica en dólares", "Gastas el rendimiento"], ok: 1, why: "Reinvertir hace que el rendimiento entre a la base del siguiente periodo." },
  { q: "Una compra de 2,1x tu promedio indica…", options: ["Un ingreso", "Un gasto fuera de patrón", "Una meta cumplida", "Un CDT"], ok: 1, why: "Supera el 150% del ticket habitual y BeHu pide una pausa." },
  { q: "¿Qué protege el Score esta semana?", options: ["Forzar cada compra", "Apartar y respetar el tope", "Ocultar movimientos", "Subir el límite solo"], ok: 1, why: "El ahorro visible y los topes estables suman más que una racha de gastos." },
];

export function Academy({
  token,
  lessons,
  currency,
  onDone,
  api,
}: {
  token: string;
  lessons: Lesson[];
  currency: string;
  onDone: (message: string) => Promise<void>;
  api: <T>(path: string, token: string | null, init?: RequestInit) => Promise<T>;
}) {
  const [tab, setTab] = useState("Rutas");
  const [flipped, setFlipped] = useState<number | null>(null);
  const [known, setKnown] = useState<number[]>([]);
  const [step, setStep] = useState(0);
  const [left, setLeft] = useState(20);
  const [streak, setStreak] = useState(0);
  const [note, setNote] = useState("");
  const [running, setRunning] = useState(false);
  const pregunta = QUIZ[step];

  useEffect(() => {
    if (!running) return;
    if (left <= 0) {
      setNote("Se acabó el tiempo. La racha vuelve a cero.");
      setStreak(0);
      setStep((value) => Math.min(QUIZ.length - 1, value + 1));
      setLeft(20);
      return;
    }
    const timer = setTimeout(() => setLeft((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [running, left]);

  async function responder(indice: number) {
    const acierto = indice === pregunta.ok;
    const next = acierto ? streak + 1 : 0;
    setStreak(next);
    setNote(acierto ? `Correcto. ${pregunta.why} Racha x${Math.max(1, next)}.` : `Incorrecto. ${pregunta.why}`);
    if (step === QUIZ.length - 1 && acierto) {
      setRunning(false);
      const modulo = lessons[0];
      if (modulo) {
        try {
          await api(`/education/modules/${modulo.id}/complete`, token, { method: "POST", body: JSON.stringify({ respuesta: "1" }) });
          await onDone(`Insignia ${modulo.insignia}. El Score suma los puntos de la lección.`);
        } catch (err) {
          await onDone(err instanceof Error ? err.message : "Respuesta de cierre no válida");
        }
      }
      return;
    }
    setStep((value) => Math.min(QUIZ.length - 1, value + 1));
    setLeft(20);
  }

  const tabs = [
    ["Rutas", "Guías cortas con ejemplos en tu moneda"],
    ["Kahoot", "Reto de 20 segundos y racha"],
    ["Quizlet", "Tarjetas que giran al tocarlas"],
    ["Insignias", "Lo que ya desbloqueaste"],
  ];

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Aprende</h1>
      <p className="text-sm text-muted">Ejemplos en {currency}. Cada lección suma al Score cuando el quiz cierra bien.</p>
      <div className="grid gap-2 md:grid-cols-4">
        {tabs.map(([id, copy]) => (
          <button key={id} className={tab === id ? "rounded-2xl bg-white p-3 text-left text-[#090D16]" : "rounded-2xl border border-[#1E293B] bg-[#111726] p-3 text-left"} type="button" onClick={() => setTab(id)}>
            <p className="text-sm font-semibold">{id}</p>
            <p className="mt-1 text-xs opacity-70">{copy}</p>
          </button>
        ))}
      </div>
      {tab === "Rutas" && RUTAS.map((ruta) => (
        <article key={ruta.slug} className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
          <p className="font-semibold">{ruta.titulo}</p>
          <p className="mt-2 text-sm text-muted">{ruta.guia}</p>
        </article>
      ))}
      {tab === "Quizlet" && FLASH.map(([frente, reverso], index) => (
        <button key={frente} className="w-full rounded-2xl border border-[#1E293B] bg-[#111726] p-5 text-left" type="button" onClick={() => setFlipped(flipped === index ? null : index)}>
          <p className="text-xs text-muted">{flipped === index ? "Reverso" : "Frente"}</p>
          <p className="mt-2 text-lg font-semibold">{flipped === index ? reverso : frente}</p>
          <div className="mt-3 flex gap-2">
            <span className="rounded-full border border-line px-2 py-1 text-xs" onClick={(event) => { event.stopPropagation(); setKnown((items) => [...items, index]); }}>Ya lo domino</span>
            <span className="rounded-full border border-line px-2 py-1 text-xs">Repasar luego</span>
          </div>
        </button>
      ))}
      {tab === "Kahoot" && (
        <article className="rounded-2xl border border-[#1E293B] bg-[#111726] p-4">
          <div className="mb-3 h-2 rounded-full bg-[#1A2338]"><div className="h-2 rounded-full bg-[#2563EB]" style={{ width: `${(left / 20) * 100}%` }} /></div>
          <p className="text-xs text-muted">{left}s · racha x{Math.max(1, streak)}</p>
          <p className="mt-2 font-semibold">{pregunta.q}</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {pregunta.options.map((opcion, index) => (
              <button key={opcion} className="rounded-xl bg-[#1A2338] px-3 py-3 text-left text-sm" type="button" onClick={() => { setRunning(true); responder(index); }}>{opcion}</button>
            ))}
          </div>
          {note && <p className="mt-3 text-sm text-muted">{note}</p>}
        </article>
      )}
      {tab === "Insignias" && (
        <div className="space-y-2">
          <p className="text-sm text-muted">Dominadas en flashcards: {known.length}. Insignias de lección: {lessons.filter((lesson) => lesson.completado).length}.</p>
          {lessons.map((lesson) => <p key={lesson.id} className="rounded-xl border border-[#1E293B] px-3 py-2 text-sm">{lesson.completado ? "Insignia" : "Pendiente"}: {lesson.insignia} · {lesson.titulo}</p>)}
        </div>
      )}
    </section>
  );
}
