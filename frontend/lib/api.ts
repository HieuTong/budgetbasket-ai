const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type BasketItem = { name: string; qty: number; unit_price: number };
export type OptimizeResponse = {
  items: BasketItem[];
  total_cost: number;
  total_utility: number;
};

export async function optimizeBasket(userId: number, budget: number): Promise<OptimizeResponse> {
  const res = await fetch(`${API_BASE}/api/basket/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, budget }),
  });
  if (!res.ok) throw new Error(`Optimize failed: ${res.status}`);
  return res.json();
}

export async function askAgent(userId: number, message: string): Promise<{ reply: string }> {
  const res = await fetch(`${API_BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, message }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}
