-- PokeApp Supabase V2 greenfield schema.
-- 009_seed: minimal reproducible seed for bootstrap/staging.
-- No credentials or historical results are seeded here.

begin;

insert into public.app_settings (key, value, description)
values
  ('schema.version', '"2.0-greenfield"'::jsonb, 'Supabase V2 schema marker.'),
  ('storage.raw_saves_bucket', '"raw-saves"'::jsonb, 'Private bucket expected for raw save files.')
on conflict (key) do update
set value = excluded.value,
    description = excluded.description,
    updated_at = now();

insert into public.trainers (display_name, slug, metadata)
values
  ('Anto', 'anto', '{"seeded": true}'::jsonb),
  ('Victor', 'victor', '{"seeded": true}'::jsonb),
  ('Rober', 'rober', '{"seeded": true}'::jsonb),
  ('Samu', 'samu', '{"seeded": true}'::jsonb),
  ('Daviry', 'daviry', '{"seeded": true}'::jsonb),
  ('Sergio', 'sergio', '{"seeded": true}'::jsonb),
  ('Iker', 'iker', '{"seeded": true}'::jsonb),
  ('Aaron', 'aaron', '{"seeded": true}'::jsonb),
  ('Miguel', 'miguel', '{"seeded": true}'::jsonb),
  ('Barto', 'barto', '{"seeded": true}'::jsonb)
on conflict (slug) do update
set display_name = excluded.display_name,
    globally_enabled = true,
    updated_at = now();

insert into public.shop_items (code, name, category, description, base_price, image_key, metadata)
values
  ('revivir_pokemon', 'Revivir Pokemon', 'comodines', 'Permite revivir un Pokemon segun las reglas activas.', 12, 'max-revive', '{"seeded": true}'::jsonb),
  ('robar_pokemon', 'Robar Pokemon', 'comodines', 'Permite robar un Pokemon segun las reglas activas.', 12, 'dread-plate', '{"seeded": true}'::jsonb),
  ('captura_extra', 'Captura Extra', 'comodines', 'Permite una captura adicional segun las reglas activas.', 5, 'ultra-ball', '{"seeded": true}'::jsonb),
  ('blindar_pokemon', 'Blindar Pokemon', 'comodines', 'Protege un Pokemon frente a robo segun las reglas activas.', 12, 'metal-coat', '{"seeded": true}'::jsonb),
  ('fosil', 'Fosil', 'comodines', 'Permite usar un fosil segun las reglas activas.', 5, 'helix-fossil', '{"seeded": true}'::jsonb),

  ('baya_aranja', 'Baya Aranja', 'bayas', 'Restaura 10 PS al 50% PS.', 2, 'oran-berry', '{"seeded": true}'::jsonb),
  ('baya_zidra', 'Baya Zidra', 'bayas', 'Restaura 25% de PS maximos.', 3, 'sitrus-berry', '{"seeded": true}'::jsonb),
  ('baya_zreza', 'Baya Zreza', 'bayas', 'Cura paralisis.', 2, 'cheri-berry', '{"seeded": true}'::jsonb),
  ('baya_ziuela', 'Baya Ziuela', 'bayas', 'Cura sueno.', 3, 'chesto-berry', '{"seeded": true}'::jsonb),
  ('baya_meloc', 'Baya Meloc', 'bayas', 'Cura envenenamiento.', 2, 'pecha-berry', '{"seeded": true}'::jsonb),
  ('baya_safre', 'Baya Safre', 'bayas', 'Cura quemaduras.', 2, 'rawst-berry', '{"seeded": true}'::jsonb),
  ('baya_perasi', 'Baya Perasi', 'bayas', 'Cura congelacion.', 2, 'aspear-berry', '{"seeded": true}'::jsonb),
  ('baya_atania', 'Baya Atania', 'bayas', 'Cura confusion.', 2, 'persim-berry', '{"seeded": true}'::jsonb),
  ('baya_aslac', 'Baya Aslac', 'bayas', 'Velocidad +1 etapa al 25% PS.', 2, 'salac-berry', '{"seeded": true}'::jsonb),
  ('baya_lichi', 'Baya Lichi', 'bayas', 'Ataque +1 etapa al 25% PS.', 2, 'liechi-berry', '{"seeded": true}'::jsonb),
  ('baya_petaya', 'Baya Petaya', 'bayas', 'At. Esp. +1 etapa al 25% PS.', 2, 'petaya-berry', '{"seeded": true}'::jsonb),
  ('baya_ganlon', 'Baya Ganlon', 'bayas', 'Defensa +1 etapa al 25% PS.', 2, 'ganlon-berry', '{"seeded": true}'::jsonb),
  ('baya_apicot', 'Baya Apicot', 'bayas', 'Def. Esp. +1 etapa al 25% PS.', 2, 'apicot-berry', '{"seeded": true}'::jsonb),
  ('baya_lansat', 'Baya Lansat', 'bayas', 'Ratio critico +2 etapas al 25% PS.', 2, 'lansat-berry', '{"seeded": true}'::jsonb),
  ('baya_starf', 'Baya Starf', 'bayas', 'Sube mucho una stat al azar.', 2, 'starf-berry', '{"seeded": true}'::jsonb),
  ('baya_occa', 'Baya Occa (Fuego)', 'bayas', 'Reduce dano de Fuego supereficaz un 50%.', 3, 'occa-berry', '{"seeded": true}'::jsonb),
  ('baya_passho', 'Baya Passho (Agua)', 'bayas', 'Reduce dano de Agua supereficaz un 50%.', 3, 'passho-berry', '{"seeded": true}'::jsonb),
  ('baya_wacan', 'Baya Wacan (Electrico)', 'bayas', 'Reduce dano de Electrico supereficaz un 50%.', 3, 'wacan-berry', '{"seeded": true}'::jsonb),
  ('baya_rindo', 'Baya Rindo (Planta)', 'bayas', 'Reduce dano de Planta supereficaz un 50%.', 3, 'rindo-berry', '{"seeded": true}'::jsonb),
  ('baya_yache', 'Baya Yache (Hielo)', 'bayas', 'Reduce dano de Hielo supereficaz un 50%.', 3, 'yache-berry', '{"seeded": true}'::jsonb),
  ('baya_shuca', 'Baya Shuca (Tierra)', 'bayas', 'Reduce dano de Tierra supereficaz un 50%.', 3, 'shuca-berry', '{"seeded": true}'::jsonb),
  ('baya_chople', 'Baya Chople (Lucha)', 'bayas', 'Reduce dano de Lucha supereficaz un 50%.', 3, 'chople-berry', '{"seeded": true}'::jsonb),
  ('baya_kebia', 'Baya Kebia (Veneno)', 'bayas', 'Reduce dano de Veneno supereficaz un 50%.', 3, 'kebia-berry', '{"seeded": true}'::jsonb),
  ('baya_coba', 'Baya Coba (Volador)', 'bayas', 'Reduce dano de Volador supereficaz un 50%.', 3, 'coba-berry', '{"seeded": true}'::jsonb),
  ('baya_payapa', 'Baya Payapa (Psiquico)', 'bayas', 'Reduce dano de Psiquico supereficaz un 50%.', 3, 'payapa-berry', '{"seeded": true}'::jsonb),
  ('baya_tanga', 'Baya Tanga (Bicho)', 'bayas', 'Reduce dano de Bicho supereficaz un 50%.', 3, 'tanga-berry', '{"seeded": true}'::jsonb),
  ('baya_charti', 'Baya Charti (Roca)', 'bayas', 'Reduce dano de Roca supereficaz un 50%.', 3, 'charti-berry', '{"seeded": true}'::jsonb),
  ('baya_kasib', 'Baya Kasib (Fantasma)', 'bayas', 'Reduce dano de Fantasma supereficaz un 50%.', 3, 'kasib-berry', '{"seeded": true}'::jsonb),
  ('baya_haban', 'Baya Haban (Dragon)', 'bayas', 'Reduce dano de Dragon supereficaz un 50%.', 3, 'haban-berry', '{"seeded": true}'::jsonb),
  ('baya_colbur', 'Baya Colbur (Siniestro)', 'bayas', 'Reduce dano de Siniestro supereficaz un 50%.', 3, 'colbur-berry', '{"seeded": true}'::jsonb),
  ('baya_babiri', 'Baya Babiri (Acero)', 'bayas', 'Reduce dano de Acero supereficaz un 50%.', 3, 'babiri-berry', '{"seeded": true}'::jsonb),
  ('baya_chilan', 'Baya Chilan (Normal)', 'bayas', 'Reduce dano de Normal un 50%.', 3, 'chilan-berry', '{"seeded": true}'::jsonb),

  ('gafas_elegidas', 'Gafas Elegidas', 'competitivos', 'At. Esp. +50%; bloquea cambio de movimiento.', 8, 'choice-specs', '{"seeded": true}'::jsonb),
  ('cinta_elegida', 'Cinta Elegida', 'competitivos', 'Ataque +50%; bloquea cambio de movimiento.', 8, 'choice-band', '{"seeded": true}'::jsonb),
  ('panuelo_elegido', 'Panuelo Elegido', 'competitivos', 'Velocidad +50%; bloquea cambio de movimiento.', 8, 'choice-scarf', '{"seeded": true}'::jsonb),
  ('restos', 'Restos', 'competitivos', 'Restaura 1/16 de PS por turno.', 8, 'leftovers', '{"seeded": true}'::jsonb),
  ('banda_focus', 'Banda Focus', 'competitivos', 'Con PS completos, sobrevive a 1 golpe con 1 PS.', 7, 'focus-sash', '{"seeded": true}'::jsonb),
  ('vidasfera', 'Vidasfera', 'competitivos', 'Dano +30%; pierde 10% PS max tras atacar.', 7, 'life-orb', '{"seeded": true}'::jsonb),
  ('mineral_evolutivo', 'Mineral Evolutivo', 'competitivos', 'Defensa y Def. Esp. +50% si el Pokemon aun puede evolucionar.', 8, 'eviolite', '{"seeded": true}'::jsonb),
  ('casco_dentado', 'Casco Dentado', 'competitivos', 'Hace dano al rival si golpea con contacto.', 7, 'rocky-helmet', '{"seeded": true}'::jsonb),
  ('globo_helio', 'Globo Helio', 'competitivos', 'Inmunidad a Tierra hasta recibir dano.', 5, 'air-balloon', '{"seeded": true}'::jsonb),
  ('gemas_elementales', 'Gemas Elementales', 'competitivos', 'Potencian una vez un movimiento del tipo de la gema.', 6, 'fire-gem', '{"seeded": true}'::jsonb),
  ('boton_escape', 'Boton Escape', 'competitivos', 'Cambia al portador tras recibir dano.', 4, 'eject-button', '{"seeded": true}'::jsonb),
  ('tarjeta_roja', 'Tarjeta Roja', 'competitivos', 'Expulsa al atacante y fuerza cambio.', 4, 'red-card', '{"seeded": true}'::jsonb),
  ('hierba_blanca', 'Hierba Blanca', 'competitivos', 'Restaura reducciones de estadisticas.', 5, 'white-herb', '{"seeded": true}'::jsonb),
  ('roca_del_rey', 'Roca del Rey', 'competitivos', 'Puede hacer retroceder al golpear.', 5, 'kings-rock', '{"seeded": true}'::jsonb),
  ('periscopio', 'Periscopio', 'competitivos', 'Sube el ratio critico.', 5, 'scope-lens', '{"seeded": true}'::jsonb),
  ('lupa', 'Lupa', 'competitivos', 'Precision +20% si el usuario actua despues.', 5, 'zoom-lens', '{"seeded": true}'::jsonb),
  ('toxisfera', 'Toxisfera', 'competitivos', 'Envenena gravemente al portador al final del turno.', 5, 'toxic-orb', '{"seeded": true}'::jsonb),
  ('llamasfera', 'Llamasfera', 'competitivos', 'Quema al portador al final del turno.', 5, 'flame-orb', '{"seeded": true}'::jsonb),
  ('objeto_potenciador_tipo', 'Objeto Potenciador de Tipo', 'competitivos', 'Potencia movimientos de un tipo.', 4, 'silk-scarf', '{"seeded": true}'::jsonb),

  ('capsula_habilidad', 'Capsula Habilidad', 'crianza', 'Cambia habilidad normal.', 8, 'ability-capsule', '{"seeded": true}'::jsonb),
  ('chapa_dorada', 'Chapa Dorada', 'crianza', 'Maximiza IVs en todos los stats.', 15, 'gold-bottle-cap', '{"seeded": true, "promotion_blocked": true}'::jsonb),
  ('chapa_plateada', 'Chapa Plateada', 'crianza', 'Maximiza un IV concreto.', 6, 'bottle-cap', '{"seeded": true}'::jsonb),
  ('menta_naturaleza', 'Menta de Naturaleza', 'crianza', 'Cambia naturaleza.', 6, 'leaf-stone', '{"seeded": true}'::jsonb),
  ('objeto_evolutivo', 'Objeto Evolutivo', 'crianza', 'Piedras y otros objetos de evolucion.', 4, 'dawn-stone', '{"seeded": true}'::jsonb)
on conflict (code) do update
set name = excluded.name,
    category = excluded.category,
    description = excluded.description,
    base_price = excluded.base_price,
    image_key = excluded.image_key,
    metadata = excluded.metadata,
    enabled = true,
    updated_at = now();

-- Supabase-only bucket bootstrap. Plain Postgres builds skip this safely.
do $$
begin
  if exists (
    select 1
    from information_schema.schemata
    where schema_name = 'storage'
  ) then
    execute $storage$
      insert into storage.buckets (id, name, public)
      values ('raw-saves', 'raw-saves', false)
      on conflict (id) do update
      set name = excluded.name,
          public = false
    $storage$;
  end if;
end;
$$;

commit;
