// Cloudflare Pages Function: POST /api/chatgpt-webhook
// Webhook endpoint for ChatGPT to add/edit website content
// ChatGPT sends structured updates via this endpoint
//
// Env vars (Cloudflare Pages -> Settings -> Environment variables):
//   SUPABASE_URL        e.g. https://YOUR_PROJECT_REF.supabase.co
//   SUPABASE_ANON_KEY    the project's public anon key
//   CHATGPT_API_KEY      your OpenAI API key (for verification)
//   WEBHOOK_SECRET       shared secret between ChatGPT and this endpoint

export interface Env {
  SUPABASE_URL: string;
  SUPABASE_ANON_KEY: string;
  CHATGPT_API_KEY: string;
  WEBHOOK_SECRET: string;
}

export interface ChatGPTUpdate {
  action: "add_product" | "edit_product" | "add_service" | "edit_service" | "update_store_section";
  data: Record<string, any>;
  timestamp: string;
}

async function verifyWebhookSignature(
  request: Request,
  secret: string
): Promise<boolean> {
  const signature = request.headers.get("x-webhook-signature");
  if (!signature) return false;

  const body = await request.clone().text();
  const encoder = new TextEncoder();
  const data = encoder.encode(body + secret);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

  return signature === hashHex;
}

async function addProduct(
  env: Env,
  data: Record<string, any>
): Promise<{ success: boolean; id?: string; error?: string }> {
  const {
    title,
    description,
    price,
    quantity,
    image_url,
    condition,
    ebay_listing_id,
  } = data;

  if (!title || !price) {
    return { success: false, error: "title and price are required" };
  }

  const product = {
    sku: `MANUAL_${Date.now()}`,
    title,
    description: description || "",
    price: parseFloat(price),
    quantity: parseInt(quantity || "1"),
    image_url: image_url || null,
    condition: condition || "Good Used Condition (GUC)",
    status: "active",
    ebay_listing_id: ebay_listing_id || null,
    source: "chatgpt_webhook",
  };

  const restUrl = `${env.SUPABASE_URL}/rest/v1/products`;

  const res = await fetch(restUrl, {
    method: "POST",
    headers: {
      apikey: env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${env.SUPABASE_ANON_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(product),
  });

  if (!res.ok) {
    const error = await res.text();
    return { success: false, error: `Supabase error: ${error}` };
  }

  const [created] = await res.json();
  return { success: true, id: created.sku };
}

async function editProduct(
  env: Env,
  data: Record<string, any>
): Promise<{ success: boolean; error?: string }> {
  const { sku, ...updates } = data;

  if (!sku) {
    return { success: false, error: "sku is required for edits" };
  }

  const restUrl = `${env.SUPABASE_URL}/rest/v1/products?sku=eq.${sku}`;

  const res = await fetch(restUrl, {
    method: "PATCH",
    headers: {
      apikey: env.SUPABASE_ANON_KEY,
      Authorization: `Bearer ${env.SUPABASE_ANON_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(updates),
  });

  if (!res.ok) {
    const error = await res.text();
    return { success: false, error: `Supabase error: ${error}` };
  }

  return { success: true };
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  try {
    // Verify webhook signature
    const isValid = await verifyWebhookSignature(
      context.request,
      context.env.WEBHOOK_SECRET
    );
    if (!isValid) {
      return new Response(JSON.stringify({ error: "Invalid signature" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    const update: ChatGPTUpdate = await context.request.json();

    let result;
    switch (update.action) {
      case "add_product":
        result = await addProduct(context.env, update.data);
        break;
      case "edit_product":
        result = await editProduct(context.env, update.data);
        break;
      default:
        return new Response(
          JSON.stringify({ error: "Unknown action" }),
          { status: 400, headers: { "Content-Type": "application/json" } }
        );
    }

    return new Response(JSON.stringify(result), {
      status: result.success ? 200 : 400,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (e) {
    const error = e instanceof Error ? e.message : "Unknown error";
    return new Response(JSON.stringify({ error }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
};
