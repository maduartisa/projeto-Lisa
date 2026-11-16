import type { OrderStatus, Role } from "@/lib/types";

export function formatCurrency(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number.isFinite(amount) ? amount : 0);
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR").format(date);
}

export function formatQuantity(value: string | number): string {
  const amount = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 3,
  }).format(Number.isFinite(amount) ? amount : 0);
}

export const roleLabels: Record<Role, string> = {
  company_admin: "Administradora",
  counter_operator: "Operação de balcão",
  inventory_manager: "Gestão de estoque",
  human_support: "Atendimento",
};

export const statusLabels: Record<OrderStatus, string> = {
  quote: "Orçamento",
  pending: "Pendente",
  separating: "Em separação",
  ready_for_pickup: "Pronto para retirada",
  in_transit: "Em trânsito",
  completed: "Concluído",
  cancelled: "Cancelado",
};
