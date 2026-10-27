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
import { useCallback, useEffect, useMemo, useState } from "react";

import { api, queryString } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import type { PublicProduct, PublicTenant } from "@/lib/types";

export function Storefront({ tenantSlug }: { tenantSlug: string }) {
  const [products, setProducts] = useState<PublicProduct[]>([]);
  const [tenant, setTenant] = useState<PublicTenant | null>(null);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("Todas");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [basket, setBasket] = useState<string[]>([]);
  const [showAvailable, setShowAvailable] = useState(false);

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
                      aria-label={selected ? `Remover ${product.name} da seleção` : `Selecionar ${product.name}`}
                      aria-pressed={selected}
                      className={`store-add ${selected ? "store-add-selected" : ""}`}
                      onClick={() => toggleProduct(product.id)}
                      title={selected ? "Remover da seleção" : "Adicionar à seleção"}
                      type="button"
                    >
                      {selected ? "✓" : "+"}
                    </button>
                  </div>
                  <div className="store-product-copy">
                    <div className="store-product-labels"><span>{product.category}</span><span>SKU {product.sku}</span></div>
                    <h3>{product.name}</h3>
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
            <p>Esta seleção é apenas para consulta. Para solicitar um orçamento, converse diretamente com a equipe da loja.</p>
            <button onClick={() => setBasket([])} type="button">Limpar seleção</button>
          </div>
        ) : null}
      </section>

      <footer className="store-footer">
        <span className="store-footer-brand"><span className="brand-mark"><Command size={16} /></span>{storeName}</span>
        <span>Preços e disponibilidade sujeitos a confirmação pela equipe da loja.</span>
        <a href="#produtos">Voltar ao catálogo ↑</a>
      </footer>
    </main>
  );
}
