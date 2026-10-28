export type Role =
  | "company_admin"
  | "counter_operator"
  | "inventory_manager"
  | "human_support";

export type OrderStatus =
  | "quote"
  | "pending"
  | "separating"
  | "ready_for_pickup"
  | "in_transit"
  | "completed"
  | "cancelled";

export type Product = {
  id: string;
  sku: string;
  name: string;
  category: string;
  size: string | null;
  color: string | null;
  description: string | null;
  price: string;
  cost_price: string | null;
  icms_rate: string | null;
  ipi_rate: string | null;
  pis_rate: string | null;
  cofins_rate: string | null;
  stock_quantity: string;
  image_url: string | null;
  is_active: boolean;
  created_at: string;
};

export type Customer = {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  document: string | null;
  address: string | null;
  postal_code: string | null;
  created_at: string;
};

export type OrderItem = {
  id: string;
  product_id: string;
  quantity: string;
  unit_price: string;
  line_total: string;
};

export type InventoryMovement = {
  id: string;
  product_id: string;
  quantity_delta: string;
  movement_type: "initial" | "adjustment" | "sale" | "purchase";
  reference_id: string | null;
  note: string | null;
  created_at: string;
};

export type Order = {
  id: string;
  customer_id: string;
  status: OrderStatus;
  source: "counter" | "catalog" | "whatsapp";
  fulfillment_method: "counter" | "pickup" | "delivery";
  total: string;
  created_at: string;
  items: OrderItem[];
};

export type Session = {
  access_token: string;
  user: { id: string; email: string };
  tenant: {
    id: string;
    slug: string;
    display_name: string;
    status: "active" | "suspended";
    role: Role;
    created_at: string;
  };
};

export type PublicProduct = {
  id: string;
  sku: string;
  name: string;
  category: string;
  size: string | null;
  color: string | null;
  description: string | null;
  price: string;
  in_stock: boolean;
  image_url: string | null;
};

export type PublicTenant = {
  slug: string;
  display_name: string;
};

export type Employee = {
  id: string;
  user_id: string;
  email: string;
  display_name: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
};

export type Supplier = {
  id: string;
  name: string;
  document: string | null;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  created_at: string;
};

export type Purchase = {
  id: string;
  supplier_id: string;
  status: "draft" | "received" | "cancelled";
  total: string;
  created_at: string;
  items: {
    id: string;
    product_id: string;
    quantity: string;
    unit_cost: string;
    line_total: string;
  }[];
};

export type FinancialEntry = {
  id: string;
  entry_type: "payable" | "receivable";
  description: string;
  amount: string;
  due_date: string;
  status: "pending" | "settled" | "cancelled";
  settled_at: string | null;
  created_at: string;
};

export type AccessLog = {
  id: string;
  user_id: string;
  action: string;
  created_at: string;
};
