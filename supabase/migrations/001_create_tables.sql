-- ================================================================
-- Incrementum Places — Schema Supabase
-- ================================================================
-- Criar este schema no SQL Editor do Supabase Dashboard
-- ================================================================

-- 1. Tabela principal de restaurantes
CREATE TABLE IF NOT EXISTS restaurants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    neighborhood TEXT,
    cuisine TEXT,
    type TEXT DEFAULT 'contemporary',
    chef TEXT DEFAULT '—',
    price INT DEFAULT 2,
    michelin INT,
    bib INT,
    latam50 INT,
    world50 INT,
    status TEXT DEFAULT 'want',
    occasions TEXT[] DEFAULT '{}',
    vibe TEXT,
    instagram TEXT,
    phone TEXT,
    website TEXT,
    reservation TEXT,
    notes TEXT,
    city TEXT DEFAULT 'SP',
    is_builtin BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tabela de deleções (soft delete cross-device)
CREATE TABLE IF NOT EXISTS restaurant_deletions (
    name TEXT PRIMARY KEY,
    deleted_at TIMESTAMPTZ DEFAULT NOW(),
    device_info TEXT DEFAULT ''
);

-- 3. Tabela de estado por usuário (status, notas, overrides)
-- Para uso futuro com autenticação
CREATE TABLE IF NOT EXISTS restaurant_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_name TEXT REFERENCES restaurants(name) ON DELETE CASCADE,
    status TEXT DEFAULT 'want',
    notes TEXT DEFAULT '',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ================================================================
-- RLS Policies — Permitir leitura pública, inserção de deleções
-- ================================================================

-- Restaurants: leitura pública
ALTER TABLE restaurants ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Allow public read restaurants"
    ON restaurants FOR SELECT USING (true);

-- Deletions: leitura pública + inserção anônima
ALTER TABLE restaurant_deletions ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Allow public read deletions"
    ON restaurant_deletions FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "Allow public insert deletions"
    ON restaurant_deletions FOR INSERT WITH CHECK (true);

-- States: leitura pública (para MVP; futuro: por user_id)
ALTER TABLE restaurant_states ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS "Allow public read states"
    ON restaurant_states FOR SELECT USING (true);

-- ================================================================
-- Índices
-- ================================================================
CREATE INDEX IF NOT EXISTS idx_restaurants_type ON restaurants(type);
CREATE INDEX IF NOT EXISTS idx_restaurants_status ON restaurants(status);
CREATE INDEX IF NOT EXISTS idx_deletions_name ON restaurant_deletions(name);

-- ================================================================
-- Função para restaurantes ativos (não deletados)
-- ================================================================
CREATE OR REPLACE FUNCTION get_active_restaurants()
RETURNS SETOF restaurants AS $$
BEGIN
    RETURN QUERY
    SELECT r.* FROM restaurants r
    LEFT JOIN restaurant_deletions d ON r.name = d.name
    WHERE d.name IS NULL
    ORDER BY r.name;
END;
$$ LANGUAGE plpgsql STABLE;
