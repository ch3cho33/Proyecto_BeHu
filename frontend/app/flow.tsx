"use client";

import {
  ArrowDownLeft,
  Banknote,
  Bus,
  Copy,
  CreditCard,
  Download,
  Gamepad2,
  GraduationCap,
  Plus,
  QrCode,
  Send,
  Shirt,
  Utensils,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import QRCode from "qrcode";

export type Draft = {
  monto: string;
  categoria: string;
  metodo: string;
  bucket: string;
  notas: string;
  redondear: boolean;
};

export type FlowMove = {
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

const CATEGORIES = [
  { id: "COMIDA", label: "Comida", icon: Utensils },
  { id: "TRANSPORTE", label: "Transporte", icon: Bus },
  { id: "ENTRETENIMIENTO", label: "Ocio", icon: Gamepad2 },
  { id: "EDUCACION", label: "Educación", icon: GraduationCap },
  { id: "ROPA", label: "Ropa", icon: Shirt },
];

const METHODS = [
  { id: "TARJETA_DEBITO", label: "Tarjeta BeHu", icon: CreditCard },
  { id: "TRANSFERENCIA", label: "Transferencia", icon: Send },
  { id: "EFECTIVO", label: "Efectivo", icon: Banknote },
];

function money(value: string | number, currency = "COP") {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency, maximumFractionDigits: 0 }).format(Number(value) || 0);
}

function dayLabel(iso: string) {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "Hoy";
  if (date.toDateString() === yesterday.toDateString()) return "Ayer";
  return "Anteriores";
}

export function QuickActions({ onOpen }: { onOpen: (action: "gasto" | "ingreso" | "enviar" | "qr") => void }) {
  const items = [
    { id: "gasto" as const, label: "Registrar gasto", icon: Plus },
    { id: "ingreso" as const, label: "Recargar", icon: ArrowDownLeft },
    { id: "enviar" as const, label: "Enviar", icon: Send },
    { id: "qr" as const, label: "Llave BeHu", icon: QrCode },
  ];
  return (
    <div className="grid grid-cols-4 gap-3">
      {items.map((item) => (
        <button key={item.id} type="button" className="flex flex-col items-center gap-2 text-xs text-muted" onClick={() => onOpen(item.id)}>
          <span className="grid h-14 w-14 place-items-center rounded-full border border-line-strong bg-surface-strong text-ink">
            <item.icon size={20} />
          </span>
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function KeyChip({ llave, onCopy }: { llave: string; onCopy: () => void }) {
  return (
    <button type="button" className="btn-secondary inline-flex h-9 items-center gap-2 px-3 text-sm" onClick={onCopy}>
      <Copy size={14} /> @{llave || "behu"}
    </button>
  );
}

export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-30 bg-black/60" onClick={onClose}>
      <div
        className="absolute inset-x-0 bottom-0 max-h-[88vh] overflow-auto rounded-t-sheet border border-line bg-elevated p-5 md:inset-y-0 md:left-auto md:right-0 md:w-[420px] md:rounded-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="btn-secondary h-8 px-3 text-sm" type="button" onClick={onClose}>Cerrar</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function AmountField({ value, currency, onChange }: { value: string; currency: string; onChange: (value: string) => void }) {
  const shown = value ? money(value, currency) : money(0, currency);
  return (
    <label className="block text-center">
      <input
        inputMode="numeric"
        className="w-full bg-transparent text-center text-4xl font-bold tracking-tight outline-none"
        value={shown}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, ""))}
      />
    </label>
  );
}

export function MovementDesk({
  moves,
  currency,
  llave,
  juniors,
  onSpend,
  onIncome,
  onSendBudget,
  onSendKey,
  onReceipt,
  onCopy,
  request,
  categories,
}: {
  moves: FlowMove[];
  currency: string;
  llave: string;
  juniors: { cuenta_junior_id: string; nombres: string; apellidos: string }[];
  onSpend: (draft: Draft, force?: boolean) => Promise<{ redondeo?: string; meta_redondeo?: string | null } | void>;
  onIncome: (monto: string) => Promise<unknown>;
  onSendBudget: (cuentaId: string, monto: string) => Promise<unknown>;
  onSendKey: (llave: string, monto: string) => Promise<unknown>;
  onReceipt: (id: string) => Promise<{ asientos: { naturaleza: string; cuenta: string; monto: string; sello_hmac?: string | null }[]; transaccion: FlowMove }>;
  onCopy: (text: string) => void;
  request?: { action: "gasto" | "ingreso" | "enviar" | "qr"; id: number } | null;
  categories?: { codigo: string; nombre: string }[];
}) {
  const [sheet, setSheet] = useState<"gasto" | "ingreso" | "enviar" | "qr" | null>(null);
  const [draft, setDraft] = useState<Draft>({ monto: "", categoria: "COMIDA", metodo: "TARJETA_DEBITO", bucket: "DESEOS", notas: "", redondear: false });
  const [filter, setFilter] = useState("Todos");
  const [query, setQuery] = useState("");
  const [receipt, setReceipt] = useState<{ asientos: { naturaleza: string; cuenta: string; monto: string; sello_hmac?: string | null }[]; transaccion: FlowMove } | null>(null);
  const [qr, setQr] = useState("");
  const [sendAmount, setSendAmount] = useState("20000");
  const [destKey, setDestKey] = useState("");
  const chips = categories?.length ? categories.map((item) => ({ id: item.codigo, label: item.nombre, icon: CATEGORIES.find((base) => base.id === item.codigo)?.icon || CreditCard })) : CATEGORIES;

  useEffect(() => {
    if (request) setSheet(request.action);
  }, [request]);

  useEffect(() => {
    if (sheet !== "qr" || !llave) return;
    QRCode.toString(`behu://pay/${llave}`, { type: "svg", margin: 1, color: { dark: "#F8FAFC", light: "#111726" } }).then(setQr);
  }, [sheet, llave]);

  const visible = moves.filter((move) => {
    const text = `${move.descripcion || ""} ${move.comercio || ""} ${move.categoria || ""}`.toLowerCase();
    if (query && !text.includes(query.toLowerCase())) return false;
    if (filter === "Ingresos") return move.tipo === "INGRESO" || move.tipo === "ASIGNACION_PRESUPUESTO";
    if (filter === "Gastos") return move.tipo === "COMPRA";
    if (filter === "Impulsivos") return Boolean(move.is_impulsive);
    return true;
  });
  const groups = useMemo(() => {
    const order = ["Hoy", "Ayer", "Anteriores"];
    return order
      .map((label) => ({ label, items: visible.filter((move) => dayLabel(move.created_at) === label) }))
      .filter((group) => group.items.length);
  }, [visible]);

  function exportCsv() {
    const header = "fecha,tipo,monto,categoria,metodo,bucket,nota\n";
    const rows = visible.map((move) =>
      [move.created_at, move.tipo, move.monto, move.categoria || "", move.metodo_pago || "", move.bucket || "", (move.descripcion || move.comercio || "").replaceAll(",", " ")].join(","),
    );
    const blob = new Blob([header + rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "extracto-behu.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Movimientos</h1>
          <p className="text-sm text-[#94A3B8]">Extracto agrupado por fecha, con comprobante y CSV.</p>
        </div>
        <button className="h-10 rounded-xl bg-white px-4 text-sm font-semibold text-[#090D16]" type="button" onClick={() => setSheet("gasto")}>+ Nuevo movimiento</button>
        <button className="btn-secondary inline-flex h-9 items-center gap-2 px-3 text-sm" type="button" onClick={exportCsv}>
          <Download size={14} /> Exportar extracto (CSV)
        </button>
      </div>
      <QuickActions onOpen={(action) => { setSheet(action); if (action === "gasto") setDraft((item) => ({ ...item, monto: "" })); }} />
      <div className="flex flex-wrap gap-2">
        {["Todos", "Ingresos", "Gastos", "Impulsivos"].map((item) => (
          <button key={item} className={filter === item ? "btn-primary h-8 px-3 text-xs" : "btn-secondary h-8 px-3 text-xs"} type="button" onClick={() => setFilter(item)}>{item}</button>
        ))}
        <input className="h-8 min-w-40 flex-1 rounded-card border border-line bg-surface px-3 text-sm" placeholder="Buscar comercio o nota" value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      {groups.length === 0 && <p className="panel p-4 text-sm text-muted">No hay movimientos con ese filtro.</p>}
      {groups.map((group) => (
        <div key={group.label} className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-dim">{group.label}</p>
          {group.items.map((move) => {
            const income = move.tipo === "INGRESO" || move.tipo === "ASIGNACION_PRESUPUESTO";
            const Icon = CATEGORIES.find((item) => item.id === move.categoria)?.icon || CreditCard;
            return (
              <button key={move.id} type="button" className="panel flex w-full items-center gap-3 p-3 text-left" onClick={async () => setReceipt(await onReceipt(move.id))}>
                <span className="grid h-10 w-10 place-items-center rounded-full bg-surface-strong text-primary"><Icon size={16} /></span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm">{move.descripcion || move.comercio || move.tipo}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-1 text-xs text-dim">
                    {new Date(move.created_at).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
                    {move.metodo_pago && <em className="rounded-full border border-line px-1.5 not-italic">{move.metodo_pago}</em>}
                    {move.bucket && <em className="rounded-full border border-line px-1.5 not-italic">{move.bucket}</em>}
                    {move.is_impulsive && <em className="rounded-full bg-warning/15 px-1.5 not-italic text-warning">Impulsivo</em>}
                  </span>
                </span>
                <span className={income ? "text-sm font-semibold text-success" : "text-sm font-semibold"}>{income ? "+" : "-"}{money(move.monto, currency)}</span>
              </button>
            );
          })}
        </div>
      ))}
      {sheet === "gasto" && (
        <Sheet title="Registrar gasto" onClose={() => setSheet(null)}>
          <AmountField currency={currency} value={draft.monto} onChange={(monto) => setDraft({ ...draft, monto })} />
          <p className="mt-4 text-xs text-dim">Categoría</p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {chips.map((item) => (
              <button key={item.id} type="button" className={`flex items-center gap-2 rounded-card border px-3 py-2 text-sm ${draft.categoria === item.id ? "border-primary bg-surface-strong" : "border-line"}`} onClick={() => setDraft({ ...draft, categoria: item.id })}>
                <item.icon size={16} /> {item.label}
              </button>
            ))}
          </div>
          <p className="mt-4 text-xs text-dim">Método</p>
          <div className="mt-2 grid gap-2">
            {METHODS.map((item) => (
              <button key={item.id} type="button" className={`flex items-center gap-2 rounded-card border px-3 py-2 text-sm ${draft.metodo === item.id ? "border-primary bg-surface-strong" : "border-line"}`} onClick={() => setDraft({ ...draft, metodo: item.id })}>
                <item.icon size={16} /> {item.label}
              </button>
            ))}
          </div>
          <button type="button" className={`mt-4 flex h-11 w-full items-center justify-between rounded-card border px-3 text-sm ${draft.redondear ? "border-success" : "border-line"}`} onClick={() => setDraft({ ...draft, redondear: !draft.redondear })}>
            Redondeo automático al ahorro
            <span className={`h-6 w-10 rounded-full ${draft.redondear ? "bg-success" : "bg-surface-strong"}`} />
          </button>
          <button className="btn-primary mt-4 h-11 w-full" type="button" onClick={async () => { await onSpend(draft); setSheet(null); }}>Registrar</button>
        </Sheet>
      )}
      {sheet === "ingreso" && (
        <Sheet title="Recargar" onClose={() => setSheet(null)}>
          <AmountField currency={currency} value={draft.monto} onChange={(monto) => setDraft({ ...draft, monto })} />
          <div className="mt-4 grid grid-cols-2 gap-2">
            {["20000", "50000", "100000", "500000"].map((amount) => (
              <button key={amount} className="btn-secondary h-10 text-sm" type="button" onClick={() => setDraft({ ...draft, monto: amount })}>+{money(amount, currency)}</button>
            ))}
          </div>
          <button className="btn-primary mt-4 h-11 w-full" type="button" onClick={async () => { await onIncome(draft.monto); setSheet(null); }}>Recibir ingreso</button>
        </Sheet>
      )}
      {sheet === "enviar" && (
        <Sheet title="Enviar" onClose={() => setSheet(null)}>
          <AmountField currency={currency} value={sendAmount} onChange={setSendAmount} />
          <p className="mt-4 text-xs text-dim">Contactos</p>
          <div className="mt-2 flex gap-2 overflow-auto">
            {juniors.map((junior) => (
              <button key={junior.cuenta_junior_id} className="panel w-24 shrink-0 p-3 text-center text-xs" type="button" onClick={() => onSendBudget(junior.cuenta_junior_id, sendAmount)}>
                <span className="mx-auto grid h-10 w-10 place-items-center rounded-full bg-surface-strong font-semibold">{junior.nombres.slice(0, 1)}</span>
                <span className="mt-2 block">{junior.nombres}</span>
              </button>
            ))}
          </div>
          <input className="mt-4 h-11 w-full rounded-card border border-line bg-surface px-3" placeholder="@llave.behu" value={destKey} onChange={(event) => setDestKey(event.target.value)} />
          <button className="btn-primary mt-3 h-11 w-full" type="button" onClick={() => onSendKey(destKey, sendAmount)}>Enviar a la llave</button>
        </Sheet>
      )}
      {sheet === "qr" && (
        <Sheet title="Llave BeHu" onClose={() => setSheet(null)}>
          <div className="mx-auto w-56" dangerouslySetInnerHTML={{ __html: qr }} />
          <button className="btn-primary mt-4 h-11 w-full" type="button" onClick={() => onCopy(`@${llave}`)}>Copiar @{llave}</button>
        </Sheet>
      )}
      {receipt && (
        <Sheet title="Comprobante BeHu" onClose={() => setReceipt(null)}>
          <p className="font-mono text-xs text-dim">Ref {receipt.transaccion.id}</p>
          <p className="mt-2 text-3xl font-bold">{money(receipt.transaccion.monto, currency)}</p>
          <p className="text-sm text-muted">{new Date(receipt.transaccion.created_at).toLocaleString("es-CO")}</p>
          <ul className="mt-4 space-y-2 text-sm">
            {receipt.asientos.map((line, index) => (
              <li key={index} className="flex justify-between border-b border-line py-2">
                <span>{line.naturaleza} · {line.cuenta}{line.sello_hmac ? ` · sello ${line.sello_hmac.slice(0, 8)}` : ""}</span>
                <span>{money(line.monto, currency)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button className="btn-secondary h-10 text-sm" type="button" onClick={() => { setDraft({ monto: String(Math.round(Number(receipt.transaccion.monto))), categoria: receipt.transaccion.categoria || "COMIDA", metodo: receipt.transaccion.metodo_pago || "TARJETA_DEBITO", bucket: receipt.transaccion.bucket || "DESEOS", notas: receipt.transaccion.descripcion || "", redondear: false }); setReceipt(null); setSheet("gasto"); }}>Repetir</button>
            <button className="btn-secondary h-10 text-sm" type="button" onClick={exportCsv}>Exportar CSV</button>
          </div>
        </Sheet>
      )}
    </section>
  );
}
