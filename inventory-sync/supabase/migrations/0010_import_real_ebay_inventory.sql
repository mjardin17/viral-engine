-- Real, verified inventory pulled live from eBay's Browse API
-- (seller: mjardin17) via a 18-term category sweep. Source = 'ebay',
-- status = 'active' since these are confirmed live listings right now.
-- Idempotent: safe to re-run, upserts on sku (= eBay itemId).
--
-- Pre-existing production bug found and fixed here, unrelated to this
-- import: `anon` had NO SELECT grant on public.products at all (only
-- REFERENCES/TRIGGER/TRUNCATE), despite the products_public_read RLS
-- policy (published = true) assuming public read access. The live
-- storefront's anon-key reads have been failing with 401 in production.
-- This restores exactly what that policy already assumes — additive only,
-- does not touch RLS policies, tenant_id, or any other grant.
grant select on public.products to anon;

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198079646764|0', '2007 Score #341 Adrian Peterson Atomic Minnesota Vikings RC', 12.99, 1, 'https://i.ebayimg.com/images/g/ocwAAeSw-3lpg8hT/s-l225.jpg', 'Ungraded', 'active', 'ebay', 'v1|198079646764|0', 'Trading Card Singles', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198086068925|0', '2007 Bowman Chrome  - Adrian Peterson Rookie Card (HOF) “AD”', 19.99, 1, 'https://i.ebayimg.com/images/g/NxAAAeSwUnlphyVD/s-l225.jpg', 'Ungraded', 'active', 'ebay', 'v1|198086068925|0', 'Trading Card Singles', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198086072303|0', '1986 Topps Set Break #389 Bruce Smith Rookie Card!  NR-MINT+!! HOF!!!  BV $50+', 11.99, 1, 'https://i.ebayimg.com/images/g/-yYAAeSwOkpphyYq/s-l225.jpg', 'Ungraded', 'active', 'ebay', 'v1|198086072303|0', 'Trading Card Singles', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198561820911|0', '🔥 Pokemon TCG 🔥 Dusknoir 071/185 🔥 Trick or Trade 2023 Halloween Stamp ✈️🚀', 1.99, 1, 'https://i.ebayimg.com/images/g/xrMAAeSwUcpqejNk/s-l225.jpg', 'Ungraded', 'active', 'ebay', 'v1|198561820911|0', 'CCG Individual Cards', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198561837567|0', 'Pokémon Lost Origins Reverse Holo Card Barbaracle', 1.99, 1, 'https://i.ebayimg.com/images/g/YYwAAeSwtAZqejSq/s-l225.jpg', 'Ungraded', 'active', 'ebay', 'v1|198561837567|0', 'CCG Individual Cards', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198102907114|0', 'Pokemon Lot Of Three! 2  9 Inch Plush Plushes & One 4 Inch Picku NEW', 19.99, 1, 'https://i.ebayimg.com/images/g/Up8AAeSw2bppjshy/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198102907114|0', 'Plush Items', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198094966456|0', 'Transformers Age Of The Primes Excellion', 19.99, 1, 'https://i.ebayimg.com/images/g/EhoAAeSwyqhpio29/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198094966456|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198174122842|0', 'Hasbro Transformer The Thirteen MICRONUS PRIME! Action Figure New Sealed', 22.99, 1, 'https://i.ebayimg.com/images/g/L0kAAeSwVRppsUah/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198174122842|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197715478430|0', 'Transformers Studio Series 112 Optimus Prime Action Figure', 18.99, 1, 'https://i.ebayimg.com/images/g/XksAAeSwhDxpmi4l/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197715478430|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198165171673|0', 'Transformers Evolution G2 Universe Lasercycle Exclusive New Sealed Hasbro', 11.96, 1, 'https://i.ebayimg.com/images/g/7tUAAeSw4JZprRqX/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198165171673|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198173447530|0', 'Hasbro Transformers Age of the Primes Venin Figure New', 22.99, 1, 'https://i.ebayimg.com/images/g/UJ8AAeSw5GFpsR06/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198173447530|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198239965925|0', 'HASBRO TRANSFORMERS STUDIO SERIES 2026 DELUXE ORION PAX OPTIMUS PRIME ONE FIGURE', 25.99, 1, 'https://i.ebayimg.com/images/g/McAAAeSwg0Bpyrl0/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198239965925|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198440889298|0', 'Transformers CYBERWORLD Optimus Prime Cyber Changers Action Figure!', 16.99, 1, 'https://i.ebayimg.com/images/g/jHkAAeSwJ9NpsUGi/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198440889298|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198089305614|0', '5 Transformers Rise of the BeastsBattle Silverfang OPTIMUS PRIMAL RHINOX AIRAZOR', 14.99, 1, 'https://i.ebayimg.com/images/g/RFEAAeSwpvJpri31/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198089305614|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197969018934|0', 'Transformers Legacy Evolution Deluxe Class Autobot Medix  Same Day Shipping.', 15.99, 1, 'https://i.ebayimg.com/images/g/WhUAAeSwm5xpSS66/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197969018934|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197619555075|0', '2 DinoTech Warriors Transforming Robot Dinosaur Action Figure by Crypto Sphere', 14.99, 1, 'https://i.ebayimg.com/images/g/sZoAAeSwUaRon1Eq/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197619555075|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198092807677|0', 'Captain America Marvel Avengers Mech Strike Monster Hunters Action Figure NEW', 6.99, 1, 'https://i.ebayimg.com/images/g/16EAAeSw6lNpiqLi/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198092807677|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198092857643|0', 'Disney Pixar Lightyear Lot Of 3 New In Box Age 4+ XL-07 XL-01 Zyclops & Pods', 11.99, 1, 'https://i.ebayimg.com/images/g/iWsAAeSw84Jpiqdg/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198092857643|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197978306897|0', 'BENDY AND THE INK MACHINE VINYL 2.4 CHARLEY BARLEY EDGAR 3 PACK JAKKS New In Box', 17.99, 1, 'https://i.ebayimg.com/images/g/98EAAeSw~xtpTjcf/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197978306897|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198173430986|0', 'Super Saiyan 2 SS2 Goku 6.5" Dragon Stars Series Bandai Dragon Ball Super GT Z', 15.99, 1, 'https://i.ebayimg.com/images/g/XnsAAeSwQvppsRwL/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198173430986|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198101749115|0', 'THE MANDALORIAN with Dark Saber Star Wars Epic Hero Collection 4" Action Figure', 4.99, 1, 'https://i.ebayimg.com/images/g/aj8AAeSwpZRpjoOM/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198101749115|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198280095535|0', 'How to Train Your Dragon Berk Book of Dragons Series 2 Sealed Lot Of 5 | Sealed', 14.99, 1, 'https://i.ebayimg.com/images/g/~fEAAeSwf5Np3ceD/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198280095535|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198094953402|0', 'STAR WARS Darth Vader, Luke skywalker And The Mandalorian  4-Inch Action Figure', 18.99, 1, 'https://i.ebayimg.com/images/g/VykAAeSwVjJpi6De/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198094953402|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198051616406|0', '2 Bluey Cars Sets Including  Muffin Pizza Mobile,Bluey Within  Mini 4 WD', 15.99, 1, 'https://i.ebayimg.com/images/g/OmUAAeSwl2NpdNsN/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198051616406|0', 'Action Figures', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198518026874|0', 'Kokie Shade Stay Lip Stain Serenade Smudge Proof Satin Finish~ Lot Of 2', 12.99, 1, 'https://i.ebayimg.com/images/g/6JkAAeSwgvZqYcQE/s-l225.jpg', 'New with box', 'active', 'ebay', 'v1|198518026874|0', 'Lip Stain', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198518023821|0', '3 Ioni Plum Lip Pencil Liner Creamy Matte Finish DT2422 (Lot of 3) Long Lasting', 16.99, 1, 'https://i.ebayimg.com/images/g/-XQAAeSwwvJqcNXM/s-l225.jpg', 'New with box', 'active', 'ebay', 'v1|198518023821|0', 'Lip Liner', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198518011330|0', 'Kokie Shade Stay Lip Stain Wildflower lot of 4 Smudge-Proof', 15.99, 1, 'https://i.ebayimg.com/images/g/ixMAAeSwEbBqYcKZ/s-l225.jpg', 'New with box', 'active', 'ebay', 'v1|198518011330|0', 'Lip Stain', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198375885887|0', 'Bazic Beauty 55 Assorted Makeup Sponges Value Pack Latex Free Blender New Lot 3', 17.99, 1, 'https://i.ebayimg.com/images/g/qDIAAeSwo41qEh7q/s-l225.jpg', 'New with box', 'active', 'ebay', 'v1|198375885887|0', 'Sponges, Applicators & Cotton', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198279152843|0', 'Harry Potter profusion Griffin door 2 piece lip oil set', 12.99, 1, 'https://i.ebayimg.com/images/g/xWUAAeSwEaNp3UJx/s-l225.jpg', 'New with box', 'active', 'ebay', 'v1|198279152843|0', 'Lip Gloss', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198373741068|0', '3 Orchid Hydrating Jelly Cleanser,Hydrates & Nourishes Skin 175ml.each', 14.99, 1, 'https://i.ebayimg.com/images/g/TIoAAeSwCbZqENt-/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198373741068|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198180850837|0', '2 Revive RX Skin Barrier Support Wipes Hydrating Niacinamide & Exfoliating Anit', 11.99, 1, 'https://i.ebayimg.com/images/g/69kAAeSww8Fps38x/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198180850837|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198555961733|0', 'PRO SILK Body Lotion 5pc Set 5 Scents 24HR Hydrating Non-Greasy 12 fl oz', 17.99, 1, 'https://i.ebayimg.com/images/g/2eEAAeSwPZVqdugp/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198555961733|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198279082469|0', 'Tecnu Original  Outdoor Skin Cleanser 12-Ounce Bottle', 12.99, 1, 'https://i.ebayimg.com/images/g/94cAAeSwBxxp3Tl1/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198279082469|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198444304154|0', 'Orchid Glowing Body Skin Care Set: Body Lotion + Body Serum + Jelly Cleanser', 19.00, 1, 'https://i.ebayimg.com/images/g/jjIAAeSwQJtqODL7/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198444304154|0', 'Sets & Kits', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198051585039|0', 'Lot of 3 Dermasil Cocoa Butter Moisturizing Body Lotion, 8 oz.', 12.99, 1, 'https://i.ebayimg.com/images/g/Gm0AAeSwzXFpdNW-/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198051585039|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198046900421|0', 'Dermasil Daily Face Cream And Night Cream 2 Fl Oz Each NEW!', 9.99, 1, 'https://i.ebayimg.com/images/g/XpQAAeSwwwFpcnSg/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198046900421|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197722589341|0', 'Dermasil Labs Facial Cleanser Acne Skin Salicylic Glycolic 5oz 2 pack', 14.99, 1, 'https://i.ebayimg.com/images/g/7kgAAeSwzVFo056H/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197722589341|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198348078926|0', 'Happy Skin Berry Glowy and Sheer Melon Body and Face Serum 3.38oz 2 Count', 9.99, 1, 'https://i.ebayimg.com/images/g/imkAAeSwFG1qAiaO/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198348078926|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198039733906|0', 'XTRACARE Active Hands Hand Cream For Extremely Dry Skin And Crack Hands Set of 3', 16.99, 1, 'https://i.ebayimg.com/images/g/VjQAAeSwkKlpbq01/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198039733906|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198127441420|0', 'b•pure Glow Up Facial Cleanser W/ Avocado Extract Ceramides 4 FL OZ 120mL X 2', 12.99, 1, 'https://i.ebayimg.com/images/g/0pIAAeSwx4BpmowS/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198127441420|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198301329027|0', '3 Spathecary Body Butter Yuzu 2 Citrus 1Sweat Melon Black Pearl Moisturizer 5 oz', 17.99, 1, 'https://i.ebayimg.com/images/g/35sAAeSwx-Bp5lzZ/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198301329027|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198046905308|0', '2 PK Dermasil Exfoliating Facial Scrub Vitamin C & Niacinamide 5 fl oz', 15.99, 1, 'https://i.ebayimg.com/images/g/~S4AAeSwDNdpcnWY/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198046905308|0', 'Exfoliators & Scrubs', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198386566509|0', 'Brazilian Orchid Sandalwood Body Butter 4 Pack Spa Luxury Viral NEW', 19.99, 1, 'https://i.ebayimg.com/images/g/cK4AAeSwjPRqGLxW/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198386566509|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198387292638|0', '(4)Global Beauty Care Hyaluronic Acid Exfoliating Body Scrub, 6 Oz', 12.99, 1, 'https://i.ebayimg.com/images/g/rDsAAeSwhw1ph04e/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198387292638|0', 'Exfoliators & Scrubs', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197876905728|0', '6 Dermasil Labs Oatmeal Milk Toner 4oz Oatmeal & Snow Mushroom', 19.99, 1, 'https://i.ebayimg.com/images/g/1aMAAeSwsqJosaJM/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197876905728|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198262781186|0', 'Disney Alice In Wonderland Lot Lip glosses balms, Bath Salts, Body Scrub, Lot 16', 19.99, 1, 'https://i.ebayimg.com/images/g/X5wAAeSwP-Rp1SaY/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198262781186|0', 'Lip Balm & Treatments', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198047121202|0', '4 Palmer''s Cocoa Butter Formula Heal Softener  & 3 Coconut Hydrate Lotions 1.7oz', 17.99, 1, 'https://i.ebayimg.com/images/g/JtwAAeSwtLtpxZl-/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198047121202|0', 'Moisturizers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198387285968|0', 'XtraCare Micellar Cleansing Water Lot Of Four', 19.99, 1, 'https://i.ebayimg.com/images/g/xC8AAeSwqUtp48Hd/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198387285968|0', 'Cleansers & Toners', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197319978174|0', 'Size 1.5Yb - Nike Jordan 4 Retro Lemon Venom Pink', 14.99, 1, 'https://i.ebayimg.com/images/g/6K8AAeSwGJ5pa3VD/s-l225.jpg', 'Pre-owned - Good', 'active', 'ebay', 'v1|197319978174|0', 'Unisex Kids'' Shoes', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198037122260|0', 'Nike SuperRep Cycle 2 Next Nature Low Spray Paint Womens 7.5', 19.99, 1, 'https://i.ebayimg.com/images/g/jtUAAeSwa3VpbPB9/s-l225.jpg', 'New without box', 'active', 'ebay', 'v1|198037122260|0', 'Athletic Shoes', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198106366434|0', 'Littlest Pet Shop Surprise Series 4 Lot of 3 Figures', 9.99, 1, 'https://i.ebayimg.com/images/g/bdYAAeSwjQxpkFkF/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198106366434|0', 'Littlest Pet Shop', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198051614690|0', 'WWE Intercontinental Championship Title Belt Replica Mattel Kids Toy Plastic NEW', 19.99, 1, 'https://i.ebayimg.com/images/g/jcsAAeSwanppdNm0/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198051614690|0', 'Wrestling', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198090129487|0', 'Fuggler Teenage Mutant Ninja Turtles Donatello + Leonardo Plush Soft Toy, NIB', 19.99, 1, 'https://i.ebayimg.com/images/g/-FUAAeSwOI5piTqC/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198090129487|0', 'Other Stuffed Animals', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198052024944|0', 'Peanuts 5" Diecast Blue Pick UP Truck Pull Back Action Snoopy New with Tag 1/32', 9.99, 1, 'https://i.ebayimg.com/images/g/c4cAAeSwumNpdSBp/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198052024944|0', 'Play Sets', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198104046566|0', '3 Fast & Furious Mustang GT, Dom’s Dodge Charger Dom’s SS 1:32 Scale Die-Cast', 22.99, 1, 'https://i.ebayimg.com/images/g/ckQAAeSwAIZpj3Fc/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198104046566|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198257926065|0', 'Hot Wheels 1:64 Fast & Furious 5 Pack Cars Set 2025', 7.99, 1, 'https://i.ebayimg.com/images/g/PZIAAeSwNOtp0reK/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198257926065|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198348476309|0', 'Minecraft Plush Lot 5 NWT Ender Dragon Fox Wolf Ghast & Sunglasses Mattel Mojang', 19.99, 1, 'https://i.ebayimg.com/images/g/44cAAeSwQdhqA9f0/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198348476309|0', 'Other Stuffed Animals', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198350925477|0', 'Lot Of 9 Small Gabby''s Dollhouse Netflix Plush Dolls', 17.99, 1, 'https://i.ebayimg.com/images/g/t7gAAeSwU9BqA9NT/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198350925477|0', 'Other Stuffed Animals', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198261785125|0', 'Hot Wheels - Mystery Lot of 15 Brand New Cars and Trucks from 1990s to Present', 29.99, 1, 'https://i.ebayimg.com/images/g/p5UAAeSwOchp1Lf6/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198261785125|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198561189663|0', 'Fisher-Price Little People Collector USA Soccer Figures Set', 9.99, 1, 'https://i.ebayimg.com/images/g/BbAAAeSw3Bxqed5O/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198561189663|0', 'Little People (1997-Now)', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|197941138173|0', '2 Squishmallows Squish-A-Long Hello Kitty Storage Clip and 6 Mystery Mini Squish', 14.99, 1, 'https://i.ebayimg.com/images/g/T24AAeSwVxJpjv89/s-l225.jpg', 'New', 'active', 'ebay', 'v1|197941138173|0', 'Other Stuffed Animals', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198086050427|0', 'HOT WHEELS PULL BACK SPEEDERS ALPHA PURSUIT POLICE CRUISER 1:43', 12.99, 1, 'https://i.ebayimg.com/images/g/WxwAAeSwerZpb1JK/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198086050427|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198090848586|0', 'Peanuts 5" Diecast Pink Bus  Pull Back Action Snoopy New with Tag 1/32', 14.99, 1, 'https://i.ebayimg.com/images/g/aLkAAeSwJm5piYx3/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198090848586|0', 'Play Sets', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198090997661|0', 'HOT WHEELS 2025 MONSTER TRUCKS - TOTALED YELLOW INCLUDES CHRUSHABLE CAR !', 9.99, 1, 'https://i.ebayimg.com/images/g/~3MAAeSwUUNpiaKo/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198090997661|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198215417514|0', 'Hot Squishy Jumbo Tiger Super Slow Rising Stress Relief Toy Small Gift For Kids', 9.99, 1, 'https://i.ebayimg.com/images/g/XUAAAeSw~NppwBxm/s-l225.jpg', 'New without box', 'active', 'ebay', 'v1|198215417514|0', 'Squeezable Stress Relievers', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198261793574|0', 'Hot Wheels - Mystery Lot of 25 Brand New Cars and Trucks from 1990s to Present', 37.99, 1, 'https://i.ebayimg.com/images/g/534AAeSwnlJp1LkS/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198261793574|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198375869512|0', 'Marvel ty Stuffed Beanie Balls Plush Collectible Lot of 6 ', 17.99, 1, 'https://i.ebayimg.com/images/g/ZUgAAeSw0lVqEhu~/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198375869512|0', 'Other Stuffed Animals', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198018063631|0', 'HOT WHEELS MONSTER TRUCKS Twin Mill & Night Shifter Glow In The Dark 1:64 New', 19.99, 1, 'https://i.ebayimg.com/images/g/4FcAAeSwGL5ph0-m/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198018063631|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

insert into public.products (sku, title, price, quantity, image_url, condition, status, source, ebay_listing_id, ebay_category_id, synced_at)
values ('v1|198126621020|0', 'Jada Toys Hollywood Rides: Teenage Mutant Ninja Turtles PARTY WAGON [83]', 14.99, 1, 'https://i.ebayimg.com/images/g/yoAAAeSwtchpmiFd/s-l225.jpg', 'New', 'active', 'ebay', 'v1|198126621020|0', 'Contemporary Manufacture', now())
on conflict (sku) do update set
  title = excluded.title,
  price = excluded.price,
  image_url = excluded.image_url,
  condition = excluded.condition,
  status = excluded.status,
  synced_at = excluded.synced_at,
  updated_at = now();

