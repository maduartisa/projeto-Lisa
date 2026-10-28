import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "MJ Comercial e Tecnologia",
  description:
    "Gestão comercial, catálogo, estoque, vendas e atendimento da MJ Comercial e Tecnologia.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
