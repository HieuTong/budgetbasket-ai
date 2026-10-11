const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type BasketItem = {
  name: string;
  qty: number;
  unit_price: number;
};

export type OptimizeResponse = {
  items: BasketItem[];
  total_cost: number;
  total_utility: number;
};

export type Product = {
  id: number;
  name: string;
  brand: string;
  category: string;
  sub_category?: string;
  product_group?: string;
  package_size?: string;
  unit_price: number;
};

export type ProductListResponse = {
  items: Product[];
};

export type PriceProbability = {
  INCREASE: number;
  STABLE: number;
  DECREASE: number;
};

export type DecisionResponse = {
  product_id: number;
  product_name: string;
  decision: string;
  confidence: number;
  reason: string;
  price_probability?: PriceProbability;
};

export type Substitute = {
  product_id: number;
  product_name: string;
  brand: string;
  category: string;
  unit_price: number;
  similarity: number;
  savings: number;
  savings_percent: number;
  preference: number;
  score: number;
  reason: string;
};

export type SubstitutesResponse = {
  product_id: number;
  product_name: string;
  brand: string;
  category: string;
  base_price: number;
  results: Substitute[];
};

export async function optimizeBasket(
  userId: number,
  budget: number,
): Promise<OptimizeResponse> {
  const res = await fetch(`${API_BASE}/api/basket/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      budget,
    }),
  });

  if (!res.ok) {
    throw new Error(`Optimize failed: ${res.status}`);
  }

  return res.json();
}

export async function getProducts(
  category?: string,
  search?: string,
  limit = 8,
): Promise<ProductListResponse> {
  const params = new URLSearchParams();

  if (category) {
    params.set("category", category);
  }

  if (search?.trim()) {
    params.set("search", search.trim());
  }

  params.set("limit", String(limit));

  const query = params.toString();

  const res = await fetch(
    `${API_BASE}/api/catalog/products${query ? `?${query}` : ""}`,
  );

  if (!res.ok) {
    throw new Error(`Products failed: ${res.status}`);
  }

  const data = await res.json();

  return {
    items: data.items.map(
      (item: {
        product_id: number;
        name: string;
        brand: string;
        category: string;
        sub_category?: string;
        product_group?: string;
        package_size?: string;
        price: number;
      }) => ({
        id: item.product_id,
        name: item.name,
        brand: item.brand,
        category: item.category,
        sub_category: item.sub_category,
        product_group: item.product_group,
        package_size: item.package_size,
        unit_price: item.price,
      }),
    ),
  };
}

export async function getDecision(
  productId: number,
  userId?: number,
): Promise<DecisionResponse> {
  const params = new URLSearchParams();

  if (userId !== undefined) {
    params.set("user_id", String(userId));
  }

  const query = params.toString();

  const res = await fetch(
    `${API_BASE}/api/decision/${productId}${query ? `?${query}` : ""}`,
  );

  if (!res.ok) {
    throw new Error(`Decision failed: ${res.status}`);
  }

  return res.json();
}

export async function getSubstitutes(
  productId: number,
  userId?: number,
  topK = 5,
): Promise<SubstitutesResponse> {
  const params = new URLSearchParams({
    top_k: String(topK),
  });

  if (userId !== undefined) {
    params.set("user_id", String(userId));
  }

  const res = await fetch(
    `${API_BASE}/api/similarity/${productId}/substitutes?${params}`,
  );

  if (!res.ok) {
    throw new Error(`Substitutes failed: ${res.status}`);
  }

  return res.json();
}

export async function askAgent(
  userId: number,
  message: string,
): Promise<{ reply: string }> {
  const res = await fetch(`${API_BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      message,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat failed: ${res.status}`);
  }

  return res.json();
}
