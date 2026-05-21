// Incrementum Places — Supabase Integration Module
// Substitui o carregamento local _RAW por fetch da API Supabase

const SUPABASE_URL = 'https://oziequrhypzbfdynnnda.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im96aWVxdXJoeXB6YmZkeW5ubmRhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQwNTU3OTEsImV4cCI6MjA4OTYzMTc5MX0.dU0_ISLUdDVAh0XQ4wLFlDXf4ZTOuRh__4_mcp0aFxo';

// Cache local para offline
const CACHE_KEY = 'ip_supabase_cache';
const CACHE_TTL = 24 * 60 * 60 * 1000; // 24 horas

async function fetchFromSupabase() {
  try {
    // Buscar restaurantes ativos (não deletados)
    const [restaurantsRes, deletionsRes] = await Promise.all([
      fetch(`${SUPABASE_URL}/rest/v1/restaurants?order=name.asc`, {
        headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
      }),
      fetch(`${SUPABASE_URL}/rest/v1/restaurant_deletions`, {
        headers: { 'apikey': SUPABASE_KEY, 'Authorization': `Bearer ${SUPABASE_KEY}` }
      })
    ]);

    if (!restaurantsRes.ok) throw new Error(`Restaurants API: ${restaurantsRes.status}`);
    if (!deletionsRes.ok) throw new Error(`Deletions API: ${deletionsRes.status}`);

    const restaurants = await restaurantsRes.json();
    const deletions = await deletionsRes.json();
    const deletedNames = new Set(deletions.map(d => d.name));

    // Filtrar deletados e converter para formato do app
    const activeRestaurants = restaurants
      .filter(r => !deletedNames.has(r.name))
      .map(r => ({
        n: r.name,
        h: r.neighborhood || '',
        c: r.cuisine || '',
        t: r.type || 'contemporary',
        ch: r.chef || '—',
        p: r.price || 2,
        mi: r.michelin || undefined,
        bib: r.bib || undefined,
        l50: r.latam50 || undefined,
        w50: r.world50 || undefined,
        st: r.status || 'want',
        oc: r.occasions || [],
        vb: r.vibe || '',
        ig: r.instagram || '',
        tel: r.phone || '',
        site: r.website || '',
        reserva: r.reservation || '',
        notes: r.notes || '',
        city: r.city || 'SP'
      }));

    // Salvar no cache local
    localStorage.setItem(CACHE_KEY, JSON.stringify({
      restaurants: activeRestaurants,
      deleted: Array.from(deletedNames),
      ts: Date.now()
    }));

    return { restaurants: activeRestaurants, deleted: Array.from(deletedNames) };
  } catch (err) {
    console.error('Supabase fetch failed:', err);
    // Fallback para cache local
    const cached = localStorage.getItem(CACHE_KEY);
    if (cached) {
      const data = JSON.parse(cached);
      console.log('Using cached data from', new Date(data.ts).toLocaleString());
      return { restaurants: data.restaurants, deleted: data.deleted };
    }
    throw err;
  }
}

// Função para deletar restaurante (cross-device)
async function deleteRestaurantCrossDevice(name) {
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/restaurant_deletions`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': `Bearer ${SUPABASE_KEY}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      },
      body: JSON.stringify({ name })
    });
    if (!res.ok) throw new Error(`Delete API: ${res.status}`);
    return true;
  } catch (err) {
    console.error('Cross-device delete failed:', err);
    return false;
  }
}

// Exportar para uso global
window.IncrementumSupabase = {
  fetch: fetchFromSupabase,
  delete: deleteRestaurantCrossDevice,
  URL: SUPABASE_URL,
  KEY: SUPABASE_KEY
};
