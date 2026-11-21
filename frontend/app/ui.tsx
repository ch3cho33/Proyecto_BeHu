"use client";

import { useState } from "react";

export type Toast = { id: number; tone: "ok" | "danger" | "warn"; text: string };

const DONUT_COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#F43F5E", "#94A3B8", "#64748B"];
const CATEGORY_LABEL: Record<string, string> = {
  COMIDA: "Comida",
  ENTRETENIMIENTO: "Ocio",
  OCIO: "Ocio",
  TRANSPORTE: "Transporte",
  EDUCACION: "Educación",
  ROPA: "Ropa",
  SALUD: "Salud",
  VIVIENDA: "Vivienda",
  SERVICIOS: "Servicios",
  SUPERMERCADO: "Supermercado",
  SUSCRIPCIONES: "Suscripciones",
  VIAJES: "Viajes",
  DEPORTES: "Deportes",
  REGALOS: "Regalos",
  CUIDADO_PERSONAL: "Cuidado personal",
  TECNOLOGIA: "Tecnología",
  IMPUESTOS: "Impuestos",
  FAMILIA: "Familia",
  TRABAJO: "Trabajo",
  OTRO: "Otros",
};

export function labelCategory(code: string) {
  return CATEGORY_LABEL[code] || code.replaceAll("_", " ").toLowerCase().replace(/(^|\s)\S/g, (letra) => letra.toUpperCase());
}

function digitsFromId(id: string) {
  const hex = (id || "behu").replace(/[^a-f0-9]/gi, "").padEnd(16, "0");
  const groups = [0, 4, 8, 12].map((start) => String(parseInt(hex.slice(start, start + 4), 16) % 10000).padStart(4, "0"));
  return { groups, last4: groups[3], cvv: String(parseInt(hex.slice(12, 15), 16) % 1000).padStart(3, "0") };
}

export function VirtualCard({
  holder,
  accountId,
  frozen,
  onToggle,
}: {
  holder: string;
  accountId: string;
  frozen: boolean;
  onToggle?: (next: boolean) => void;
}) {
  const pan = digitsFromId(accountId);
  const [open, setOpen] = useState(false);
  return (
    <article className="behu-card relative min-h-[190px] overflow-hidden p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-semibold tracking-wide">BeHu</p>
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${frozen ? "bg-danger/15 text-danger" : "bg-success/15 text-success"}`}>
          {frozen ? "CONGELADA" : "ACTIVA"}
        </span>
      </div>
      <div className="mt-6 h-8 w-11 rounded-behu border border-line-strong bg-gradient-to-br from-[#d6d3c4] to-[#8a8472]" />
      <p className="mt-4 font-mono text-lg tracking-[0.18em]">{open ? pan.groups.join("  ") : `••••  ••••  ••••  ${pan.last4}`}</p>
      <div className="mt-4 flex items-end justify-between text-xs text-muted">
        <div>
          <p className="uppercase tracking-wide">{holder}</p>
          <p className="mt-1">Exp 12/29{open ? ` · CVV ${pan.cvv}` : ""}</p>
        </div>
        <button className="btn-secondary h-8 px-3" type="button" onClick={() => setOpen((value) => !value)}>
          {open ? "Ocultar datos" : "Mostrar datos"}
        </button>
      </div>
      {onToggle && (
        <button className="btn-secondary mt-4 h-9 w-full text-sm" type="button" onClick={() => onToggle(!frozen)}>
          {frozen ? "Activar tarjeta" : "Congelar tarjeta"}
        </button>
      )}
    </article>
  );
}

export function Donut({ slices, totalLabel }: { slices: { label: string; value: number }[]; totalLabel: string }) {
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);
  const radius = 42;
  const circ = 2 * Math.PI * radius;
  let offset = 0;
  return (
    <div className="panel flex flex-col gap-4 p-4 sm:flex-row sm:items-center">
      <svg viewBox="0 0 120 120" className="mx-auto h-40 w-40">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="#1A2338" strokeWidth="14" />
        {total > 0 &&
          slices.map((slice, index) => {
            const length = (slice.value / total) * circ;
            const dash = `${length} ${circ - length}`;
            const node = (
              <circle
                key={slice.label}
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={DONUT_COLORS[index % DONUT_COLORS.length]}
                strokeWidth="14"
                strokeDasharray={dash}
                strokeDashoffset={-offset}
                transform="rotate(-90 60 60)"
              />
            );
            offset += length;
            return node;
          })}
        <text x="60" y="58" textAnchor="middle" fill="#F8FAFC" fontSize="11" fontWeight="600">
          {totalLabel}
        </text>
        <text x="60" y="72" textAnchor="middle" fill="#94A3B8" fontSize="8">
          del mes
        </text>
      </svg>
      <ul className="flex-1 space-y-2 text-sm">
        {slices.length === 0 && <li className="text-muted">Todavía no hay gastos este mes.</li>}
        {slices.map((slice, index) => (
          <li key={slice.label} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DONUT_COLORS[index % DONUT_COLORS.length] }} />
              {slice.label}
            </span>
            <span className="text-muted">{total ? Math.round((slice.value / total) * 100) : 0}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function WeekBars({
  days,
}: {
  days: { label: string; spent: number; limit: number; impulsive: boolean }[];
}) {
  const max = Math.max(...days.map((day) => Math.max(day.spent, day.limit)), 1);
  return (
    <div className="panel p-4">
      <p className="text-sm text-muted">Gasto contra límite, últimos 7 días</p>
      <svg viewBox="0 0 320 140" className="mt-3 w-full">
        {days.map((day, index) => {
          const x = 12 + index * 44;
          const spentH = (day.spent / max) * 96;
          const limitH = (day.limit / max) * 96;
          const color = day.impulsive ? (day.spent > day.limit ? "#F43F5E" : "#F59E0B") : "#3B82F6";
          return (
            <g key={day.label}>
              <rect x={x} y={110 - limitH} width="14" height={limitH} rx="3" fill="#1A2338" />
              <rect x={x + 16} y={110 - spentH} width="14" height={Math.max(spentH, day.spent ? 2 : 0)} rx="3" fill={color} />
              <text x={x + 15} y="128" textAnchor="middle" fill="#64748B" fontSize="9">
                {day.label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="text-xs text-dim">Gris: límite. Azul: gasto. Ámbar o rojo: día con compra impulsiva.</p>
    </div>
  );
}

export function ScoreGauge({
  score,
  level,
  factors,
}: {
  score: number;
  level: string;
  factors: { etiqueta: string; puntos: number }[];
}) {
  const radius = 46;
  const circ = 2 * Math.PI * radius;
  const dash = (Math.max(0, Math.min(100, score)) / 100) * circ;
  const tone = score >= 80 ? "#10B981" : score >= 60 ? "#3B82F6" : "#F43F5E";
  const short = score >= 80 ? "Excelente" : score >= 60 ? "Bueno" : "En riesgo";
  return (
    <div className="panel p-4">
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 120 120" className="h-28 w-28">
          <circle cx="60" cy="60" r={radius} fill="none" stroke="#1A2338" strokeWidth="10" />
          <circle
            cx="60"
            cy="60"
            r={radius}
            fill="none"
            stroke={tone}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ - dash}`}
            transform="rotate(-90 60 60)"
          />
          <text x="60" y="58" textAnchor="middle" fill="#F8FAFC" fontSize="22" fontWeight="650">
            {score}
          </text>
          <text x="60" y="74" textAnchor="middle" fill="#94A3B8" fontSize="9">
            {short}
          </text>
        </svg>
        <div>
          <p className="text-sm text-muted">Nivel BeHu</p>
          <p className="text-lg font-semibold">{level}</p>
        </div>
      </div>
      <ul className="mt-3 space-y-1 text-sm">
        {factors.length === 0 && <li className="text-muted">Sin movimientos que muevan el score todavía.</li>}
        {factors.map((factor) => (
          <li key={factor.etiqueta} className={factor.puntos >= 0 ? "text-success" : "text-danger"}>
            {factor.puntos > 0 ? "+" : ""}
            {factor.puntos} · {factor.etiqueta}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function Skeleton() {
  return (
    <div className="space-y-3">
      <div className="h-8 w-40 animate-pulse rounded-card bg-surface-hover" />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <div key={index} className="h-24 animate-pulse rounded-sheet bg-surface-hover" />
        ))}
      </div>
      <div className="h-48 animate-pulse rounded-sheet bg-surface-hover" />
    </div>
  );
}

export function Toasts({ items }: { items: Toast[] }) {
  return (
    <div className="pointer-events-none fixed bottom-20 right-4 z-30 flex w-72 flex-col gap-2 md:bottom-6">
      {items.map((item) => (
        <p
          key={item.id}
          className={`rounded-card border bg-surface px-3 py-2 text-sm shadow-lg ${
            item.tone === "ok" ? "border-success text-success" : item.tone === "warn" ? "border-warning text-warning" : "border-danger text-danger"
          }`}
        >
          {item.text}
        </p>
      ))}
    </div>
  );
}
