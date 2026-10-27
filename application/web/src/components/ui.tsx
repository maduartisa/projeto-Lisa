"use client";

import {
  AlertCircle,
  Check,
  ChevronDown,
  LoaderCircle,
  Search,
  X,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type FormEvent,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

type ToastMessage = { id: number; kind: "success" | "error"; text: string };
type ToastContextValue = (kind: ToastMessage["kind"], text: string) => void;
const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ToastMessage[]>([]);
  const toast = useCallback((kind: ToastMessage["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setMessages((current) => [...current, { id, kind, text }]);
    window.setTimeout(
      () => setMessages((current) => current.filter((message) => message.id !== id)),
      5000,
    );
  }, []);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {messages.map((message) => (
          <div
            className={`toast toast-${message.kind}`}
            key={message.id}
            role={message.kind === "error" ? "alert" : "status"}
          >
            {message.kind === "success" ? <Check size={17} /> : <AlertCircle size={17} />}
            <span>{message.text}</span>
            <button
              aria-label="Fechar notificação"
              className="icon-button toast-close"
              onClick={() =>
                setMessages((current) =>
                  current.filter((item) => item.id !== message.id),
                )
              }
              type="button"
            >
              <X size={15} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const toast = useContext(ToastContext);
  if (!toast) {
    throw new Error("useToast precisa ser usado dentro de ToastProvider.");
  }
  return toast;
}

export function Button({
  children,
  variant = "primary",
  className = "",
  loading = false,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
}) {
  return (
    <button
      className={`button button-${variant} ${className}`}
      disabled={props.disabled || loading}
      {...props}
    >
      {loading ? <LoaderCircle className="spin" size={17} /> : null}
      {children}
    </button>
  );
}

export function Modal({
  title,
  description,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      role="presentation"
    >
      <section
        aria-labelledby="modal-title"
        aria-modal="true"
        className={`modal ${wide ? "modal-wide" : ""}`}
        role="dialog"
      >
        <header className="modal-header">
          <div>
            <h2 id="modal-title">{title}</h2>
            {description ? <p>{description}</p> : null}
          </div>
          <button
            aria-label="Fechar janela"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <X size={19} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

export function Field({
  label,
  hint,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...props} />
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function SelectField({
  label,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <span className="select-wrap">
        <select {...props}>{children}</select>
        <ChevronDown aria-hidden="true" size={16} />
      </span>
    </label>
  );
}

export function TextAreaField({
  label,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea {...props} />
    </label>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder = "Buscar...",
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="search-box">
      <Search aria-hidden="true" size={17} />
      <input
        aria-label={placeholder}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        value={value}
      />
      {value ? (
        <button
          aria-label="Limpar busca"
          className="icon-button"
          onClick={() => onChange("")}
          type="button"
        >
          <X size={15} />
        </button>
      ) : null}
    </label>
  );
}

export function FormError({ children }: { children: ReactNode }) {
  return children ? (
    <p className="form-error" role="alert">
      <AlertCircle size={16} />
      {children}
    </p>
  ) : null;
}

export function FormShell({
  onSubmit,
  children,
  footer,
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
  footer: ReactNode;
}) {
  return (
    <form className="modal-form" onSubmit={onSubmit}>
      <div className="form-content">{children}</div>
      <footer className="form-footer">{footer}</footer>
    </form>
  );
}
