// The basket the user is editing. All functions here are pure: they take the current lines
// and return new ones without changing the old array. That keeps React state updates
// predictable and makes each rule easy to unit test later.
import type { OptimizeResponse } from "@/lib/api";

export type BasketLine = {
  productId: number;
  name: string;
  unitPrice: number;
  qty: number;
  // Where the line came from, so the receipt can show what the user changed.
  origin: "built" | "added" | "swapped";
  swappedFrom?: string;
};

export type NewProduct = {
  productId: number;
  name: string;
  unitPrice: number;
};

export const MAX_QTY = 20;

export function fromOptimized(result: OptimizeResponse): BasketLine[] {
  return result.items.map((item) => ({
    productId: item.product_id,
    name: item.name,
    unitPrice: item.unit_price,
    qty: item.qty,
    origin: "built",
  }));
}

export function addProduct(lines: BasketLine[], product: NewProduct): BasketLine[] {
  const existing = lines.find((line) => line.productId === product.productId);
  if (existing) {
    return changeQty(lines, product.productId, 1);
  }
  return [...lines, { ...product, qty: 1, origin: "added" }];
}

export function changeQty(lines: BasketLine[], productId: number, delta: number): BasketLine[] {
  return lines
    .map((line) =>
      line.productId === productId
        ? { ...line, qty: Math.min(MAX_QTY, line.qty + delta) }
        : line,
    )
    .filter((line) => line.qty > 0);
}

export function removeLine(lines: BasketLine[], productId: number): BasketLine[] {
  return lines.filter((line) => line.productId !== productId);
}

// Replace one product with another, keeping the quantity. If the replacement is already in
// the basket, the quantities are merged instead of creating a duplicate line.
export function swapLine(
  lines: BasketLine[],
  oldProductId: number,
  replacement: NewProduct,
): BasketLine[] {
  const old = lines.find((line) => line.productId === oldProductId);
  if (!old) return addProduct(lines, replacement);

  const alreadyThere = lines.some((line) => line.productId === replacement.productId);
  if (alreadyThere) {
    return changeQty(removeLine(lines, oldProductId), replacement.productId, old.qty);
  }

  return lines.map((line) =>
    line.productId === oldProductId
      ? { ...replacement, qty: old.qty, origin: "swapped", swappedFrom: old.name }
      : line,
  );
}

// Sum in cents to avoid floating-point drift (0.1 + 0.2 !== 0.3).
export function basketTotal(lines: BasketLine[]): number {
  const cents = lines.reduce((sum, line) => sum + Math.round(line.unitPrice * 100) * line.qty, 0);
  return cents / 100;
}

export function quantityOf(lines: BasketLine[] | null, productId: number): number {
  return lines?.find((line) => line.productId === productId)?.qty ?? 0;
}

// ---- Saving the basket in this browser, so a refresh doesn't lose the user's edits ----

type Saved = { lines: BasketLine[]; builtFor: number | null; edited: boolean };

const storageKey = (userId: number) => `bb-basket-v1-${userId}`;

export function loadBasket(userId: number): Saved | null {
  try {
    const raw = window.localStorage.getItem(storageKey(userId));
    if (!raw) return null;
    const saved = JSON.parse(raw) as Saved;
    return Array.isArray(saved.lines) ? saved : null;
  } catch {
    return null; // private browsing, full storage or corrupted data: start fresh
  }
}

export function saveBasket(userId: number, saved: Saved | null): void {
  try {
    if (saved === null) {
      window.localStorage.removeItem(storageKey(userId));
    } else {
      window.localStorage.setItem(storageKey(userId), JSON.stringify(saved));
    }
  } catch {
    // Saving is a convenience; the basket still works without it.
  }
}
