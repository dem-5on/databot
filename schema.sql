-- ============================================================
-- DATABOT COMPLETE DATABASE SCHEMA
-- Run this in your Supabase SQL Editor
-- ============================================================
-- 
-- This script creates all tables, relations, indexes, and
-- RPC functions for the DataBot application.
--
-- Tables:
--   1. base_users      - Core user table (shared identity)
--   2. telegram_users  - Telegram-specific user data
--   3. whatsapp_users  - WhatsApp-specific user data
--   4. wallets         - User wallet balances
--   5. bundles         - Data bundle products
--   6. orders          - Bundle purchase orders
--   7. transactions    - Deposit/withdrawal transactions
--   8. referrals       - Referral tracking
-- ============================================================


-- ============================================================
-- 1. BASE_USERS TABLE
-- Core user identity (supports multi-platform users)
-- ============================================================
CREATE TABLE IF NOT EXISTS base_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    phone TEXT,  -- Legacy field, may be deprecated
    referral_code TEXT UNIQUE,  -- User's unique referral code
    referred_by UUID REFERENCES base_users(id) ON DELETE SET NULL,  -- Who referred this user
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_base_users_phone ON base_users(phone);
CREATE INDEX IF NOT EXISTS idx_base_users_referral_code ON base_users(referral_code);
CREATE INDEX IF NOT EXISTS idx_base_users_referred_by ON base_users(referred_by);
CREATE INDEX IF NOT EXISTS idx_base_users_created_at ON base_users(created_at);


-- ============================================================
-- 2. TELEGRAM_USERS TABLE
-- Platform-specific data for Telegram users
-- ============================================================
CREATE TABLE IF NOT EXISTS telegram_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_users(id) ON DELETE CASCADE,
    telegram_id TEXT NOT NULL UNIQUE,
    name TEXT,
    phone TEXT,
    provider TEXT,  -- Mobile money provider preference
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_telegram_users_telegram_id ON telegram_users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_telegram_users_user_id ON telegram_users(user_id);


-- ============================================================
-- 3. WHATSAPP_USERS TABLE
-- Platform-specific data for WhatsApp users
-- ============================================================
CREATE TABLE IF NOT EXISTS whatsapp_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_users(id) ON DELETE CASCADE,
    phone TEXT NOT NULL UNIQUE,  -- E.164 format (e.g., "233XXXXXXXXX")
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_whatsapp_users_phone ON whatsapp_users(phone);
CREATE INDEX IF NOT EXISTS idx_whatsapp_users_user_id ON whatsapp_users(user_id);


-- ============================================================
-- 4. WALLETS TABLE
-- User wallet balances
-- ============================================================
CREATE TABLE IF NOT EXISTS wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES base_users(id) ON DELETE CASCADE,
    balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_wallets_user_id ON wallets(user_id);


-- ============================================================
-- 5. BUNDLES TABLE
-- Data bundle products (MTN, TELECEL, AIRTELTIGO)
-- ============================================================
CREATE TABLE IF NOT EXISTS bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    network TEXT NOT NULL,     -- MTN, TELECEL, AIRTELTIGO
    capacity TEXT NOT NULL,    -- Human-readable (e.g., "1", "5", "10")
    mb TEXT NOT NULL,          -- Size in MB (e.g., "1024", "5120")
    price DECIMAL(10, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GHS',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one bundle per network + capacity
    UNIQUE(network, capacity)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bundles_network ON bundles(network);
CREATE INDEX IF NOT EXISTS idx_bundles_active ON bundles(active);
CREATE INDEX IF NOT EXISTS idx_bundles_network_active ON bundles(network, active);


-- ============================================================
-- 6. ORDERS TABLE
-- Bundle purchase orders
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_users(id) ON DELETE CASCADE,
    bundle_id UUID NOT NULL REFERENCES bundles(id) ON DELETE RESTRICT,
    phone TEXT NOT NULL,  -- Recipient phone number
    price DECIMAL(10, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed, cancelled
    vendor_reference TEXT,
    vendor_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_bundle_id ON orders(bundle_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_vendor_reference ON orders(vendor_reference);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);


-- ============================================================
-- 7. TRANSACTIONS TABLE
-- Deposit/withdrawal/purchase transactions
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES base_users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,  -- deposit, withdrawal, purchase
    amount DECIMAL(12, 2) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'GHS',
    reference TEXT NOT NULL UNIQUE,  -- Unique transaction reference
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, completed, failed
    phone TEXT,
    provider TEXT,  -- Payment provider (e.g., Paystack, MoMo)
    raw_payload JSONB,  -- Raw response from payment provider
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_reference ON transactions(reference);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at DESC);
-- JSON index for Paystack reference lookup
CREATE INDEX IF NOT EXISTS idx_transactions_paystack_ref 
    ON transactions((raw_payload->'data'->>'reference'));


-- ============================================================
-- 8. REFERRALS TABLE
-- Referral tracking and bonus management
-- ============================================================
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES base_users(id) ON DELETE CASCADE,
    referred_id UUID NOT NULL UNIQUE REFERENCES base_users(id) ON DELETE CASCADE,
    referral_code TEXT NOT NULL,
    bonus_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.10,
    bonus_paid BOOLEAN NOT NULL DEFAULT false,
    bonus_paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referral_code ON referrals(referral_code);
CREATE INDEX IF NOT EXISTS idx_referrals_bonus_paid ON referrals(bonus_paid);


-- ============================================================
-- RPC FUNCTIONS FOR ATOMIC WALLET OPERATIONS
-- These prevent race conditions during concurrent transactions
-- ============================================================

-- Credit wallet balance atomically
CREATE OR REPLACE FUNCTION credit_wallet(
    wallet_id_param UUID,
    amount_param DECIMAL
)
RETURNS VOID AS $$
BEGIN
    UPDATE wallets
    SET 
        balance = balance + amount_param,
        updated_at = NOW()
    WHERE id = wallet_id_param;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Wallet not found: %', wallet_id_param;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- Debit wallet balance atomically with balance check
CREATE OR REPLACE FUNCTION debit_wallet(
    wallet_id_param UUID,
    amount_param DECIMAL
)
RETURNS VOID AS $$
DECLARE
    current_balance DECIMAL;
BEGIN
    -- Lock the row for update to prevent race conditions
    SELECT balance INTO current_balance
    FROM wallets
    WHERE id = wallet_id_param
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Wallet not found: %', wallet_id_param;
    END IF;
    
    IF current_balance < amount_param THEN
        RAISE EXCEPTION 'Insufficient balance. Available: %, Required: %', current_balance, amount_param;
    END IF;
    
    UPDATE wallets
    SET 
        balance = balance - amount_param,
        updated_at = NOW()
    WHERE id = wallet_id_param;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ============================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Enable RLS for production security
-- ============================================================

-- Enable RLS on all tables (uncomment in production)
-- ALTER TABLE base_users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE telegram_users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE whatsapp_users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE bundles ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- UPDATED_AT TRIGGER
-- Automatically update 'updated_at' on row changes
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_base_users_updated_at
    BEFORE UPDATE ON base_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_telegram_users_updated_at
    BEFORE UPDATE ON telegram_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_whatsapp_users_updated_at
    BEFORE UPDATE ON whatsapp_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at
    BEFORE UPDATE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bundles_updated_at
    BEFORE UPDATE ON bundles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- VERIFICATION QUERY
-- Run this to verify all tables were created
-- ============================================================
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
AND table_name IN (
    'base_users', 
    'telegram_users', 
    'whatsapp_users', 
    'wallets', 
    'bundles', 
    'orders', 
    'transactions', 
    'referrals'
)
ORDER BY table_name;

-- Expected output:
-- table_name       | column_count
-- -----------------|-------------
-- base_users       | 5
-- bundles          | 9
-- orders           | 10
-- referrals        | 8
-- telegram_users   | 8
-- transactions     | 12
-- wallets          | 5
-- whatsapp_users   | 6
