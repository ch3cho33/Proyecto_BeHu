import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BeHu",
  description: "Sandbox fintech de cuentas parentales y BeHu Mini",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
