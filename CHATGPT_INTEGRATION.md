# ChatGPT → Website Integration

ChatGPT can now add and edit products on your website directly via webhook.

## Setup

### 1. Set Cloudflare Environment Variables

Go to **Cloudflare Dashboard → Pages → jardins-outpost.pages.dev → Settings → Environment Variables**

Add:
```
SUPABASE_URL = https://irslzufsqjveyibkfjtz.supabase.co
SUPABASE_ANON_KEY = sb_publishable_HV03fWT-xFr4mB1x3AGlcg_a3JbBtwA
CHATGPT_API_KEY = (your OpenAI API key)
WEBHOOK_SECRET = (generate: openssl rand -hex 32)
```

Generate a webhook secret:
```bash
# On Mac/Linux:
openssl rand -hex 32

# On Windows (PowerShell):
[Convert]::ToHexString((1..16 | ForEach-Object {[byte](Get-Random -Max 256)}))
```

### 2. Add ChatGPT Custom Action

In **ChatGPT → Settings → My GPTs → Actions**

Create a new action with this schema:

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Empire OS Store API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://jardins-outpost.pages.dev/api"
    }
  ],
  "paths": {
    "/chatgpt-webhook": {
      "post": {
        "operationId": "updateStore",
        "summary": "Add or edit products on the store",
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "action": {
                    "type": "string",
                    "enum": ["add_product", "edit_product"],
                    "description": "Action to perform"
                  },
                  "data": {
                    "type": "object",
                    "properties": {
                      "title": {
                        "type": "string",
                        "description": "Product title"
                      },
                      "description": {
                        "type": "string",
                        "description": "Product description"
                      },
                      "price": {
                        "type": "number",
                        "description": "Product price"
                      },
                      "quantity": {
                        "type": "integer",
                        "description": "Quantity available"
                      },
                      "image_url": {
                        "type": "string",
                        "description": "URL to product image"
                      },
                      "condition": {
                        "type": "string",
                        "description": "Product condition"
                      },
                      "sku": {
                        "type": "string",
                        "description": "SKU (required for edits)"
                      }
                    },
                    "required": ["title", "price"]
                  },
                  "timestamp": {
                    "type": "string",
                    "format": "date-time"
                  }
                },
                "required": ["action", "data"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "success": {
                      "type": "boolean"
                    },
                    "id": {
                      "type": "string"
                    },
                    "error": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 3. Test It

Tell ChatGPT:
> "Add a product to my store: Red Vintage Jacket, $45, Good Condition, 3 in stock"

ChatGPT will call your webhook and the product appears on your website instantly.

## Examples

**Add product:**
```
"Add to my store: Nike Air Max 90, $89.99, Like New, 2 in stock, image: https://example.com/nike.jpg"
```

**Edit product:**
```
"Update the Red Jacket price to $39.99"
```

**Result:**
- ✅ Product appears in "Shop The Inventory" section
- ✅ Website updates in real-time
- ✅ Boss Listers shows it immediately
- ✅ Syncs to Supabase

## How It Works

```
ChatGPT
  ↓ (webhook POST)
Cloudflare Function (/api/chatgpt-webhook)
  ↓ (verify signature)
Supabase (products table)
  ↓ (realtime broadcast)
Website + Boss Listers (instant update)
```

## Security

- Webhook signature verification (SHA-256)
- SUPABASE_ANON_KEY has RLS: public SELECT only
- Products can only be written via authenticated webhook
- All requests logged in Supabase

---

**Ready to use.** ChatGPT can now manage your store.
