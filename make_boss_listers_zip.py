"""Run this to generate boss-listers-ai.zip in the pipeline folder."""
import zipfile, os, pathlib

ROOT = pathlib.Path(__file__).parent
OUT  = ROOT / "boss-listers-ai.zip"

files = {
    "MASTER_PROMPT.txt": (ROOT / "BOSS_LISTERS_AI_PROMPT.md").read_text(encoding="utf-8"),
    "src/types.ts": """\
export type PlatformName = "ebay" | "poshmark" | "mercari" | "depop" | "grailed" | "etsy" | "shopify" | "tiktok";

export type ProductCondition =
  | "New With Tags (NWT)"
  | "New Without Tags (NWOT)"
  | "Like New / Excellent Used Condition (EUC)"
  | "Good Used Condition (GUC)"
  | "Fair Condition";

export interface SyncRecord {
  listed: boolean;
  listedPrice?: number;
  listedUrl?: string;
  syncedAt?: string;
  syncStatus: "idle" | "loading" | "success" | "error";
  syncLog?: string;
}

export interface ResellerProduct {
  id: string;
  title: string;
  brand: string;
  size: string;
  condition: ProductCondition;
  buyCost: number;
  suggestedPrice: number;
  sku: string;
  upc?: string;
  imageUrl: string;
  description: string;
  platforms: Record<PlatformName, SyncRecord>;
  createdAt: string;
}
""",
    "src/data.ts": """\
import { ResellerProduct, PlatformName } from "./types";

export function calculateProductProfit(price: number, buyCost: number, platform: PlatformName) {
  let platformFee = 0;
  if (platform === "ebay")          platformFee = price * 0.1325 + 0.30;
  else if (platform === "poshmark") platformFee = price < 15 ? 2.95 : price * 0.20;
  else if (platform === "mercari")  platformFee = price * 0.10 + (price * 0.029 + 0.50);
  else if (platform === "depop")    platformFee = price * 0.10 + (price * 0.033 + 0.45);
  else if (platform === "grailed")  platformFee = price * 0.09 + (price * 0.0349 + 0.49);
  else if (platform === "etsy")     platformFee = price * 0.065 + (price * 0.03 + 0.25);
  else if (platform === "shopify")  platformFee = price * 0.029 + 0.30;
  else if (platform === "tiktok")   platformFee = price * 0.08 + 0.30;

  const roundedFee    = Math.round(platformFee * 100) / 100;
  const netProfit     = price - buyCost - roundedFee;
  const marginPercent = price > 0 ? Math.round((netProfit / price) * 100) : 0;
  return { platformFee: roundedFee, netProfit: Math.round(netProfit * 100) / 100, marginPercent };
}
""",
    "README.txt": """\
BOSS LISTERS AI — Starter Kit
==============================
1. Open MASTER_PROMPT.txt
2. Copy ALL of it
3. Paste into Google AI Studio (aistudio.google.com) with Gemini 1.5 Pro
4. Also upload src/types.ts and src/data.ts as context files
5. Gemini will output the full working codebase

After Gemini generates the files:
  npm install
  npm run dev
""",
}

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for name, content in files.items():
        zf.writestr(f"boss-listers-ai/{name}", content)

print(f"Created: {OUT}  ({OUT.stat().st_size // 1024} KB)")
