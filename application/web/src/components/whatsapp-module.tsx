"use client";

import { MessageCircle, Send, Smartphone } from "lucide-react";
import { useMemo, useState } from "react";

import { formatCurrency, formatDate, statusLabels } from "@/lib/format";
import type { Customer, Order, Product } from "@/lib/types";
import { Button, Field, SelectField } from "@/components/ui";

type Props = {
  customers: Customer[];
  orders: Order[];
  products: Product[];
  tenantSlug: string;
};

function whatsappUrl(phone: string, message: string) {
  let number = phone.replace(/\D/g, "");
  if (number.length === 10 || number.length === 11) number = `55${number}`;
  if (number.length < 12 || number.length > 15) return null;
  return `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
}

export function WhatsAppModule({ customers, orders, products, tenantSlug }: Props) {
  const [customerId, setCustomerId] = useState("");
  const [template, setTemplate] = useState("welcome");
  const [customMessage, setCustomMessage] = useState("");
  const customer = customers.find((item) => item.id === customerId);
  const latestOrder = useMemo(
    () => orders.find((order) => order.customer_id === customerId),
    [customerId, orders],
  );
  const latestOrderProduct = latestOrder?.items
    .map((item) => products.find((product) => product.id === item.product_id)?.name)
    .filter(Boolean)
    .join(", ");

  const message = customMessage.trim() || (() => {
    if (!customer) return "";
    if (template === "order") {
      if (!latestOrder) return `Olá, ${customer.name}! Não encontramos um pedido recente associado ao seu cadastro. Se precisar, estamos à disposição.`;
      return `Olá, ${customer.name}! Atualização do seu pedido #${latestOrder.id.slice(0, 8).toUpperCase()}. Status: ${statusLabels[latestOrder.status]}. Itens: ${latestOrderProduct || "em separação"}. Total: ${formatCurrency(latestOrder.total)}.`;
    }
    if (template === "catalog") {
      const origin = typeof window === "undefined" ? "" : window.location.origin;
      return `Olá, ${customer.name}! Confira nosso catálogo online: ${origin}/catalog/${tenantSlug}`;
    }
    if (template === "custom") return "";
    return `Olá, ${customer.name}! Aqui é da equipe comercial. Como podemos ajudar você hoje?`;
  })();
  const url = customer?.phone ? whatsappUrl(customer.phone, message) : null;

  return (
    <div className="page-content">
      <section className="page-title-row">
        <div>
          <p className="eyebrow">ATENDIMENTO E RELACIONAMENTO</p>
          <h1>WhatsApp</h1>
          <p className="page-lead">Abra conversas com mensagens prontas, atualizações de pedido e link do catálogo.</p>
        </div>
      </section>

      <div className="whatsapp-layout">
        <section className="surface-card whatsapp-card">
          <div className="whatsapp-card-heading">
            <span className="whatsapp-icon"><MessageCircle size={20} /></span>
            <div><h2>Iniciar conversa</h2><p>A mensagem abre no WhatsApp para você revisar e enviar.</p></div>
          </div>
          <div className="form-grid form-grid-single">
            <SelectField label="Cliente" onChange={(event) => {
              setCustomerId(event.target.value);
              setCustomMessage("");
            }} value={customerId}>
              <option value="">Selecione um cliente</option>
              {customers.map((item) => <option key={item.id} value={item.id}>{item.name}{item.phone ? ` · ${item.phone}` : " · sem telefone"}</option>)}
            </SelectField>
            {customer ? <div className="whatsapp-contact">
              <span className="customer-avatar">{customer.name.charAt(0).toUpperCase()}</span>
              <span><strong>{customer.name}</strong><small>{customer.phone || "Cadastre um telefone para abrir a conversa"}</small></span>
            </div> : null}
            <SelectField label="Modelo de mensagem" onChange={(event) => {
              setTemplate(event.target.value);
              setCustomMessage("");
            }} value={template}>
              <option value="welcome">Atendimento geral</option>
              <option value="order">Atualização do pedido mais recente</option>
              <option value="catalog">Enviar link do catálogo</option>
              <option value="custom">Escrever mensagem personalizada</option>
            </SelectField>
            {template === "custom" || customMessage ? (
              <label className="field">
                <span>Mensagem</span>
                <textarea maxLength={1200} onChange={(event) => setCustomMessage(event.target.value)} placeholder="Escreva sua mensagem..." rows={5} value={customMessage} />
              </label>
            ) : <div className="whatsapp-preview"><span>PRÉVIA DA MENSAGEM</span><p>{message || "Selecione um cliente para visualizar a mensagem."}</p></div>}
            {customer?.phone && url && message ? (
              <a className="button button-primary whatsapp-send" href={url} rel="noreferrer" target="_blank">
                <Send size={16} /> Abrir conversa no WhatsApp
              </a>
            ) : <p className="whatsapp-hint"><Smartphone size={15} />{!customer?.phone || !url ? "Selecione um cliente com telefone cadastrado em formato válido para o WhatsApp." : "Escreva sua mensagem para habilitar o WhatsApp."}</p>}
          </div>
          <p className="checkout-disclaimer">Integração atual via link oficial wa.me: não envia mensagens em segundo plano nem registra entrega. Mensagens automáticas e WhatsApp Business API exigem uma conta Meta e credenciais autorizadas.</p>
        </section>

        <section className="surface-card whatsapp-guide">
          <span className="eyebrow">O QUE JÁ FUNCIONA</span>
          <h2>Atendimento conectado à operação</h2>
          <ul>
            <li>Conversa direta com clientes cadastrados.</li>
            <li>Texto personalizado antes de abrir o aplicativo.</li>
            <li>Atalho com o status e o total do pedido mais recente.</li>
            <li>Compartilhamento do catálogo digital.</li>
          </ul>
          <div className="whatsapp-latest">
            <strong>Pedidos recentes</strong>
            {orders.slice(0, 4).map((order) => {
              const orderCustomer = customers.find((item) => item.id === order.customer_id);
              return <div key={order.id}><span>{orderCustomer?.name || "Cliente"}<small> · {formatDate(order.created_at)}</small></span><b>{formatCurrency(order.total)}</b></div>;
            })}
            {!orders.length ? <small>Nenhum pedido cadastrado ainda.</small> : null}
          </div>
          <Button onClick={() => setTemplate("order")} variant="secondary">Preparar atualização de pedido</Button>
        </section>
      </div>
    </div>
  );
}
