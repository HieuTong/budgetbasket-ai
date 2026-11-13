const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

// Every request gets a time limit, so a stuck backend can't leave the UI waiting forever.
const DEFAULT_TIMEOUT_MS = 20_000;
// The assistant may call several tools and retry the model, so it gets longer.
const CHAT_TIMEOUT_MS = 60_000;
// Temporary: building a basket takes about 80 s on the free hosting plan (measured).
// Lower this again once the optimiser is faster.
const BASKET_TIMEOUT_MS = 90_000;

export class TimeoutError extends Error {
  constructor(message = "The request took too long.") {
    super(message);
    this.name = "TimeoutError";
  }
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new TimeoutError();
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Authentication
//
// The server decides who you are from a signed token, never from an id the page sends.
// Visitors are signed into the shared demo account automatically.
//
// The token is kept in memory only (not localStorage), so a malicious script on the page
// cannot read it from storage. A page refresh simply fetches a new one.
// ---------------------------------------------------------------------------

// The first request may have to wait for the free hosting plan to wake the server.
const AUTH_TIMEOUT_MS = 60_000;

let accessToken: string | null = null;
// Shared by every request that needs a token at the same moment, so a page that fires
// five requests on load performs one login, not five.
let tokenRequest: Promise<string> | null = null;

async function requestDemoToken(): Promise<string> {
  const res = await fetchWithTimeout(
    `${API_BASE}/api/auth/demo`,
    { method: "POST" },
    AUTH_TIMEOUT_MS,
  );

  if (!res.ok) {
    throw new Error(`Sign-in failed: ${res.status}`);
  }

  const data = await res.json();
  return data.access_token as string;
}

async function getToken(): Promise<string> {
  if (accessToken) {
    return accessToken;
  }

  if (!tokenRequest) {
    tokenRequest = requestDemoToken()
      .then((token) => {
        accessToken = token;
        return token;
      })
      .finally(() => {
        tokenRequest = null;
      });
  }

  return tokenRequest;
}

// fetchWithTimeout plus the login token. If the server rejects the token (it expired),
// sign in again and retry once. Only once: a second 401 is a real error, not an expiry.
async function authFetch(
  url: string,
  init: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  const send = async () => {
    const token = await getToken();
    return fetchWithTimeout(
      url,
      { ...init, headers: { ...init.headers, Authorization: `Bearer ${token}` } },
      timeoutMs,
    );
  };

  const res = await send();

  if (res.status !== 401) {
    return res;
  }

  accessToken = null;
  return send();
}

export type BasketItem = {
  product_id: number;
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

// True if the backend answers its health check within a few seconds.
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/health`, {}, 5_000);
    return res.ok;
  } catch {
    return false;
  }
}

// `userId` is no longer sent anywhere in this file: the server reads the user from the
// token. The parameter stays for now so the components that call these functions do not
// change in this step; they still use it as the key for the basket saved in the browser.
export async function optimizeBasket(
  userId: number,
  budget: number,
): Promise<OptimizeResponse> {
  const res = await authFetch(`${API_BASE}/api/basket/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      budget,
    }),
  }, BASKET_TIMEOUT_MS);

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

  const res = await fetchWithTimeout(
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
  // Signed in, so the advice is personalised to the token's user.
  const res = await authFetch(`${API_BASE}/api/decision/${productId}`);

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

  const res = await authFetch(
    `${API_BASE}/api/similarity/${productId}/substitutes?${params}`,
  );

  if (!res.ok) {
    throw new Error(`Substitutes failed: ${res.status}`);
  }

  return res.json();
}

export type ChatTurn = {
  role: "user" | "assistant";
  text: string;
};

export type ChatStep = {
  tool: string;
  label: string;
  ok: boolean;
};

// A basket the assistant built in its reply. Offered to the user, never applied by itself.
export type ChatBasket = {
  budget: number | null;
  items: BasketItem[];
  total_cost: number;
};

export type ChatResponse = {
  reply: string;
  steps: ChatStep[];
  // Required, not optional: then TypeScript rejects any code that builds a chat response
  // and forgets the basket, which is exactly how the "Use this basket" button went missing.
  basket: ChatBasket | null;
};

export async function askAgent(
  userId: number,
  message: string,
  history: ChatTurn[] = [],
): Promise<ChatResponse> {
  const res = await authFetch(
    `${API_BASE}/api/chat/`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        history,
      }),
    },
    CHAT_TIMEOUT_MS,
  );

  if (!res.ok) {
    throw new Error(`Chat failed: ${res.status}`);
  }

  const data = await res.json();

  return {
    reply: data.reply,
    steps: data.steps ?? [],
    basket: data.basket ?? null,
  };
}
