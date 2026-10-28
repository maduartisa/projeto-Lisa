"use client";

import {
  ArrowDown,
  ArrowDownToLine,
  ArrowLeft,
  ArrowUp,
  ArrowUpRight,
  ArrowUpToLine,
  Banknote,
  Box,
  Check,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  ClipboardList,
  Clock3,
  Command,
  Ellipsis,
  ExternalLink,
  FileClock,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
  Package,
  Plus,
  ReceiptText,
  RefreshCw,
  Settings2,
  ShoppingBag,
  Sparkles,
  Users,
  UserRoundCog,
  Truck,
  X,
} from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import { ApiError, api, queryString } from "@/lib/api";
import { formatCurrency, formatDate, formatQuantity, roleLabels, statusLabels } from "@/lib/format";
import type {
  Customer,
  InventoryMovement,
  Order,
  OrderStatus,
  Product,
  Role,
  Session,
} from "@/lib/types";
import {
  Button,
  Field,
  FormError,
  FormShell,
  Modal,
  SearchBox,
  SelectField,
  TextAreaField,
  ToastProvider,
  useToast,
} from "@/components/ui";
import { OperationsModule, type OperationsView } from "@/components/operations-module";
import { WhatsAppModule } from "@/components/whatsapp-module";

type View = "overview" | "pos" | "orders" | "products" | "inventory" | "customers" | "whatsapp" | OperationsView;
type DataSet = { products: Product[]; customers: Customer[]; orders: Order[] };
type ProductDraft = {
  sku: string;
  name: string;
  category: string;
  size: string;
  color: string;
  price: string;
  cost_price: string;
  icms_rate: string;
  ipi_rate: string;
  pis_rate: string;
  cofins_rate: string;
  stock_quantity: string;
  description: string;
  image_url: string;
  is_active: boolean;
};
type OrderLine = { product_id: string; quantity: string };

const EMPTY_DATA: DataSet = { products: [], customers: [], orders: [] };
const NAV_ITEMS: { id: View; label: string; icon: typeof LayoutDashboard; roles: Role[] }[] = [
  {
    id: "overview",
    label: "Visão geral",
    icon: LayoutDashboard,
    roles: ["company_admin", "counter_operator", "inventory_manager", "human_support"],
  },
  { id: "pos", label: "PDV / Vendas", icon: ShoppingBag, roles: ["company_admin", "counter_operator"] },
  { id: "orders", label: "Pedidos", icon: ClipboardList, roles: ["company_admin", "counter_operator"] },
  {
    id: "products",
    label: "Produtos",
    icon: Package,
    roles: ["company_admin", "counter_operator", "inventory_manager"],
  },
  {
    id: "inventory",
    label: "Estoque",
    icon: Box,
    roles: ["company_admin", "inventory_manager"],
  },
  {
    id: "customers",
    label: "Clientes",
    icon: Users,
    roles: ["company_admin", "counter_operator", "human_support"],
  },
  { id: "suppliers", label: "Fornecedores", icon: Truck, roles: ["company_admin", "inventory_manager"] },
  { id: "purchases", label: "Compras", icon: ReceiptText, roles: ["company_admin", "inventory_manager"] },
  { id: "employees", label: "Funcionários", icon: UserRoundCog, roles: ["company_admin"] },
  { id: "finance", label: "Financeiro", icon: Banknote, roles: ["company_admin"] },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle, roles: ["company_admin", "counter_operator"] },
  { id: "access_logs", label: "Auditoria", icon: FileClock, roles: ["company_admin"] },
];

const PRODUCT_BLANK: ProductDraft = {
  sku: "",
  name: "",
  category: "",
  size: "",
  color: "",
  price: "",
  cost_price: "0.00",
  icms_rate: "0.00",
  ipi_rate: "0.00",
  pis_rate: "0.00",
  cofins_rate: "0.00",
  stock_quantity: "0",
  description: "",
  image_url: "",
  is_active: true,
};

function currencyAmount(value: string) {
  const parsed = Number(value.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function managementPermissions(role: Role) {
  return {
    products: ["company_admin", "counter_operator", "inventory_manager"].includes(role),
    customers: ["company_admin", "counter_operator", "human_support"].includes(role),
    orders: ["company_admin", "counter_operator"].includes(role),
    inventory: ["company_admin", "inventory_manager"].includes(role),
    editProducts: ["company_admin", "inventory_manager"].includes(role),
    editOrders: ["company_admin", "counter_operator"].includes(role),
  };
}

function LoginScreen({
  onLogin,
}: {
  onLogin: (token: string, context: Session) => void;
}) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tenantSlug, setTenantSlug] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const issued = await api<{ access_token: string }>("/api/v1/auth/token", undefined, {
        method: "POST",
        body: JSON.stringify({ email, password, tenant_slug: tenantSlug }),
      });
      const context = await api<Omit<Session, "access_token">>(
        "/api/v1/auth/me",
        issued.access_token,
      );
      onLogin(issued.access_token, { ...context, access_token: issued.access_token });
      toast("success", `Boas-vindas à ${context.tenant.display_name}.`);
    } catch (issue) {
      setError(
        issue instanceof Error
          ? issue.message
          : "Não foi possível iniciar sua sessão.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-art" aria-hidden="true">
        <div className="login-orbit orbit-one" />
        <div className="login-orbit orbit-two" />
        <div className="login-art-content">
          <div className="brand-mark brand-mark-light">
            <Command size={24} strokeWidth={2.2} />
          </div>
          <p className="eyebrow eyebrow-light">GESTÃO COMERCIAL</p>
          <h1>Seu negócio,<br />em boas mãos.</h1>
          <p className="login-art-copy">
            Produtos, pessoas e pedidos conectados em um só lugar.
          </p>
          <div className="login-art-note">
            <span className="online-dot" />
            Um espaço seguro para sua equipe
          </div>
        </div>
        <div className="login-plant plant-a" />
        <div className="login-plant plant-b" />
        <div className="login-art-stamp"><Sparkles size={17} /> Simplesmente organizado</div>
      </div>
      <section className="login-panel">
        <div className="login-form-wrap">
          <div className="brand-lockup login-brand">
            <span className="brand-mark brand-mark-initials">MJ</span>
            <span className="brand-name">MJ<small>COMERCIAL E TECNOLOGIA</small></span>
          </div>
          <p className="eyebrow">ACESSO DA EQUIPE</p>
          <h2>Que bom ter você<br />por aqui.</h2>
          <p className="login-subtitle">Entre para cuidar da sua operação.</p>
          <form className="login-form" onSubmit={submit}>
            <Field
              autoComplete="email"
              label="E-mail"
              onChange={(event) => setEmail(event.target.value)}
              placeholder="voce@suaempresa.com"
              required
              type="email"
              value={email}
            />
            <Field
              autoComplete="current-password"
              label="Senha"
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Sua senha"
              required
              type="password"
              value={password}
            />
            <Field
              autoComplete="organization"
              label="Identificador da empresa"
              onChange={(event) =>
                setTenantSlug(event.target.value.toLowerCase().replace(/\s/g, "-"))
              }
              placeholder="ex: minha-empresa"
              required
              value={tenantSlug}
            />
            <FormError>{error}</FormError>
            <Button className="login-submit" loading={busy} type="submit">
              Entrar no painel <ArrowUpRight size={17} />
            </Button>
          </form>
          <p className="login-help">
            <CircleHelp size={15} />
            Precisa de acesso? Fale com a pessoa administradora da sua empresa.
          </p>
          <p className="login-legal">Acesso protegido • Seus dados pertencem à sua empresa</p>
        </div>
      </section>
    </main>
  );
}

function Sidebar({
  session,
  view,
  onNavigate,
  onLogout,
  open,
  onClose,
}: {
  session: Session;
  view: View;
  onNavigate: (view: View) => void;
  onLogout: () => void;
  open: boolean;
  onClose: () => void;
}) {
  const items = NAV_ITEMS.filter((item) => item.roles.includes(session.tenant.role));
  return (
    <>
      {open ? <button className="mobile-sidebar-backdrop" onClick={onClose} aria-label="Fechar menu" /> : null}
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <span className="brand-mark brand-mark-initials">MJ</span>
          <span className="brand-name">MJ<small>COMERCIAL E TECNOLOGIA</small></span>
        </div>
        <div className="workspace-switcher">
          <div className="workspace-avatar">L</div>
          <div className="workspace-copy">
            <span>Seu espaço</span>
            <strong title="Lisa Comercial">Lisa Comercial</strong>
          </div>
          <ChevronDown size={16} />
        </div>
        <span className="nav-caption">OPERAÇÃO</span>
        <nav className="side-nav" aria-label="Navegação principal">
          {items.map(({ id, label, icon: Icon }) => (
            <button
              aria-current={view === id ? "page" : undefined}
              className={`nav-item ${view === id ? "nav-item-active" : ""}`}
              key={id}
              onClick={() => {
                onNavigate(id);
                onClose();
              }}
              type="button"
            >
              <Icon size={18} strokeWidth={1.8} />
              <span>{label}</span>
              {id === "orders" ? <span className="nav-pulse" /> : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-card">
          <div className="sidebar-card-icon"><Sparkles size={16} /></div>
          <strong>Um passo de cada vez</strong>
          <p>Seu painel está pronto para organizar a rotina.</p>
          <a href={`/catalog/${session.tenant.slug}`} rel="noreferrer" target="_blank">
            Ver catálogo público <ExternalLink size={13} />
          </a>
        </div>
        <div className="sidebar-divider" />
        <div className="sidebar-user">
          <div className="user-avatar">{session.user.email.charAt(0).toUpperCase()}</div>
          <div className="user-copy">
            <strong>{session.user.email.split("@")[0]}</strong>
            <span>{roleLabels[session.tenant.role]}</span>
          </div>
          <button aria-label="Sair da conta" className="icon-button logout-button" onClick={onLogout} title="Sair" type="button">
            <LogOut size={17} />
          </button>
        </div>
      </aside>
    </>
  );
}

function Header({
  title,
  subtitle,
  onMenu,
  action,
  session,
}: {
  title: string;
  subtitle: string;
  onMenu: () => void;
  action?: ReactNode;
  session: Session;
}) {
  return (
    <header className="topbar">
      <div className="topbar-heading">
        <button aria-label="Abrir menu" className="icon-button mobile-menu-button" onClick={onMenu} type="button">
          <Menu size={21} />
        </button>
        <div>
          <div className="breadcrumb"><span>Início</span><ChevronRight size={13} /><strong>{title}</strong></div>
          <p className="topbar-subtitle">{subtitle}</p>
        </div>
      </div>
      <div className="topbar-actions">
        {action}
        <a
          aria-label="Abrir catálogo público em nova aba"
          className="icon-button public-link"
          href={`/catalog/${session.tenant.slug}`}
          rel="noreferrer"
          target="_blank"
          title="Ver catálogo público"
        >
          <ExternalLink size={18} />
        </a>
        <div className="topbar-avatar">{session.user.email.charAt(0).toUpperCase()}</div>
      </div>
    </header>
  );
}

function MetricCard({
  label,
  value,
  icon: Icon,
  tone,
  footnote,
  footnoteTone = "neutral",
}: {
  label: string;
  value: string | number;
  icon: typeof Package;
  tone: string;
  footnote: string;
  footnoteTone?: "positive" | "warning" | "neutral";
}) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <span className={`metric-icon metric-${tone}`}><Icon size={19} strokeWidth={1.9} /></span>
        <button aria-label={`Detalhes: ${label}`} className="icon-button metric-menu" title={label} type="button">
          <Ellipsis size={19} />
        </button>
      </div>
      <p className="metric-label">{label}</p>
      <strong className="metric-value">{value}</strong>
      <p className={`metric-footnote footnote-${footnoteTone}`}>
        {footnoteTone === "positive" ? <ArrowUpRight size={13} /> : null}
        {footnote}
      </p>
    </article>
  );
}

function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`status-badge status-${status}`}>{statusLabels[status]}</span>;
}

function Overview({
  session,
  data,
  permissions,
  onNavigate,
  onCreateOrder,
  onRefresh,
  loading,
}: {
  session: Session;
  data: DataSet;
  permissions: ReturnType<typeof managementPermissions>;
  onNavigate: (view: View) => void;
  onCreateOrder: () => void;
  onRefresh: () => void;
  loading: boolean;
}) {
  const activeProducts = data.products.filter((product) => product.is_active);
  const outOfStock = activeProducts.filter((product) => Number(product.stock_quantity) <= 0);
  const pendingOrders = data.orders.filter((order) =>
    ["quote", "pending", "separating", "ready_for_pickup", "in_transit"].includes(order.status),
  );
  const completedOrders = data.orders.filter((order) => order.status === "completed");
  const completeValue = completedOrders.reduce((sum, order) => sum + Number(order.total), 0);
  const maxBars = Math.max(1, ...data.orders.map((order) => Number(order.total)));
  const recentOrders = data.orders.slice(0, 5);
  const bars = useMemo(() => {
    const now = new Date();
    return Array.from({ length: 7 }, (_, index) => {
      const day = new Date(now);
      day.setHours(0, 0, 0, 0);
      day.setDate(day.getDate() - (6 - index));
      const next = new Date(day);
      next.setDate(next.getDate() + 1);
      const sum = data.orders
        .filter((order) => {
          const created = new Date(order.created_at);
          return created >= day && created < next;
        })
        .reduce((total, order) => total + Number(order.total), 0);
      return {
        label: new Intl.DateTimeFormat("pt-BR", { weekday: "short" })
          .format(day)
          .replace(".", ""),
        value: sum,
      };
    });
  }, [data.orders]);
  const maxBarValue = Math.max(1, ...bars.map((bar) => bar.value));

  return (
    <div className="page-content overview-content">
      <section className="welcome-banner">
        <div className="welcome-copy">
          <span className="welcome-kicker"><Sparkles size={14} /> SEU NEGÓCIO EM UM SÓ LUGAR</span>
          <h1>Bom trabalho,<br className="welcome-mobile-break" /> sua equipe está no ritmo.</h1>
          <p>Acompanhe o movimento e cuide do que precisa de atenção hoje.</p>
          <div className="welcome-actions">
            {permissions.orders ? (
              <Button onClick={onCreateOrder}><Plus size={16} /> Novo pedido</Button>
            ) : null}
            <Button onClick={() => onNavigate(permissions.products ? "products" : "customers")} variant="secondary">
              Ver operação <ArrowUpRight size={16} />
            </Button>
          </div>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="welcome-sun" />
          <div className="welcome-arc arc-back" />
          <div className="welcome-arc arc-front" />
          <div className="welcome-leaf leaf-one" />
          <div className="welcome-leaf leaf-two" />
          <div className="welcome-leaf leaf-three" />
          <div className="welcome-spark spark-one">✦</div>
          <div className="welcome-spark spark-two">✦</div>
        </div>
      </section>

      <div className="section-heading metric-heading">
        <div>
          <p className="eyebrow">RESUMO DA OPERAÇÃO</p>
          <h2>Como estão as coisas</h2>
        </div>
        <button aria-label="Atualizar indicadores" className={`icon-button refresh-button ${loading ? "refreshing" : ""}`} onClick={onRefresh} title="Atualizar" type="button">
          <RefreshCw size={17} />
        </button>
      </div>
      <section className="metric-grid" aria-label="Indicadores">
        {permissions.products ? (
          <MetricCard
            footnote={`${activeProducts.length} disponíveis no catálogo`}
            icon={Package}
            label="Produtos ativos"
            tone="lavender"
            value={loading ? "—" : activeProducts.length}
          />
        ) : null}
        {permissions.inventory ? (
          <MetricCard
            footnote={`${outOfStock.length} sem saldo`}
            footnoteTone={outOfStock.length ? "warning" : "positive"}
            icon={Box}
            label="Itens esgotados"
            tone="sand"
            value={loading ? "—" : outOfStock.length}
          />
        ) : null}
        {permissions.customers ? (
          <MetricCard
            footnote="cadastros da empresa"
            icon={Users}
            label="Clientes"
            tone="mint"
            value={loading ? "—" : data.customers.length}
          />
        ) : null}
        {permissions.orders ? (
          <MetricCard
            footnote={formatCurrency(completeValue)}
            footnoteTone="positive"
            icon={ShoppingBag}
            label="Pedidos concluídos"
            tone="peach"
            value={loading ? "—" : completedOrders.length}
          />
        ) : null}
      </section>

      <section className="overview-lower-grid">
        {permissions.orders ? (
          <article className="surface-card activity-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">ÚLTIMOS 7 DIAS</p>
                <h3>Movimento de pedidos</h3>
              </div>
              <button className="text-action" onClick={() => onNavigate("orders")} type="button">
                Ver pedidos <ArrowUpRight size={15} />
              </button>
            </div>
            <div className="chart-summary">
              <strong>{formatCurrency(data.orders.reduce((sum, order) => sum + Number(order.total), 0))}</strong>
              <span>em pedidos registrados</span>
            </div>
            <div className="bar-chart" role="img" aria-label="Valores dos pedidos por dia nos últimos sete dias">
              {bars.map((bar, index) => (
                <div className="bar-column" key={`${bar.label}-${index}`}>
                  <div className="bar-track">
                    <span
                      className={`bar-fill ${index === 6 ? "bar-fill-current" : ""}`}
                      style={{ height: `${Math.max(4, (bar.value / maxBarValue) * 100)}%` }}
                    />
                  </div>
                  <span>{bar.label}</span>
                </div>
              ))}
            </div>
            <div className="chart-footnote"><span className="legend-dot" /> Valor total dos pedidos por dia</div>
          </article>
        ) : null}
        <article className="surface-card pending-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">PRECISAM DE ATENÇÃO</p>
              <h3>Em andamento <span className="count-pill">{pendingOrders.length}</span></h3>
            </div>
            {permissions.orders ? (
              <button className="icon-button" onClick={() => onNavigate("orders")} title="Ver todos" type="button">
                <ArrowUpRight size={17} />
              </button>
            ) : null}
          </div>
          {permissions.orders ? (
            pendingOrders.length ? (
              <div className="pending-list">
                {pendingOrders.slice(0, 4).map((order) => {
                  const customer = data.customers.find((item) => item.id === order.customer_id);
                  return (
                    <div className="pending-row" key={order.id}>
                      <span className="pending-icon"><ShoppingBag size={16} /></span>
                      <span className="pending-info">
                        <strong>{customer?.name ?? "Cliente"}</strong>
                        <small>{formatDate(order.created_at)}</small>
                      </span>
                      <span className="pending-total">{formatCurrency(order.total)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-mini">
                <span className="empty-mini-icon"><Check size={18} /></span>
                <strong>Tudo em dia por aqui</strong>
                <span>Novos pedidos aparecem nesta lista.</span>
              </div>
            )
          ) : (
            <div className="empty-mini">
              <span className="empty-mini-icon"><Sparkles size={18} /></span>
              <strong>Seu espaço de trabalho</strong>
              <span>{roleLabels[session.tenant.role]} • dados da sua empresa</span>
            </div>
          )}
          {permissions.orders ? (
            <div className="pending-footer">
              <Clock3 size={15} />
              <span>{pendingOrders.length} pedidos aguardam uma ação</span>
            </div>
          ) : null}
        </article>
      </section>

      {permissions.orders ? (
        <section className="surface-card recent-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">ACOMPANHAMENTO</p>
              <h3>Pedidos recentes</h3>
            </div>
            <button className="text-action" onClick={() => onNavigate("orders")} type="button">
              Abrir central de pedidos <ArrowUpRight size={15} />
            </button>
          </div>
          <OrderTable orders={recentOrders} customers={data.customers} compact />
        </section>
      ) : null}
      <footer className="page-footnote">
        <span>Visualização vinculada a <strong>{session.tenant.display_name}</strong></span>
        <span>Os valores representam pedidos, não pagamentos recebidos.</span>
      </footer>
    </div>
  );
}

function OrderTable({
  orders,
  customers,
  onSelect,
  compact = false,
}: {
  orders: Order[];
  customers: Customer[];
  onSelect?: (order: Order) => void;
  compact?: boolean;
}) {
  if (!orders.length) {
    return <EmptyState title="Nenhum pedido encontrado" copy="Os pedidos da empresa aparecerão aqui." icon={ClipboardList} />;
  }
  return (
    <div className="table-scroll">
      <table className={`data-table ${compact ? "data-table-compact" : ""}`}>
        <thead>
          <tr>
            <th>Pedido</th>
            <th>Cliente</th>
            <th>Data</th>
            <th>Itens</th>
            <th>Valor cotado</th>
            <th>Status</th>
            {onSelect ? <th aria-label="Ações" /> : null}
          </tr>
        </thead>
        <tbody>
          {orders.map((order) => {
            const customer = customers.find((item) => item.id === order.customer_id);
            return (
              <tr key={order.id}>
                <td><span className="order-reference">#{order.id.slice(0, 8).toUpperCase()}</span></td>
                <td><span className="table-primary">{customer?.name ?? "Cliente"}</span></td>
                <td className="table-muted">{formatDate(order.created_at)}</td>
                <td className="table-muted">{order.items.length} {order.items.length === 1 ? "item" : "itens"}</td>
                <td><strong className="table-primary">{formatCurrency(order.total)}</strong></td>
                <td><StatusBadge status={order.status} /></td>
                {onSelect ? (
                  <td>
                    <button aria-label={`Abrir pedido ${order.id.slice(0, 8)}`} className="icon-button row-open" onClick={() => onSelect(order)} title="Abrir detalhes" type="button">
                      <ArrowUpRight size={16} />
                    </button>
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyState({
  title,
  copy,
  icon: Icon,
  action,
}: {
  title: string;
  copy: string;
  icon: typeof Package;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span className="empty-state-icon"><Icon size={22} /></span>
      <h3>{title}</h3>
      <p>{copy}</p>
      {action}
    </div>
  );
}

function OrdersPage({
  data,
  onCreate,
  onSelect,
  onRefresh,
  loading,
  mode = "orders",
}: {
  data: DataSet;
  onCreate: () => void;
  onSelect: (order: Order) => void;
  onRefresh: () => void;
  loading: boolean;
  mode?: "orders" | "pos";
}) {
  const [filter, setFilter] = useState("all");
  const filtered = filter === "all" ? data.orders : data.orders.filter((order) => order.status === filter);
  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><p className="eyebrow">{mode === "pos" ? "VENDA PRESENCIAL" : "ORÇAMENTOS E PEDIDOS"}</p><h1>{mode === "pos" ? "Ponto de venda" : "Central de pedidos"}</h1><p className="page-lead">{mode === "pos" ? "Registre uma venda de balcão e acompanhe estoque e conclusão." : "Organize cada etapa, da cotação à conclusão."}</p></div>
        <Button onClick={onCreate}><Plus size={17} /> {mode === "pos" ? "Iniciar venda" : "Novo pedido"}</Button>
      </div>
      {mode === "pos" ? <p className="checkout-disclaimer pos-disclaimer">O PDV cria um pedido para confirmação. Não há captura de pagamento integrada; o estoque é baixado ao concluir o pedido.</p> : null}
      <div className="toolbar">
        <div className="filter-tabs" role="tablist" aria-label="Filtrar pedidos">
          {[["all", "Todos"], ["quote", "Orçamentos"], ["pending", "Pendentes"], ["separating", "Em separação"], ["completed", "Concluídos"]].map(([value, label]) => (
            <button aria-selected={filter === value} className={`filter-tab ${filter === value ? "filter-tab-active" : ""}`} key={value} onClick={() => setFilter(value)} role="tab" type="button">{label}</button>
          ))}
        </div>
        <button aria-label="Atualizar pedidos" className={`icon-button refresh-button ${loading ? "refreshing" : ""}`} onClick={onRefresh} title="Atualizar" type="button"><RefreshCw size={17} /></button>
      </div>
      <section className="surface-card list-card">
        <div className="list-card-heading">
          <div><h2>{filter === "all" ? "Todos os pedidos" : statusLabels[filter] ?? "Pedidos"}</h2><p>{filtered.length} {filtered.length === 1 ? "registro" : "registros"} desta empresa</p></div>
        </div>
        <OrderTable customers={data.customers} onSelect={onSelect} orders={filtered} />
      </section>
    </div>
  );
}

function ProductForm({
  initial,
  onClose,
  onSave,
}: {
  initial?: Product;
  onClose: () => void;
  onSave: (draft: ProductDraft) => Promise<void>;
}) {
  const [draft, setDraft] = useState<ProductDraft>(
    initial
      ? {
          sku: initial.sku,
          name: initial.name,
          category: initial.category,
          size: initial.size ?? "",
          color: initial.color ?? "",
          price: initial.price,
          cost_price: initial.cost_price ?? "0.00",
          icms_rate: initial.icms_rate ?? "0.00",
          ipi_rate: initial.ipi_rate ?? "0.00",
          pis_rate: initial.pis_rate ?? "0.00",
          cofins_rate: initial.cofins_rate ?? "0.00",
          stock_quantity: initial.stock_quantity,
          description: initial.description ?? "",
          image_url: initial.image_url ?? "",
          is_active: initial.is_active,
        }
      : PRODUCT_BLANK,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSave(draft);
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível salvar o produto.");
    } finally {
      setBusy(false);
    }
  }

  function set<K extends keyof ProductDraft>(field: K, value: ProductDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  return (
    <Modal
      description="As informações serão visíveis apenas para a sua empresa."
      onClose={onClose}
      title={initial ? "Editar produto" : "Adicionar produto"}
    >
      <FormShell
        footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">{initial ? "Salvar alterações" : "Salvar produto"}</Button></>}
        onSubmit={submit}
      >
        <div className="form-grid">
          <p className="form-span page-lead">Cadastre cada combinação de tamanho e cor como uma variação com SKU e estoque próprios. As alíquotas são informativas e não geram cálculo automático de tributos.</p>
          <Field label="SKU" maxLength={64} onChange={(event) => set("sku", event.target.value)} placeholder="Ex.: LIM-001" required value={draft.sku} />
          <Field label="Nome do produto" maxLength={160} onChange={(event) => set("name", event.target.value)} placeholder="Nome comercial" required value={draft.name} />
          <Field label="Categoria" maxLength={100} onChange={(event) => set("category", event.target.value)} placeholder="Ex.: Limpeza" required value={draft.category} />
          <Field label="Tamanho / medida" maxLength={64} onChange={(event) => set("size", event.target.value)} placeholder="Ex.: P, M, G ou 500 ml" value={draft.size} />
          <Field label="Cor" maxLength={64} onChange={(event) => set("color", event.target.value)} placeholder="Ex.: Azul" value={draft.color} />
          <Field label="Preço (R$)" min="0" onChange={(event) => set("price", event.target.value)} placeholder="0,00" required step="0.01" type="number" value={draft.price} />
          <Field label="Preço de custo (R$)" min="0" onChange={(event) => set("cost_price", event.target.value)} placeholder="0,00" required step="0.01" type="number" value={draft.cost_price} />
          <Field label="ICMS (%)" min="0" max="100" onChange={(event) => set("icms_rate", event.target.value)} required step="0.01" type="number" value={draft.icms_rate} />
          <Field label="IPI (%)" min="0" max="100" onChange={(event) => set("ipi_rate", event.target.value)} required step="0.01" type="number" value={draft.ipi_rate} />
          <Field label="PIS (%)" min="0" max="100" onChange={(event) => set("pis_rate", event.target.value)} required step="0.01" type="number" value={draft.pis_rate} />
          <Field label="COFINS (%)" min="0" max="100" onChange={(event) => set("cofins_rate", event.target.value)} required step="0.01" type="number" value={draft.cofins_rate} />
          {!initial ? <Field label="Saldo inicial" min="0" onChange={(event) => set("stock_quantity", event.target.value)} step="0.001" type="number" value={draft.stock_quantity} /> : null}
          <Field label="Imagem (URL)" maxLength={2048} onChange={(event) => set("image_url", event.target.value)} placeholder="https://..." type="url" value={draft.image_url} />
          <TextAreaField className="form-span" label="Descrição" maxLength={2000} onChange={(event) => set("description", event.target.value)} placeholder="Detalhes importantes para a equipe e o catálogo..." rows={3} value={draft.description} />
          <label className="toggle-field form-span">
            <span className="toggle-copy"><strong>Produto ativo</strong><small>Produtos ativos podem aparecer no catálogo público.</small></span>
            <input checked={draft.is_active} onChange={(event) => set("is_active", event.target.checked)} type="checkbox" />
          </label>
        </div>
        <FormError>{error}</FormError>
      </FormShell>
    </Modal>
  );
}

function ProductsPage({
  data,
  canEdit,
  onCreate,
  onEdit,
  onRefresh,
}: {
  data: DataSet;
  canEdit: boolean;
  onCreate: () => void;
  onEdit: (product: Product) => void;
  onRefresh: () => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [active, setActive] = useState("all");
  const categories = [...new Set(data.products.map((product) => product.category))].sort((a, b) => a.localeCompare(b, "pt-BR"));
  const visible = data.products.filter((product) => {
    const matchSearch = `${product.name} ${product.sku} ${product.category}`.toLowerCase().includes(search.toLowerCase());
    const matchCategory = category === "all" || product.category === category;
    const matchActive = active === "all" || String(product.is_active) === active;
    return matchSearch && matchCategory && matchActive;
  });
  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><p className="eyebrow">CATÁLOGO DA EMPRESA</p><h1>Produtos</h1><p className="page-lead">Cadastre itens, preços e visibilidade do catálogo.</p></div>
        {canEdit ? <Button onClick={onCreate}><Plus size={17} /> Novo produto</Button> : null}
      </div>
      <div className="toolbar product-toolbar">
        <SearchBox onChange={setSearch} placeholder="Buscar por produto, SKU ou categoria" value={search} />
        <SelectField aria-label="Filtrar por categoria" label="Categoria" onChange={(event) => setCategory(event.target.value)} value={category}>
          <option value="all">Todas as categorias</option>
          {categories.map((item) => <option key={item} value={item}>{item}</option>)}
        </SelectField>
        <SelectField aria-label="Filtrar por status" label="Visibilidade" onChange={(event) => setActive(event.target.value)} value={active}>
          <option value="all">Todos</option><option value="true">Ativos</option><option value="false">Inativos</option>
        </SelectField>
        <button aria-label="Atualizar produtos" className="icon-button refresh-button" onClick={onRefresh} title="Atualizar" type="button"><RefreshCw size={17} /></button>
      </div>
      {visible.length ? (
        <section aria-label="Lista de produtos" className="product-grid">
          {visible.map((product, index) => (
            <article className="product-card" key={product.id}>
              <div className={`product-visual product-visual-${index % 5}`}>
                {product.image_url ? <img alt="" loading="lazy" src={product.image_url} /> : <Package aria-hidden="true" size={32} strokeWidth={1.3} />}
                <span className={`product-live ${product.is_active ? "product-live-active" : ""}`}>{product.is_active ? "Ativo" : "Inativo"}</span>
                {canEdit ? <button aria-label={`Editar ${product.name}`} className="product-edit icon-button" onClick={() => onEdit(product)} title="Editar" type="button"><Settings2 size={16} /></button> : null}
              </div>
              <div className="product-card-body">
                <div className="product-meta"><span>{product.category}</span><span>SKU {product.sku}</span></div>
                <h3>{product.name}</h3>
                {product.size || product.color ? <p className="product-variant">{[product.size, product.color].filter(Boolean).join(" · ")}</p> : null}
                <p className="product-description">{product.description || "Sem descrição cadastrada."}</p>
                <div className="product-card-footer">
                  <strong>{formatCurrency(product.price)}</strong>
                  <span className={`stock-label ${Number(product.stock_quantity) <= 0 ? "stock-empty" : ""}`}>
                    <span /> {Number(product.stock_quantity) <= 0 ? "Esgotado" : `${formatQuantity(product.stock_quantity)} un.`}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </section>
      ) : (
        <EmptyState
          action={canEdit ? <Button onClick={onCreate}><Plus size={16} /> Adicionar primeiro produto</Button> : undefined}
          copy={search || category !== "all" ? "Tente ajustar os filtros de busca." : "Cadastre produtos para começar a montar o catálogo da empresa."}
          icon={Package}
          title={search || category !== "all" ? "Nenhum produto encontrado" : "Seu catálogo começa aqui"}
        />
      )}
      <div className="list-count">Exibindo {visible.length} de {data.products.length} produtos</div>
    </div>
  );
}

function InventoryPage({
  products,
  onAdjust,
  onHistory,
  onRefresh,
}: {
  products: Product[];
  onAdjust: (product: Product) => void;
  onHistory: (product: Product) => void;
  onRefresh: () => void;
}) {
  const [search, setSearch] = useState("");
  const [availability, setAvailability] = useState("all");
  const visible = products.filter((product) => {
    const text = `${product.name} ${product.sku} ${product.category}`.toLowerCase();
    const inStock = Number(product.stock_quantity) > 0;
    return text.includes(search.toLowerCase()) && (availability === "all" || (availability === "available" ? inStock : !inStock));
  });
  const active = products.filter((product) => product.is_active);
  const inStockCount = active.filter((product) => Number(product.stock_quantity) > 0).length;
  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><p className="eyebrow">CONTROLE DE SALDOS</p><h1>Estoque</h1><p className="page-lead">Acompanhe as quantidades e registre movimentações.</p></div>
        <Button onClick={onRefresh} variant="secondary"><RefreshCw size={16} /> Atualizar saldos</Button>
      </div>
      <section className="inventory-summary">
        <div><span className="inventory-summary-icon"><Box size={19} /></span><span><small>Produtos ativos</small><strong>{active.length}</strong></span></div>
        <div><span className="inventory-summary-icon inventory-summary-mint"><ArrowDownToLine size={19} /></span><span><small>Produtos com saldo</small><strong>{inStockCount}</strong></span></div>
        <div><span className="inventory-summary-icon inventory-summary-peach"><ArrowDown size={19} /></span><span><small>Produtos sem saldo</small><strong>{active.filter((item) => Number(item.stock_quantity) <= 0).length}</strong></span></div>
      </section>
      <div className="toolbar">
        <SearchBox onChange={setSearch} placeholder="Buscar produto ou SKU" value={search} />
        <SelectField label="Disponibilidade" onChange={(event) => setAvailability(event.target.value)} value={availability}>
          <option value="all">Todos</option><option value="available">Com saldo</option><option value="empty">Sem saldo</option>
        </SelectField>
      </div>
      <section className="surface-card list-card">
        <div className="list-card-heading">
          <div><h2>Saldo por produto</h2><p>Movimentações ficam registradas no histórico de cada item.</p></div>
        </div>
        {visible.length ? (
          <div className="table-scroll">
            <table className="data-table inventory-table">
              <thead><tr><th>Produto</th><th>SKU</th><th>Categoria</th><th>Saldo atual</th><th>Disponibilidade</th><th /></tr></thead>
              <tbody>{visible.map((product) => (
                <tr key={product.id}>
                  <td><span className="table-product-name"><span className={`table-product-thumb product-visual-${products.indexOf(product) % 5}`}><Package size={16} /></span><span className="table-primary">{product.name}</span></span></td>
                  <td className="table-muted">{product.sku}</td><td className="table-muted">{product.category}</td>
                  <td><strong className="table-primary">{formatQuantity(product.stock_quantity)}</strong><span className="table-unit"> un.</span></td>
                  <td><span className={`availability-pill ${Number(product.stock_quantity) > 0 ? "availability-in" : "availability-out"}`}><span />{Number(product.stock_quantity) > 0 ? "Disponível" : "Sem saldo"}</span></td>
                  <td className="inventory-row-actions">
                    <Button className="small-action" onClick={() => onHistory(product)} variant="ghost"><Clock3 size={14} /> Histórico</Button>
                    <Button className="small-action" onClick={() => onAdjust(product)} variant="secondary"><ArrowUpToLine size={15} /> Ajustar</Button>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState copy="Experimente outra busca ou cadastre um produto." icon={Box} title="Nenhum item encontrado" />}
      </section>
      <div className="list-count">Saldo calculado a partir dos cadastros, ajustes e pedidos concluídos.</div>
    </div>
  );
}

function InventoryHistory({
  product,
  token,
  onClose,
}: {
  product: Product;
  token: string;
  onClose: () => void;
}) {
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const result = await api<InventoryMovement[]>(
          `/api/v1/admin/products/${product.id}/inventory?limit=200`,
          token,
        );
        if (active) setMovements(result);
      } catch (issue) {
        if (active) {
          setError(issue instanceof Error ? issue.message : "Não foi possível carregar o histórico.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [product.id, token]);

  const movementLabel: Record<InventoryMovement["movement_type"], string> = {
    initial: "Saldo inicial",
    adjustment: "Ajuste",
    sale: "Pedido concluído",
    purchase: "Compra recebida",
  };

  return (
    <Modal
      description={`${product.name} · saldo atual ${formatQuantity(product.stock_quantity)} unidades`}
      onClose={onClose}
      title="Histórico de estoque"
    >
      <div className="history-content">
        {loading ? (
          <div className="history-state"><span className="loading-indicator" /><span>Carregando movimentações...</span></div>
        ) : error ? (
          <div className="history-error" role="alert">{error}</div>
        ) : movements.length ? (
          <div className="movement-list">
            {movements.map((movement) => {
              const incoming = Number(movement.quantity_delta) > 0;
              return (
                <article className="movement-row" key={movement.id}>
                  <span className={`movement-sign ${incoming ? "movement-sign-in" : "movement-sign-out"}`}>
                    {incoming ? <ArrowUp size={15} /> : <ArrowDown size={15} />}
                  </span>
                  <span className="movement-copy">
                    <strong>{movementLabel[movement.movement_type]}</strong>
                    <small>{movement.note || "Sem observação"} · {formatDate(movement.created_at)}</small>
                  </span>
                  <strong className={incoming ? "movement-quantity-in" : "movement-quantity-out"}>
                    {incoming ? "+" : ""}{formatQuantity(movement.quantity_delta)}
                  </strong>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState copy="Ainda não há movimentações para este produto." icon={Clock3} title="Histórico vazio" />
        )}
        <footer className="form-footer"><Button onClick={onClose} variant="secondary">Fechar</Button></footer>
      </div>
    </Modal>
  );
}

function CustomersPage({
  customers,
  onCreate,
  onRefresh,
}: {
  customers: Customer[];
  onCreate: () => void;
  onRefresh: () => void;
}) {
  const [search, setSearch] = useState("");
  const visible = customers.filter((customer) =>
    `${customer.name} ${customer.document ?? ""} ${customer.email ?? ""} ${customer.phone ?? ""} ${customer.address ?? ""} ${customer.postal_code ?? ""}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <div className="page-content">
      <div className="page-title-row">
        <div><p className="eyebrow">RELACIONAMENTO</p><h1>Clientes</h1><p className="page-lead">Dados de contato, identificação e endereço para atender cada pessoa.</p></div>
        <Button onClick={onCreate}><Plus size={17} /> Novo cliente</Button>
      </div>
      <div className="toolbar">      <SearchBox onChange={setSearch} placeholder="Buscar nome, CPF/CNPJ, e-mail ou telefone" value={search} /><button aria-label="Atualizar clientes" className="icon-button refresh-button" onClick={onRefresh} title="Atualizar" type="button"><RefreshCw size={17} /></button></div>
      <section className="surface-card list-card">
        <div className="list-card-heading"><div><h2>Base de clientes</h2><p>{visible.length} cadastros vinculados a esta empresa</p></div></div>
        {visible.length ? (
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Cliente</th><th>CPF/CNPJ</th><th>Telefone</th><th>E-mail</th><th>Endereço</th><th>CEP</th><th>Cadastro</th></tr></thead>
              <tbody>{visible.map((customer) => (
                <tr key={customer.id}>
                  <td><span className="table-customer"><span className="customer-avatar">{customer.name.charAt(0).toUpperCase()}</span><strong className="table-primary">{customer.name}</strong></span></td>
                  <td className="table-muted">{customer.document || "—"}</td>
                  <td className="table-muted">{customer.phone || "—"}</td>
                  <td className="table-muted">{customer.email || "—"}</td>
                  <td className="table-muted">{customer.address || "—"}</td>
                  <td className="table-muted">{customer.postal_code || "—"}</td>
                  <td className="table-muted">{formatDate(customer.created_at)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyState action={<Button onClick={onCreate}><Plus size={16} /> Adicionar cliente</Button>} copy={search ? "Tente outro termo de busca." : "Cadastros da empresa aparecerão aqui."} icon={Users} title={search ? "Nenhum cliente encontrado" : "Sua base de clientes começa aqui"} />}
      </section>
      <div className="privacy-note"><span className="privacy-note-icon"><Check size={15} /></span>Os contatos são armazenados separadamente para cada empresa.</div>
    </div>
  );
}

function CustomerForm({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (draft: { name: string; phone: string; email: string; document: string; address: string; postal_code: string }) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [document, setDocument] = useState("");
  const [address, setAddress] = useState("");
  const [postalCode, setPostalCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSave({ name, phone, email, document, address, postal_code: postalCode });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível salvar o cliente.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description="Os dados de contato são usados para atender e acompanhar pedidos." onClose={onClose} title="Adicionar cliente">
      <FormShell footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Salvar cliente</Button></>} onSubmit={submit}>
        <div className="form-grid form-grid-single">
          <Field autoComplete="name" label="Nome completo" maxLength={160} onChange={(event) => setName(event.target.value)} placeholder="Nome da pessoa" required value={name} />
          <Field autoComplete="tel" label="Telefone / WhatsApp" maxLength={32} onChange={(event) => setPhone(event.target.value)} placeholder="+55 (11) 99999-9999" type="tel" value={phone} />
          <Field autoComplete="email" label="E-mail" maxLength={320} onChange={(event) => setEmail(event.target.value)} placeholder="cliente@email.com" type="email" value={email} />
          <Field autoComplete="off" label="CPF/CNPJ" maxLength={18} onChange={(event) => setDocument(event.target.value)} placeholder="000.000.000-00 ou 00.000.000/0000-00" value={document} />
          <Field autoComplete="street-address" label="Endereço" maxLength={500} onChange={(event) => setAddress(event.target.value)} placeholder="Rua, número, complemento, bairro e cidade/UF" value={address} />
          <Field autoComplete="postal-code" label="CEP" maxLength={10} onChange={(event) => setPostalCode(event.target.value)} placeholder="00000-000" value={postalCode} />
        </div>
        <FormError>{error}</FormError>
      </FormShell>
    </Modal>
  );
}

function InventoryForm({
  product,
  onClose,
  onSave,
}: {
  product: Product;
  onClose: () => void;
  onSave: (draft: { quantity_delta: string; note: string }) => Promise<void>;
}) {
  const [movement, setMovement] = useState<"in" | "out">("in");
  const [quantity, setQuantity] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const value = Number(quantity);
      await onSave({ quantity_delta: String(movement === "in" ? value : -value), note });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível ajustar o estoque.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal description={`${product.sku} · saldo atual ${formatQuantity(product.stock_quantity)} unidades`} onClose={onClose} title="Ajustar estoque">
      <FormShell footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Registrar movimentação</Button></>} onSubmit={submit}>
        <div className="movement-switch" aria-label="Tipo de ajuste">
          <button aria-pressed={movement === "in"} className={movement === "in" ? "movement-choice movement-choice-active" : "movement-choice"} onClick={() => setMovement("in")} type="button"><ArrowUp size={16} /> Entrada</button>
          <button aria-pressed={movement === "out"} className={movement === "out" ? "movement-choice movement-choice-active" : "movement-choice"} onClick={() => setMovement("out")} type="button"><ArrowDown size={16} /> Saída</button>
        </div>
        <div className="form-grid form-grid-single">
          <Field autoFocus label="Quantidade" min="0.001" onChange={(event) => setQuantity(event.target.value)} required step="0.001" type="number" value={quantity} />
          <TextAreaField label="Motivo / observação" maxLength={500} onChange={(event) => setNote(event.target.value)} placeholder="Ex.: conferência, recebimento..." rows={3} value={note} />
        </div>
        <FormError>{error}</FormError>
      </FormShell>
    </Modal>
  );
}

function OrderForm({
  data,
  onClose,
  onSave,
  posOnly = false,
}: {
  data: DataSet;
  onClose: () => void;
  posOnly?: boolean;
  onSave: (draft: {
    customer_id: string;
    source: string;
    fulfillment_method: string;
    items: { product_id: string; quantity: string }[];
  }) => Promise<void>;
}) {
  const [customerId, setCustomerId] = useState("");
  const [source, setSource] = useState("counter");
  const [fulfillment, setFulfillment] = useState("counter");
  const [lines, setLines] = useState<OrderLine[]>([{ product_id: "", quantity: "1" }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const activeProducts = data.products.filter((product) => product.is_active);
  const estimate = lines.reduce((sum, line) => {
    const product = data.products.find((item) => item.id === line.product_id);
    return sum + (product ? Number(product.price) * currencyAmount(line.quantity) : 0);
  }, 0);

  function updateLine(index: number, patch: Partial<OrderLine>) {
    setLines((current) => current.map((line, position) => position === index ? { ...line, ...patch } : line));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSave({
        customer_id: customerId,
        source,
        fulfillment_method: fulfillment,
        items: lines.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível criar o pedido.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description={posOnly ? "Crie um pedido de balcão. O pagamento deve ser confirmado fora do sistema e o estoque é baixado ao concluir o pedido." : "O sistema consulta os preços e confirma o total no momento da cotação."} onClose={onClose} title={posOnly ? "Iniciar venda no PDV" : "Novo pedido"} wide>
      {data.customers.length && activeProducts.length ? (
        <FormShell footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">{posOnly ? "Criar pedido" : "Criar orçamento"} · {formatCurrency(estimate)}</Button></>} onSubmit={submit}>
          <div className="form-grid">
            <SelectField label="Cliente" onChange={(event) => setCustomerId(event.target.value)} required value={customerId}>
              <option disabled value="">Selecione um cliente</option>{data.customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}{customer.phone ? ` · ${customer.phone}` : ""}</option>)}
            </SelectField>
            {posOnly ? <div className="field"><span>Origem do pedido</span><strong className="pos-origin">Balcão</strong></div> : (
              <SelectField label="Origem do pedido" onChange={(event) => setSource(event.target.value)} value={source}>
                <option value="counter">Balcão</option><option value="catalog">Catálogo digital</option><option value="whatsapp">WhatsApp</option>
              </SelectField>
            )}
            <SelectField className="form-span" label="Atendimento" onChange={(event) => setFulfillment(event.target.value)} value={fulfillment}>
              <option value="counter">Venda presencial</option><option value="pickup">Retirada na loja</option><option value="delivery">Entrega local</option>
            </SelectField>
          </div>
          <div className="order-lines-heading"><div><h3>Itens do pedido</h3><p>Preços e disponibilidade serão validados pelo sistema.</p></div><Button onClick={() => setLines((current) => [...current, { product_id: "", quantity: "1" }])} type="button" variant="secondary"><Plus size={15} /> Adicionar item</Button></div>
          <div className="order-line-list">
            {lines.map((line, index) => {
              const product = data.products.find((item) => item.id === line.product_id);
              return (
                <div className="order-line" key={index}>
                  <SelectField label={index === 0 ? "Produto" : `Produto ${index + 1}`} onChange={(event) => updateLine(index, { product_id: event.target.value })} required value={line.product_id}>
                    <option disabled value="">Selecione um produto</option>
                    {activeProducts.map((item) => <option disabled={lines.some((other, otherIndex) => otherIndex !== index && other.product_id === item.id)} key={item.id} value={item.id}>{item.name} · {item.sku} · {formatCurrency(item.price)}</option>)}
                  </SelectField>
                  <Field label="Quantidade" min="0.001" onChange={(event) => updateLine(index, { quantity: event.target.value })} required step="0.001" type="number" value={line.quantity} />
                  <div className="line-price"><span>Subtotal estimado</span><strong>{product ? formatCurrency(Number(product.price) * currencyAmount(line.quantity)) : "—"}</strong></div>
                  {lines.length > 1 ? <button aria-label="Remover item" className="icon-button remove-line" onClick={() => setLines((current) => current.filter((_, position) => position !== index))} type="button"><X size={16} /></button> : null}
                </div>
              );
            })}
          </div>
          <FormError>{error}</FormError>
        </FormShell>
      ) : (
        <div className="prerequisite-state">
          <span className="empty-state-icon"><ShoppingBag size={22} /></span>
          <h3>Prepare o catálogo primeiro</h3>
          <p>Para abrir um pedido, cadastre ao menos um cliente e um produto ativo.</p>
          <Button onClick={onClose} variant="secondary">Entendi</Button>
        </div>
      )}
    </Modal>
  );
}

function OrderDetail({
  order,
  customer,
  products,
  onClose,
  onTransition,
}: {
  order: Order;
  customer?: Customer;
  products: Product[];
  onClose: () => void;
  onTransition: (order: Order, next: OrderStatus) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const transitions: Partial<Record<OrderStatus, { status: OrderStatus; label: string }[]>> = {
    quote: [{ status: "pending", label: "Confirmar orçamento" }, { status: "cancelled", label: "Cancelar pedido" }],
    pending: [{ status: "separating", label: "Iniciar separação" }, { status: "cancelled", label: "Cancelar pedido" }],
    separating: [
      ...(order.fulfillment_method === "pickup" ? [{ status: "ready_for_pickup" as const, label: "Pronto para retirada" }] : []),
      ...(order.fulfillment_method === "delivery" ? [{ status: "in_transit" as const, label: "Saiu para entrega" }] : []),
      ...(order.fulfillment_method === "counter" ? [{ status: "completed" as const, label: "Concluir pedido" }] : []),
      { status: "cancelled", label: "Cancelar pedido" },
    ],
    ready_for_pickup: [{ status: "completed", label: "Confirmar retirada" }, { status: "cancelled", label: "Cancelar pedido" }],
    in_transit: [{ status: "completed", label: "Confirmar conclusão" }, { status: "cancelled", label: "Cancelar pedido" }],
  };
  const options = transitions[order.status] ?? [];
  const sourceNames = { counter: "Balcão", catalog: "Catálogo digital", whatsapp: "WhatsApp" };
  const fulfillmentNames = { counter: "Venda presencial", pickup: "Retirada", delivery: "Entrega local" };

  async function transition(next: OrderStatus) {
    setBusy(true);
    setError("");
    try {
      await onTransition(order, next);
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível atualizar o pedido.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description={`Criado em ${formatDate(order.created_at)}`} onClose={onClose} title={`Pedido #${order.id.slice(0, 8).toUpperCase()}`} wide>
      <div className="order-detail-content">
        <div className="order-detail-top">
          <div><span className="eyebrow">STATUS ATUAL</span><StatusBadge status={order.status} /></div>
          <div className="order-detail-fields">
            <span><small>Cliente</small><strong>{customer?.name ?? "Cliente"}</strong></span>
            <span><small>Origem</small><strong>{sourceNames[order.source]}</strong></span>
            <span><small>Atendimento</small><strong>{fulfillmentNames[order.fulfillment_method]}</strong></span>
          </div>
        </div>
        <div className="order-detail-items">
          <div className="order-detail-row order-detail-table-heading"><span>Produto</span><span>Qtd.</span><span>Preço unitário</span><span>Total</span></div>
          {order.items.map((item) => {
            const product = products.find((entry) => entry.id === item.product_id);
            return <div className="order-detail-row" key={item.id}><span className="order-detail-product"><span className="table-product-thumb product-visual-1"><Package size={15} /></span><span><strong>{product?.name ?? "Produto"}</strong><small>SKU {product?.sku ?? "—"}</small></span></span><span>{formatQuantity(item.quantity)}</span><span>{formatCurrency(item.unit_price)}</span><strong>{formatCurrency(item.line_total)}</strong></div>;
          })}
          <div className="order-total-row"><span>Total cotado</span><strong>{formatCurrency(order.total)}</strong></div>
        </div>
        {error ? <FormError>{error}</FormError> : null}
        {options.length ? <div className="order-actions"><Button onClick={onClose} variant="ghost">Fechar</Button>{options.map((option) => <Button className={option.status === "cancelled" ? "" : "primary-action"} key={option.status} loading={busy} onClick={() => transition(option.status)} variant={option.status === "cancelled" ? "danger" : "primary"}>{option.label}</Button>)}</div> : <div className="order-actions"><Button onClick={onClose} variant="secondary">Fechar detalhes</Button></div>}
      </div>
    </Modal>
  );
}

function ManagementAppContent() {
  const toast = useToast();
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [view, setView] = useState<View>("overview");
  const [data, setData] = useState<DataSet>(EMPTY_DATA);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [productModal, setProductModal] = useState<Product | "new" | null>(null);
  const [customerModal, setCustomerModal] = useState(false);
  const [inventoryProduct, setInventoryProduct] = useState<Product | null>(null);
  const [historyProduct, setHistoryProduct] = useState<Product | null>(null);
  const [orderModal, setOrderModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const permissions = session ? managementPermissions(session.tenant.role) : null;

  const refresh = useCallback(async (activeToken: string, role: Role) => {
    setLoading(true);
    try {
      const allowed = managementPermissions(role);
      const [products, customers, orders] = await Promise.all([
        allowed.products ? api<Product[]>("/api/v1/admin/products?limit=200", activeToken) : Promise.resolve([]),
        allowed.customers ? api<Customer[]>("/api/v1/admin/customers?limit=200", activeToken) : Promise.resolve([]),
        allowed.orders ? api<Order[]>("/api/v1/admin/orders?limit=200", activeToken) : Promise.resolve([]),
      ]);
      setData({ products, customers, orders });
    } catch (issue) {
      if (issue instanceof ApiError && issue.status === 401) {
        sessionStorage.removeItem("commercial_access_token");
        setToken(null);
        setSession(null);
        setData(EMPTY_DATA);
      }
      toast("error", issue instanceof Error ? issue.message : "Não foi possível carregar os dados.");
      throw issue;
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    const savedToken = sessionStorage.getItem("commercial_access_token");
    if (!savedToken) {
      setReady(true);
      return;
    }
    const activeToken = savedToken;
    let active = true;
    async function restore() {
      try {
        const context = await api<Omit<Session, "access_token">>("/api/v1/auth/me", activeToken);
        if (!active) return;
        const restoredSession = { ...context, access_token: activeToken };
        setToken(activeToken);
        setSession(restoredSession);
        const allowed = managementPermissions(context.tenant.role);
        const [products, customers, orders] = await Promise.all([
          allowed.products ? api<Product[]>("/api/v1/admin/products?limit=200", activeToken) : Promise.resolve([]),
          allowed.customers ? api<Customer[]>("/api/v1/admin/customers?limit=200", activeToken) : Promise.resolve([]),
          allowed.orders ? api<Order[]>("/api/v1/admin/orders?limit=200", activeToken) : Promise.resolve([]),
        ]);
        if (active) setData({ products, customers, orders });
      } catch (issue) {
        if (issue instanceof ApiError && issue.status === 401) {
          sessionStorage.removeItem("commercial_access_token");
          toast("error", "Sua sessão expirou. Entre novamente.");
        } else {
          toast(
            "error",
            issue instanceof Error
              ? issue.message
              : "Não foi possível restaurar sua sessão.",
          );
        }
      } finally {
        if (active) {
          setLoading(false);
          setReady(true);
        }
      }
    }
    setLoading(true);
    void restore();
    return () => { active = false; };
  }, [toast]);

  async function refreshCurrent() {
    if (!token || !session) return;
    try {
      await refresh(token, session.tenant.role);
    } catch {
      return;
    }
  }

  function login(nextToken: string, context: Session) {
    sessionStorage.setItem("commercial_access_token", nextToken);
    setToken(nextToken);
    setSession(context);
    setView("overview");
    setReady(true);
    void refresh(nextToken, context.tenant.role).catch(() => undefined);
  }

  function logout() {
    sessionStorage.removeItem("commercial_access_token");
    setToken(null);
    setSession(null);
    setData(EMPTY_DATA);
    setView("overview");
    toast("success", "Sessão encerrada.");
  }

  async function saveProduct(draft: ProductDraft) {
    if (!token) throw new Error("Sua sessão expirou.");
    const editing = productModal && productModal !== "new" ? productModal : null;
    const body = {
      sku: draft.sku.trim(),
      name: draft.name.trim(),
      category: draft.category.trim(),
      size: draft.size.trim() || null,
      color: draft.color.trim() || null,
      price: draft.price,
      cost_price: draft.cost_price,
      icms_rate: draft.icms_rate,
      ipi_rate: draft.ipi_rate,
      pis_rate: draft.pis_rate,
      cofins_rate: draft.cofins_rate,
      ...(editing ? {} : { stock_quantity: draft.stock_quantity }),
      description: draft.description.trim() || null,
      image_url: draft.image_url.trim() || null,
      is_active: draft.is_active,
    };
    const result = await api<Product>(
      editing ? `/api/v1/admin/products/${editing.id}` : "/api/v1/admin/products",
      token,
      { method: editing ? "PATCH" : "POST", body: JSON.stringify(body) },
    );
    await refreshCurrent();
    toast("success", editing ? "Produto atualizado." : "Produto cadastrado.");
    if (result.id) setProductModal(null);
  }

  async function saveCustomer(draft: { name: string; phone: string; email: string; document: string; address: string; postal_code: string }) {
    if (!token) throw new Error("Sua sessão expirou.");
    await api<Customer>("/api/v1/admin/customers", token, {
      method: "POST",
      body: JSON.stringify({
        name: draft.name.trim(),
        phone: draft.phone.trim() || null,
        email: draft.email.trim() || null,
        document: draft.document.trim() || null,
        address: draft.address.trim() || null,
        postal_code: draft.postal_code.trim() || null,
      }),
    });
    await refreshCurrent();
    toast("success", "Cliente cadastrado.");
  }

  async function saveInventory(draft: { quantity_delta: string; note: string }) {
    if (!token || !inventoryProduct) throw new Error("Sua sessão expirou.");
    await api(`/api/v1/admin/products/${inventoryProduct.id}/inventory`, token, {
      method: "POST",
      body: JSON.stringify({
        quantity_delta: draft.quantity_delta,
        note: draft.note.trim() || null,
      }),
    });
    await refreshCurrent();
    toast("success", "Movimentação de estoque registrada.");
  }

  async function saveOrder(draft: {
    customer_id: string;
    source: string;
    fulfillment_method: string;
    items: { product_id: string; quantity: string }[];
  }) {
    if (!token) throw new Error("Sua sessão expirou.");
    await api<Order>("/api/v1/admin/orders", token, {
      method: "POST",
      body: JSON.stringify(draft),
    });
    await refreshCurrent();
    toast("success", "Orçamento criado com sucesso.");
  }

  async function transitionOrder(order: Order, next: OrderStatus) {
    if (!token) throw new Error("Sua sessão expirou.");
    await api<Order>(`/api/v1/admin/orders/${order.id}/status`, token, {
      method: "PATCH",
      body: JSON.stringify({ status: next }),
    });
    await refreshCurrent();
    toast("success", `Pedido atualizado: ${statusLabels[next]}.`);
  }

  if (!ready || (loading && !session)) {
    return <div className="app-loading"><span className="brand-mark"><Command size={20} /></span><div className="loading-indicator" /><span>Preparando seu espaço...</span></div>;
  }
  if (!session || !token) return <LoginScreen onLogin={login} />;

  const pageInfo: Record<View, { title: string; subtitle: string }> = {
    overview: { title: "Visão geral", subtitle: "Uma visão tranquila do que acontece na sua empresa." },
    pos: { title: "PDV / Vendas", subtitle: "Registre vendas de balcão e acompanhe a conclusão de cada pedido." },
    orders: { title: "Pedidos", subtitle: "Cotações, atendimento e andamento da operação." },
    products: { title: "Produtos", subtitle: "Organize o catálogo e as informações comerciais." },
    inventory: { title: "Estoque", subtitle: "Saldos e movimentações da empresa." },
    customers: { title: "Clientes", subtitle: "Contatos cadastrados para o atendimento." },
    suppliers: { title: "Fornecedores", subtitle: "Contatos e parceiros da sua operação." },
    purchases: { title: "Compras", subtitle: "Entradas e recebimentos de mercadorias." },
    employees: { title: "Funcionários", subtitle: "Contas da equipe e permissões de acesso." },
    finance: { title: "Financeiro", subtitle: "Contas a pagar e receber." },
    whatsapp: { title: "WhatsApp", subtitle: "Atendimento conectado aos clientes, pedidos e catálogo." },
    access_logs: { title: "Auditoria de acesso", subtitle: "Histórico de atividades autenticadas." },
  };

  return (
    <div className="management-shell">
      <Sidebar
        onClose={() => setMobileNav(false)}
        onLogout={logout}
        onNavigate={setView}
        open={mobileNav}
        session={session}
        view={view}
      />
      <main className="main-panel">
        <Header
          action={view === "orders" ? <Button className="topbar-create" onClick={() => setOrderModal(true)}><Plus size={16} /> Novo pedido</Button> : undefined}
          onMenu={() => setMobileNav(true)}
          session={session}
          subtitle={pageInfo[view].subtitle}
          title={pageInfo[view].title}
        />
        {view === "overview" ? (
          <Overview
            data={data}
            loading={loading}
            onCreateOrder={() => setOrderModal(true)}
            onNavigate={setView}
            onRefresh={() => void refreshCurrent()}
            permissions={permissions!}
            session={session}
          />
        ) : null}
        {view === "orders" ? (
          <OrdersPage
            data={data}
            loading={loading}
            onCreate={() => setOrderModal(true)}
            onRefresh={() => void refreshCurrent()}
            onSelect={setSelectedOrder}
          />
        ) : null}
        {view === "pos" ? (
          <OrdersPage
            data={data}
            loading={loading}
            onCreate={() => setOrderModal(true)}
            onRefresh={() => void refreshCurrent()}
            onSelect={setSelectedOrder}
            mode="pos"
          />
        ) : null}
        {view === "whatsapp" ? (
          <WhatsAppModule
            customers={data.customers}
            orders={data.orders}
            products={data.products}
            tenantSlug={session.tenant.slug}
          />
        ) : null}
        {view === "products" ? (
          <ProductsPage
            canEdit={permissions!.editProducts}
            data={data}
            onCreate={() => setProductModal("new")}
            onEdit={setProductModal}
            onRefresh={() => void refreshCurrent()}
          />
        ) : null}
        {view === "inventory" ? (
          <InventoryPage
            onAdjust={setInventoryProduct}
            onHistory={setHistoryProduct}
            onRefresh={() => void refreshCurrent()}
            products={data.products}
          />
        ) : null}
        {view === "customers" ? (
          <CustomersPage
            customers={data.customers}
            onCreate={() => setCustomerModal(true)}
            onRefresh={() => void refreshCurrent()}
          />
        ) : null}
        {["suppliers", "purchases", "employees", "finance", "access_logs"].includes(view) ? (
          <OperationsModule
            key={view}
            onRefresh={refreshCurrent}
            products={data.products}
            token={token}
            view={view as OperationsView}
          />
        ) : null}
      </main>

      {productModal ? <ProductForm initial={productModal === "new" ? undefined : productModal} onClose={() => setProductModal(null)} onSave={saveProduct} /> : null}
      {customerModal ? <CustomerForm onClose={() => setCustomerModal(false)} onSave={saveCustomer} /> : null}
      {inventoryProduct ? <InventoryForm onClose={() => setInventoryProduct(null)} onSave={saveInventory} product={inventoryProduct} /> : null}
      {historyProduct && token ? <InventoryHistory onClose={() => setHistoryProduct(null)} product={historyProduct} token={token} /> : null}
      {orderModal ? <OrderForm data={data} onClose={() => setOrderModal(false)} onSave={saveOrder} posOnly={view === "pos"} /> : null}
      {selectedOrder ? <OrderDetail customer={data.customers.find((item) => item.id === selectedOrder.customer_id)} onClose={() => setSelectedOrder(null)} onTransition={transitionOrder} order={selectedOrder} products={data.products} /> : null}
    </div>
  );
}

export function ManagementApp() {
  return (
    <ToastProvider>
      <ManagementAppContent />
    </ToastProvider>
  );
}
