-- ============================================================
-- BLESSDATAHUB BUNDLE SEEDING SCRIPT (IDEMPOTENT)
-- Run this in your Supabase SQL Editor
-- ============================================================
-- 
-- This script populates the bundles table with static pricing
-- from Blessdatahub. Safe to run multiple times (uses UPSERT).
--
-- Networks supported:
--   - MTN (16 packages: 1GB - 50GB)
--   - TELECEL (8 packages: 5GB - 50GB)
--   - AIRTELTIGO (17 packages: 1GB - 100GB)
-- ============================================================


-- ============================================================
-- MTN BUNDLES
-- ============================================================
INSERT INTO bundles (id, network, capacity, mb, price, currency, active)
VALUES 
    (gen_random_uuid(), 'MTN', '1', '1024', 4.30, 'GHS', true),
    (gen_random_uuid(), 'MTN', '2', '2048', 8.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '3', '3072', 12.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '4', '4096', 17.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '5', '5120', 21.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '6', '6144', 26.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '7', '7168', 30.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '8', '8192', 34.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '9', '9216', 38.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '10', '10240', 42.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '15', '15360', 59.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '20', '20480', 80.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '25', '25600', 102.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '30', '30720', 117.50, 'GHS', true),
    (gen_random_uuid(), 'MTN', '40', '40960', 160.00, 'GHS', true),
    (gen_random_uuid(), 'MTN', '50', '51200', 198.00, 'GHS', true)
ON CONFLICT (network, capacity) DO UPDATE SET
    mb = EXCLUDED.mb,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    active = EXCLUDED.active,
    updated_at = NOW();

-- ============================================================
-- TELECEL BUNDLES (formerly Vodafone)
-- ============================================================
INSERT INTO bundles (id, network, capacity, mb, price, currency, active)
VALUES 
    (gen_random_uuid(), 'TELECEL', '5', '5120', 23.50, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '10', '10240', 40.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '15', '15360', 59.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '20', '20480', 79.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '25', '25600', 94.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '30', '30720', 112.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '40', '40960', 146.00, 'GHS', true),
    (gen_random_uuid(), 'TELECEL', '50', '51200', 182.00, 'GHS', true)
ON CONFLICT (network, capacity) DO UPDATE SET
    mb = EXCLUDED.mb,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    active = EXCLUDED.active,
    updated_at = NOW();

-- ============================================================
-- AIRTELTIGO BUNDLES
-- ============================================================
INSERT INTO bundles (id, network, capacity, mb, price, currency, active)
VALUES 
    (gen_random_uuid(), 'AIRTELTIGO', '1', '1024', 4.50, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '2', '2048', 8.90, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '3', '3072', 13.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '4', '4096', 17.50, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '5', '5120', 21.50, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '6', '6144', 26.50, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '7', '7168', 29.50, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '8', '8192', 34.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '9', '9216', 39.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '10', '10240', 42.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '15', '15360', 57.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '20', '20480', 84.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '25', '25600', 100.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '30', '30720', 125.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '40', '40960', 160.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '50', '51200', 200.00, 'GHS', true),
    (gen_random_uuid(), 'AIRTELTIGO', '100', '102400', 220.00, 'GHS', true)
ON CONFLICT (network, capacity) DO UPDATE SET
    mb = EXCLUDED.mb,
    price = EXCLUDED.price,
    currency = EXCLUDED.currency,
    active = EXCLUDED.active,
    updated_at = NOW();


-- ============================================================
-- VERIFICATION QUERY
-- Run this to verify the bundles were inserted correctly
-- ============================================================
SELECT 
    network, 
    COUNT(*) as bundle_count,
    MIN(price) as min_price,
    MAX(price) as max_price
FROM bundles 
WHERE active = true 
GROUP BY network
ORDER BY network;

-- Expected output:
-- network    | bundle_count | min_price | max_price
-- -----------|--------------|-----------|----------
-- AIRTELTIGO | 17           | 4.50      | 220.00
-- MTN        | 16           | 4.30      | 198.00
-- TELECEL    | 8            | 23.50     | 182.00
