"use client";

import {
  ArrowDownToLine,
  Check,
  Clock3,
  FileClock,
  Plus,
  ReceiptText,
  Truck,
  UserRoundCog,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { api } from "@/lib/api";
import { formatCurrency, formatDate, formatQuantity, roleLabels } from "@/lib/format";
import type {
  AccessLog,
  Employee,
  FinancialEntry,
  Product,
  Purchase,
  Role,
  Supplier,
} from "@/lib/types";
import {
  Button,
  Field,
  FormError,
  FormShell,
  Modal,
  SelectField,
  useToast,
} from "@/components/ui";

export type OperationsView =
  | "suppliers"
  | "purchases"
  | "employees"
  | "finance"
  | "access_logs";

type Props = {
  view: OperationsView;
  token: string;
  products: Product[];
  onRefresh: () => Promise<void>;
};

type PurchaseLine = { product_id: string; quantity: string; unit_cost: string };

const EMPTY_LINE: PurchaseLine = { product_id: "", quantity: "1", unit_cost: "" };

const roleOptions: Role[] = [
  "company_admin",
  "counter_operator",
  "inventory_manager",
  "human_support",
];

function SupplierForm({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (body: Record<string, string | null>) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [document, setDocument] = useState("");
  const [contact, setContact] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave({
        name: name.trim(),
        document: document.trim() || null,
        contact_name: contact.trim() || null,
        phone: phone.trim() || null,
        email: email.trim() || null,
      });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível cadastrar o fornecedor.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description="Cadastre os dados comerciais para organizar as entradas de compra." onClose={onClose} title="Novo fornecedor">
      <FormShell
        footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Salvar fornecedor</Button></>}
        onSubmit={submit}
      >
        <div className="form-grid form-grid-single">
          <Field autoFocus label="Razão social / nome" maxLength={160} onChange={(event) => setName(event.target.value)} required value={name} />
          <Field label="CPF / CNPJ" maxLength={32} onChange={(event) => setDocument(event.target.value)} value={document} />
          <Field label="Pessoa de contato" maxLength={160} onChange={(event) => setContact(event.target.value)} value={contact} />
          <Field label="Telefone" maxLength={32} onChange={(event) => setPhone(event.target.value)} type="tel" value={phone} />
          <Field label="E-mail" maxLength={320} onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
          <FormError>{error}</FormError>
        </div>
      </FormShell>
    </Modal>
  );
}

function EmployeeForm({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (body: Record<string, string>) => Promise<void>;
}) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("counter_operator");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave({ display_name: displayName.trim(), email: email.trim(), password, role });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível cadastrar o acesso.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description="A senha inicial deve ter pelo menos 12 caracteres. A equipe poderá entrar com este e-mail." onClose={onClose} title="Adicionar funcionário">
      <FormShell
        footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Criar acesso</Button></>}
        onSubmit={submit}
      >
        <div className="form-grid form-grid-single">
          <Field autoFocus autoComplete="name" label="Nome" maxLength={160} onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
          <Field autoComplete="email" label="E-mail de acesso" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
          <Field autoComplete="new-password" label="Senha inicial" minLength={12} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
          <SelectField label="Perfil de acesso" onChange={(event) => setRole(event.target.value as Role)} value={role}>
            {roleOptions.map((option) => <option key={option} value={option}>{roleLabels[option]}</option>)}
          </SelectField>
          <FormError>{error}</FormError>
        </div>
      </FormShell>
    </Modal>
  );
}

function PurchaseForm({
  suppliers,
  products,
  onClose,
  onSave,
}: {
  suppliers: Supplier[];
  products: Product[];
  onClose: () => void;
  onSave: (body: { supplier_id: string; items: PurchaseLine[] }) => Promise<void>;
}) {
  const [supplierId, setSupplierId] = useState("");
  const [lines, setLines] = useState<PurchaseLine[]>([{ ...EMPTY_LINE }]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const total = lines.reduce(
    (sum, line) => sum + Number(line.quantity || 0) * Number(line.unit_cost || 0),
    0,
  );

  function updateLine(index: number, patch: Partial<PurchaseLine>) {
    setLines((current) => current.map((line, position) =>
      position === index ? { ...line, ...patch } : line,
    ));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave({ supplier_id: supplierId, items: lines });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível registrar a compra.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description="A compra ficará em rascunho. O estoque e o contas a pagar só serão atualizados ao confirmar o recebimento." onClose={onClose} title="Registrar compra" wide>
      {suppliers.length && products.length ? (
        <FormShell
          footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Salvar compra · {formatCurrency(total)}</Button></>}
          onSubmit={submit}
        >
          <div className="form-grid">
            <SelectField className="form-span" label="Fornecedor" onChange={(event) => setSupplierId(event.target.value)} required value={supplierId}>
              <option disabled value="">Selecione um fornecedor</option>
              {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
            </SelectField>
          </div>
          <div className="order-lines-heading">
            <div><h3>Itens recebidos</h3><p>O custo unitário é usado no contas a pagar.</p></div>
            <Button onClick={() => setLines((current) => [...current, { ...EMPTY_LINE }])} type="button" variant="secondary"><Plus size={15} /> Adicionar item</Button>
          </div>
          <div className="order-line-list">
            {lines.map((line, index) => (
              <div className="order-line" key={index}>
                <SelectField label={index === 0 ? "Produto" : `Produto ${index + 1}`} onChange={(event) => updateLine(index, { product_id: event.target.value })} required value={line.product_id}>
                  <option disabled value="">Selecione um produto</option>
                  {products.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
                </SelectField>
                <Field label="Quantidade" min="0.001" onChange={(event) => updateLine(index, { quantity: event.target.value })} required step="0.001" type="number" value={line.quantity} />
                <Field label="Custo unitário" min="0" onChange={(event) => updateLine(index, { unit_cost: event.target.value })} required step="0.01" type="number" value={line.unit_cost} />
                {lines.length > 1 ? <button aria-label="Remover item" className="icon-button remove-line" onClick={() => setLines((current) => current.filter((_, position) => position !== index))} type="button"><X size={16} /></button> : <span />}
              </div>
            ))}
          </div>
          <FormError>{error}</FormError>
        </FormShell>
      ) : (
        <div className="prerequisite-state">
          <span className="empty-state-icon"><Truck size={22} /></span>
          <h3>Prepare os cadastros</h3>
          <p>Cadastre pelo menos um fornecedor e um produto ativo antes de registrar uma compra.</p>
          <Button onClick={onClose} variant="secondary">Entendi</Button>
        </div>
      )}
    </Modal>
  );
}

function FinanceForm({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (body: Record<string, string>) => Promise<void>;
}) {
  const [entryType, setEntryType] = useState<"payable" | "receivable">("payable");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [dueDate, setDueDate] = useState(() => {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${today.getFullYear()}-${month}-${day}`;
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await onSave({ entry_type: entryType, description: description.trim(), amount, due_date: dueDate });
      onClose();
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível salvar o lançamento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal description="Registre receitas e despesas previstas. A baixa representa somente o controle interno, não uma cobrança bancária." onClose={onClose} title="Novo lançamento">
      <FormShell
        footer={<><Button onClick={onClose} variant="ghost">Cancelar</Button><Button loading={busy} type="submit">Salvar lançamento</Button></>}
        onSubmit={submit}
      >
        <div className="form-grid form-grid-single">
          <SelectField label="Tipo" onChange={(event) => setEntryType(event.target.value as "payable" | "receivable")} value={entryType}>
            <option value="payable">Conta a pagar</option><option value="receivable">Conta a receber</option>
          </SelectField>
          <Field autoFocus label="Descrição" maxLength={240} onChange={(event) => setDescription(event.target.value)} required value={description} />
          <Field label="Valor (R$)" min="0.01" onChange={(event) => setAmount(event.target.value)} required step="0.01" type="number" value={amount} />
          <Field label="Vencimento" onChange={(event) => setDueDate(event.target.value)} required type="date" value={dueDate} />
          <FormError>{error}</FormError>
        </div>
      </FormShell>
    </Modal>
  );
}

export function OperationsModule({ view, token, products, onRefresh }: Props) {
  const toast = useToast();
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [entries, setEntries] = useState<FinancialEntry[]>([]);
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [modal, setModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (view === "suppliers") {
        setSuppliers(await api<Supplier[]>("/api/v1/admin/suppliers?limit=200", token));
      } else if (view === "purchases") {
        const [purchaseRows, supplierRows] = await Promise.all([
          api<Purchase[]>("/api/v1/admin/purchases?limit=200", token),
          api<Supplier[]>("/api/v1/admin/suppliers?limit=200", token),
        ]);
        setPurchases(purchaseRows);
        setSuppliers(supplierRows);
      } else if (view === "employees") {
        setEmployees(await api<Employee[]>("/api/v1/admin/employees", token));
      } else if (view === "finance") {
        setEntries(await api<FinancialEntry[]>("/api/v1/admin/finance?limit=200", token));
      } else {
        const [logRows, employeeRows] = await Promise.all([
          api<AccessLog[]>("/api/v1/admin/access-logs?limit=200", token),
          api<Employee[]>("/api/v1/admin/employees", token),
        ]);
        setLogs(logRows);
        setEmployees(employeeRows);
      }
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível carregar os dados deste módulo.");
    } finally {
      setLoading(false);
    }
  }, [token, view]);

  useEffect(() => {
    void load();
  }, [load]);

  const supplierById = useMemo(
    () => new Map(suppliers.map((supplier) => [supplier.id, supplier.name])),
    [suppliers],
  );
  const employeeByUserId = useMemo(
    () => new Map(employees.map((employee) => [employee.user_id, employee])),
    [employees],
  );

  async function save(path: string, body: unknown, success: string) {
    try {
      await api(path, token, { method: "POST", body: JSON.stringify(body) });
      setModal(false);
      toast("success", success);
      await load();
      await onRefresh();
    } catch (issue) {
      toast("error", issue instanceof Error ? issue.message : "Não foi possível salvar.");
      throw issue;
    }
  }

  async function update(path: string, body: unknown, success: string, id: string) {
    setBusyId(id);
    try {
      await api(path, token, { method: "PATCH", body: JSON.stringify(body) });
      toast("success", success);
      await load();
      await onRefresh();
    } catch (issue) {
      toast("error", issue instanceof Error ? issue.message : "Não foi possível atualizar.");
    } finally {
      setBusyId("");
    }
  }

  const config = {
    suppliers: { title: "Fornecedores", description: "Contatos e parceiros da sua operação.", icon: Truck, action: "Novo fornecedor" },
    purchases: { title: "Compras", description: "Registre entradas e acompanhe recebimentos.", icon: ReceiptText, action: "Registrar compra" },
    employees: { title: "Funcionários", description: "Contas da equipe e permissões de acesso.", icon: UserRoundCog, action: "Adicionar funcionário" },
    finance: { title: "Financeiro", description: "Contas a pagar e receber, com controle de vencimentos.", icon: ReceiptText, action: "Novo lançamento" },
    access_logs: { title: "Auditoria de acesso", description: "Atividades autenticadas registradas para esta empresa.", icon: FileClock, action: "" },
  }[view];
  const Icon = config.icon;

  return (
    <div className="page-content">
      <section className="page-title-row">
        <div>
          <p className="eyebrow">GESTÃO COMERCIAL</p>
          <h1>{config.title}</h1>
          <p className="page-lead">{config.description}</p>
        </div>
        {config.action ? <Button onClick={() => setModal(true)}><Plus size={16} /> {config.action}</Button> : null}
      </section>

      <section className="surface-card">
        {loading ? (
          <div className="empty-state"><span className="loading-indicator" /><h3>Carregando informações</h3></div>
        ) : error ? (
          <div className="empty-state" role="alert">
            <span className="empty-state-icon"><Icon size={22} /></span>
            <h3>Não foi possível carregar este módulo</h3><p>{error}</p>
            <Button onClick={() => void load()} variant="secondary">Tentar novamente</Button>
          </div>
        ) : view === "suppliers" ? (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Fornecedor</th><th>Contato</th><th>Telefone</th><th>E-mail</th><th>Documento</th></tr></thead>
            <tbody>{suppliers.map((supplier) => <tr key={supplier.id}>
              <td className="table-primary">{supplier.name}</td><td className="table-muted">{supplier.contact_name || "—"}</td>
              <td className="table-muted">{supplier.phone || "—"}</td><td className="table-muted">{supplier.email || "—"}</td>
              <td className="table-muted">{supplier.document || "—"}</td>
            </tr>)}</tbody>
          </table>{suppliers.length === 0 ? <Empty icon={Truck} text="Nenhum fornecedor cadastrado." /> : null}</div>
        ) : view === "purchases" ? (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Compra</th><th>Fornecedor</th><th>Itens</th><th>Total</th><th>Data</th><th>Situação</th><th>Ações</th></tr></thead>
            <tbody>{purchases.map((purchase) => <tr key={purchase.id}>
              <td className="order-reference">#{purchase.id.slice(0, 8).toUpperCase()}</td>
              <td className="table-primary">{supplierById.get(purchase.supplier_id) || "Fornecedor"}</td>
              <td>{purchase.items.reduce((sum, item) => sum + Number(item.quantity), 0)}</td>
              <td>{formatCurrency(purchase.total)}</td><td className="table-muted">{formatDate(purchase.created_at)}</td>
              <td><span className={`status-badge status-${purchase.status}`}>{purchase.status === "draft" ? "Rascunho" : purchase.status === "received" ? "Recebida" : "Cancelada"}</span></td>
              <td>{purchase.status === "draft" ? <div className="table-actions">
                <Button className="small-action" loading={busyId === purchase.id} onClick={() => void update(`/api/v1/admin/purchases/${purchase.id}/status`, { status: "received" }, "Compra recebida; estoque e contas a pagar atualizados.", purchase.id)}><Check size={14} /> Receber</Button>
                <Button className="small-action" disabled={busyId === purchase.id} onClick={() => void update(`/api/v1/admin/purchases/${purchase.id}/status`, { status: "cancelled" }, "Compra cancelada.", purchase.id)} variant="ghost"><X size={14} /> Cancelar</Button>
              </div> : "—"}</td>
            </tr>)}</tbody>
          </table>{purchases.length === 0 ? <Empty icon={ReceiptText} text="Nenhuma compra registrada." /> : null}</div>
        ) : view === "employees" ? (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Funcionário</th><th>E-mail</th><th>Perfil</th><th>Estado</th><th>Cadastro</th><th>Acesso</th></tr></thead>
            <tbody>{employees.map((employee) => <tr key={employee.id}>
              <td className="table-primary">{employee.display_name || employee.email}</td><td className="table-muted">{employee.email}</td>
              <td>{roleLabels[employee.role]}</td><td><span className={`status-badge status-${employee.is_active ? "completed" : "cancelled"}`}>{employee.is_active ? "Ativo" : "Inativo"}</span></td>
              <td className="table-muted">{formatDate(employee.created_at)}</td>
              <td>{employee.is_active ? <Button className="small-action" loading={busyId === employee.id} onClick={() => void update(`/api/v1/admin/employees/${employee.id}`, { is_active: false }, "Acesso desativado.", employee.id)} variant="ghost">Desativar</Button> : <Button className="small-action" loading={busyId === employee.id} onClick={() => void update(`/api/v1/admin/employees/${employee.id}`, { is_active: true }, "Acesso reativado.", employee.id)} variant="secondary">Reativar</Button>}</td>
            </tr>)}</tbody>
          </table></div>
        ) : view === "finance" ? (
          <>
            <div className="inventory-summary">
              <FinanceTotal title="A pagar" value={entries.filter((entry) => entry.entry_type === "payable" && entry.status === "pending").reduce((sum, entry) => sum + Number(entry.amount), 0)} tone="peach" />
              <FinanceTotal title="A receber" value={entries.filter((entry) => entry.entry_type === "receivable" && entry.status === "pending").reduce((sum, entry) => sum + Number(entry.amount), 0)} tone="mint" />
              <FinanceTotal title="Em aberto" value={entries.filter((entry) => entry.status === "pending").length} tone="lavender" count />
            </div>
            <div className="table-scroll"><table className="data-table">
              <thead><tr><th>Descrição</th><th>Tipo</th><th>Vencimento</th><th>Valor</th><th>Situação</th><th>Ação</th></tr></thead>
              <tbody>{entries.map((entry) => <tr key={entry.id}>
                <td className="table-primary">{entry.description}</td><td>{entry.entry_type === "payable" ? "A pagar" : "A receber"}</td>
                <td className="table-muted">{formatDate(`${entry.due_date}T00:00:00`)}</td><td>{formatCurrency(entry.amount)}</td>
                <td><span className={`status-badge status-${entry.status === "settled" ? "completed" : entry.status === "pending" ? "pending" : "cancelled"}`}>{entry.status === "settled" ? "Baixado" : entry.status === "pending" ? "Pendente" : "Cancelado"}</span></td>
                <td>{entry.status === "pending" ? <Button className="small-action" loading={busyId === entry.id} onClick={() => void update(`/api/v1/admin/finance/${entry.id}/settle`, {}, "Lançamento baixado.", entry.id)}><Check size={14} /> Dar baixa</Button> : entry.settled_at ? <span className="table-muted">{formatDate(entry.settled_at)}</span> : "—"}</td>
              </tr>)}</tbody>
            </table>{entries.length === 0 ? <Empty icon={ReceiptText} text="Nenhum lançamento financeiro." /> : null}</div>
          </>
        ) : (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Data e hora</th><th>Usuário</th><th>Atividade</th></tr></thead>
            <tbody>{logs.map((log) => {
              const employee = employeeByUserId.get(log.user_id);
              return <tr key={log.id}>
                <td className="table-muted">{formatDate(log.created_at)}</td>
                <td className="table-primary">{employee?.display_name || employee?.email || `${log.user_id.slice(0, 8)}…`}</td>
                <td><span className="audit-action"><FileClock size={14} /> {log.action}</span></td>
              </tr>;
            })}</tbody>
          </table>{logs.length === 0 ? <Empty icon={Clock3} text="Nenhum acesso registrado." /> : null}</div>
        )}
      </section>
      {view === "access_logs" ? <p className="privacy-note"><span className="privacy-note-icon"><FileClock size={14} /></span>Registros mostram acessos autenticados; ações de login inválidas não armazenam credenciais nem dados de senha.</p> : null}

      {modal && view === "suppliers" ? <SupplierForm onClose={() => setModal(false)} onSave={(body) => save("/api/v1/admin/suppliers", body, "Fornecedor cadastrado.")} /> : null}
      {modal && view === "employees" ? <EmployeeForm onClose={() => setModal(false)} onSave={(body) => save("/api/v1/admin/employees", body, "Acesso criado.")} /> : null}
      {modal && view === "purchases" ? <PurchaseForm onClose={() => setModal(false)} onSave={(body) => save("/api/v1/admin/purchases", body, "Compra registrada como rascunho.")} products={products.filter((product) => product.is_active)} suppliers={suppliers} /> : null}
      {modal && view === "finance" ? <FinanceForm onClose={() => setModal(false)} onSave={(body) => save("/api/v1/admin/finance", body, "Lançamento financeiro criado.")} /> : null}
    </div>
  );
}

function Empty({ icon: Icon, text }: { icon: typeof Truck; text: string }) {
  return <div className="empty-state compact-empty"><span className="empty-state-icon"><Icon size={21} /></span><p>{text}</p></div>;
}

function FinanceTotal({ title, value, tone, count = false }: { title: string; value: number; tone: string; count?: boolean }) {
  return <div><span className={`inventory-summary-icon inventory-summary-${tone}`}><ArrowDownToLine size={17} /></span><span><small>{title}</small><strong>{count ? value : formatCurrency(value)}</strong></span></div>;
}
