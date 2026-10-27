"use client";

import {
  ArrowUpRight,
  Command,
  LoaderCircle,
  PackageOpen,
  Search,
  ShoppingBasket,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { api, queryString } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { PublicProduct, PublicTenant } from "@/lib/types";
import { Button, Field, FormError, FormShell, Modal, SelectField } from "@/components/ui";

type CheckoutReceipt = { order_id: string; status: string; total: string };

function CheckoutForm({
  tenantSlug,
  products,
  selectedIds,
  onClose,
  onComplete,
}: {
  tenantSlug: string;
  products: PublicProduct[];
  selectedIds: string[];
  onClose: () => void;
  onComplete: (receipt: CheckoutReceipt) => void;
}) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [fulfillment, setFulfillment] = useState<"pickup" | "delivery">("pickup");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const receipt = await api<CheckoutReceipt>(
        `/api/v1/public/${encodeURIComponent(tenantSlug)}/orders`,
        undefined,
        {
          method: "POST",
          body: JSON.stringify({
            customer_name: name.trim(),
            phone: phone.trim() || null,
            email: email.trim() || null,
            fulfillment_method: fulfillment,
            items: selectedIds.map((product_id) => ({ product_id, quantity: "1" })),
          }),
        },
      );
      onComplete(receipt);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível enviar o pedido.");
    } finally {
      setBusy(false);
    }
  }

  const total = products
    .filter((product) => selectedIds.includes(product.id))
    .reduce((sum, product) => sum + Number(product.price), 0);

  return (
    <Modal description="Você enviará um pedido para confirmação da loja. Este fluxo não cobra nem processa pagamentos." onClose={onClose} title="Conferir pedido">
      <FormShell
        footer={<><Button onClick={onClose} variant="ghost">Voltar</Button><Button loading={busy} type="submit">Enviar pedido · {formatCurrency(total)}</Button></>}
        onSubmit={submit}
      >
        <div className="form-grid form-grid-single">
          <div className="checkout-items">
            {products.filter((product) => selectedIds.includes(product.id)).map((product) => (
              <div key={product.id}><span>{product.name}{product.size || product.color ? ` · ${[product.size, product.color].filter(Boolean).join(" / ")}` : ""}</span><strong>{formatCurrency(product.price)}</strong></div>
            ))}
          </div>
          <Field autoComplete="name" autoFocus label="Nome" maxLength={160} onChange={(event) => setName(event.target.value)} required value={name} />
          <Field autoComplete="tel" label="Telefone / WhatsApp" maxLength={32} onChange={(event) => setPhone(event.target.value)} placeholder="Informe telefone ou e-mail" type="tel" value={phone} />
          <Field autoComplete="email" label="E-mail (opcional)" onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
          <SelectField label="Forma de recebimento" onChange={(event) => setFulfillment(event.target.value as "pickup" | "delivery")} value={fulfillment}>
            <option value="pickup">Retirada na loja</option><option value="delivery">Entrega local</option>
          </SelectField>
          {!phone.trim() && !email.trim() ? <p className="checkout-contact-hint">Informe telefone ou e-mail para a equipe entrar em contato.</p> : null}
          <FormError>{error}</FormError>
          <p className="checkout-disclaimer">Pedido sem cobrança. A loja confirmará disponibilidade, entrega e pagamento diretamente com você.</p>
        </div>
      </FormShell>
    </Modal>
  );
}

export function Storefront({ tenantSlug }: { tenantSlug: string }) {
  const [products, setProducts] = useState<PublicProduct[]>([]);
  const [tenant, setTenant] = useState<PublicTenant | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("Todas");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [basket, setBasket] = useState<string[]>([]);
  const [showAvailable, setShowAvailable] = useState(false);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [receipt, setReceipt] = useState<CheckoutReceipt | null>(null);

  const loadCatalog = useCallback(async (search: string) => {
    setLoading(true);
    setError("");
    try {
      const base = `/api/v1/public/${encodeURIComponent(tenantSlug)}`;
      const [profile, result] = await Promise.all([
        api<PublicTenant>(base),
        api<PublicProduct[]>(`${base}/catalog${queryString({ q: search || undefined, limit: 100 })}`),
      ]);
      setTenant(profile);
      setProducts(result);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Não foi possível carregar o catálogo.");
    } finally {
      setLoading(false);
    }
  }, [tenantSlug]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadCatalog(query), 250);
    return () => window.clearTimeout(timer);
  }, [loadCatalog, query]);

  const categories = useMemo(
    () => ["Todas", ...new Set(products.map((product) => product.category))],
    [products],
  );
  const visible = products.filter((product) => {
    const matchingCategory = category === "Todas" || product.category === category;
    return matchingCategory && (!showAvailable || product.in_stock);
  });
  const storeName = tenant?.display_name || tenantSlug
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");

  function toggleProduct(productId: string) {
    setBasket((current) =>
      current.includes(productId)
        ? current.filter((id) => id !== productId)
        : [...current, productId],
    );
  }

  return (
    <main className="storefront">
      <header className="store-header">
        <a className="store-brand" href={`/catalog/${tenantSlug}`}>
          <span className="brand-mark"><Command size={19} strokeWidth={2.2} /></span>
          <span>{storeName}<small>CATÁLOGO DIGITAL</small></span>
        </a>
        <div className="store-header-right">
          <span className="store-open-indicator"><span /> Catálogo atualizado</span>
          <span className="store-basket"><ShoppingBasket size={17} /> {basket.length || "Sua seleção"}</span>
        </div>
      </header>

      <section className="store-hero">
        <div className="store-hero-copy">
          <span className="store-eyebrow"><Sparkles size={14} /> BEM-VINDA(O) À {storeName.toUpperCase()}</span>
          <h1>O que você<br /><span>precisa hoje?</span></h1>
          <p>Encontre seus produtos com praticidade. Consulte os itens e a disponibilidade desta loja.</p>
          <a className="store-hero-link" href="#produtos">Explorar produtos <ArrowUpRight size={17} /></a>
        </div>
        <div className="store-hero-art" aria-hidden="true">
          <div className="store-orbit store-orbit-one" />
          <div className="store-orbit store-orbit-two" />
          <div className="store-bottle bottle-back"><span /></div>
          <div className="store-bottle bottle-front"><span /></div>
          <div className="store-art-spark">✦</div>
          <div className="store-art-dot" />
        </div>
      </section>

      <section className="store-catalog" id="produtos">
        <div className="store-section-head">
          <div>
            <span className="store-eyebrow">FEITO PARA A SUA ROTINA</span>
            <h2>Nosso catálogo</h2>
            <p>Explore produtos e confira valores e disponibilidade.</p>
          </div>
          <label className="store-search">
            <Search size={17} />
            <input onChange={(event) => setQuery(event.target.value)} placeholder="Buscar um produto..." value={query} />
          </label>
        </div>
        <div className="store-filter-row">
          <div className="store-categories" aria-label="Categorias">
            {categories.map((item) => (
              <button
                aria-pressed={category === item}
                className={category === item ? "store-category store-category-active" : "store-category"}
                key={item}
                onClick={() => setCategory(item)}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>
          <label className="store-availability">
            <input checked={showAvailable} onChange={(event) => setShowAvailable(event.target.checked)} type="checkbox" />
            Mostrar disponíveis
          </label>
        </div>

        {error ? (
          <div className="store-state store-error-state" role="alert">
            <PackageOpen size={24} /><strong>Não foi possível exibir este catálogo</strong><p>{error}</p>
            <button onClick={() => void loadCatalog(query)} type="button">Tentar novamente</button>
          </div>
        ) : loading ? (
          <div className="store-state"><LoaderCircle className="spin" size={25} /><span>Carregando produtos...</span></div>
        ) : visible.length ? (
          <div className="store-product-grid">
            {visible.map((product, index) => {
              const selected = basket.includes(product.id);
              return (
                <article className="store-product-card" key={product.id}>
                  <div className={`store-product-image store-image-${index % 5}`}>
                    {product.image_url ? <img alt="" loading="lazy" src={product.image_url} /> : <PackageOpen size={38} strokeWidth={1.35} />}
                    <span className={`store-stock ${product.in_stock ? "store-stock-in" : "store-stock-out"}`}>
                      <span /> {product.in_stock ? "Disponível" : "Indisponível"}
                    </span>
                    <button
                      aria-label={selected ? `Remover ${product.name} da seleção` : product.in_stock ? `Selecionar ${product.name}` : `${product.name} indisponível`}
                      aria-pressed={selected}
                      className={`store-add ${selected ? "store-add-selected" : ""}`}
                      onClick={() => toggleProduct(product.id)}
                      disabled={!product.in_stock && !selected}
                      title={selected ? "Remover da seleção" : product.in_stock ? "Adicionar à seleção" : "Produto indisponível"}
                      type="button"
                    >
                      {selected ? "✓" : "+"}
                    </button>
                  </div>
                  <div className="store-product-copy">
                    <div className="store-product-labels"><span>{product.category}</span><span>SKU {product.sku}</span></div>
                    <h3>{product.name}</h3>
                    {product.size || product.color ? <span className="store-variant">{[product.size, product.color].filter(Boolean).join(" · ")}</span> : null}
                    <p>{product.description || "Um produto selecionado para sua rotina."}</p>
                    <div className="store-product-footer"><strong>{formatCurrency(product.price)}</strong><span>valor informado pela loja</span></div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="store-state store-empty-state">
            <PackageOpen size={25} /><strong>Nenhum produto por aqui</strong><p>Tente buscar com outros termos ou confira outra categoria.</p>
          </div>
        )}
        {basket.length ? (
          <div className="store-selection-note" role="status">
            <span><ShoppingBasket size={17} /> {basket.length} {basket.length === 1 ? "produto selecionado" : "produtos selecionados"}</span>
            <p>O pedido será enviado para confirmação. Nenhum pagamento será processado neste fluxo.</p>
            <div className="store-selection-actions">
              <button onClick={() => setBasket([])} type="button">Limpar</button>
              <Button onClick={() => setCheckoutOpen(true)} type="button">Continuar pedido</Button>
            </div>
          </div>
        ) : null}
        {receipt ? (
          <div className="store-order-success" role="status">
            <strong>Pedido enviado para a loja</strong>
            <p>Referência #{receipt.order_id.slice(0, 8).toUpperCase()} · {formatCurrency(receipt.total)}. A equipe confirmará os próximos passos.</p>
            <span>Este pedido não gerou cobrança ou pagamento.</span>
          </div>
        ) : null}
      </section>

      <footer className="store-footer">
        <span className="store-footer-brand"><span className="brand-mark"><Command size={16} /></span>{storeName}</span>
        <span>Preços e disponibilidade sujeitos a confirmação pela equipe da loja.</span>
        <a href="#produtos">Voltar ao catálogo ↑</a>
      </footer>
      {checkoutOpen ? (
        <CheckoutForm
          onClose={() => setCheckoutOpen(false)}
          onComplete={(newReceipt) => {
            setReceipt(newReceipt);
            setCheckoutOpen(false);
            setBasket([]);
          }}
          products={products}
          selectedIds={basket}
          tenantSlug={tenantSlug}
        />
      ) : null}
    </main>
  );
}
