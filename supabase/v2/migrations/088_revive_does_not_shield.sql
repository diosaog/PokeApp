-- 088: Revivir ya no blinda (owner rule of 2026-11-18).
--
-- A revived Pokémon is REVIVIDO only: it can be robbed like any other live
-- Pokémon and can still be protected with Blindar. Blindar and Robar keep
-- shielding exactly as before (087). Pokémon that were shielded only because
-- they were revived lose that shield; a shield that came from Blindar, from a
-- robbery or from the retired «Blindaje por Robo» stays.
begin;

do $$ declare definition text=pg_get_functiondef('public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure);
  shield text=$q$  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'blindado',true)
    on conflict(season_id,pokemon_entity_id,flag_type) do update
      set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
$q$;
  guarded text=$q$  -- 088: Revivir no blinda; Blindar y Robar, sí.
  if v_effect<>'revive' then
  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'blindado',true)
    on conflict(season_id,pokemon_entity_id,flag_type) do update
      set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
  end if;
$q$;
begin
  if position(shield in definition)=0 or position(guarded in definition)>0 then
    raise exception 'unexpected redemption definition before 088'; end if;
  execute replace(definition,shield,guarded);
end $$;

-- Shields that only a revive gave. Every other source of a shield is an
-- applied Blindar, robbery or «Blindaje por Robo» redemption on that Pokémon.
update public.pokemon_entity_flags f set flag_value=false,legacy_flag_id=null,
    flag_timestamp=null,flag_trainer_id=null
  where f.flag_type='blindado' and f.flag_value is true
    and exists(select 1 from public.redemptions r where r.season_id=f.season_id
      and r.target_pokemon_entity_id=f.pokemon_entity_id and r.effect_code='revive' and r.status='applied')
    and not exists(select 1 from public.redemptions r where r.season_id=f.season_id
      and r.target_pokemon_entity_id=f.pokemon_entity_id
      and r.effect_code in ('shield','robbery_shield','steal') and r.status='applied');

do $$ begin
  if position($q$if v_effect<>'revive' then
  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'blindado',true)$q$ in
      pg_get_functiondef('public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure))=0
    or exists(select 1 from public.pokemon_entity_flags f
      where f.flag_type='blindado' and f.flag_value is true
        and exists(select 1 from public.redemptions r where r.season_id=f.season_id
          and r.target_pokemon_entity_id=f.pokemon_entity_id and r.effect_code='revive' and r.status='applied')
        and not exists(select 1 from public.redemptions r where r.season_id=f.season_id
          and r.target_pokemon_entity_id=f.pokemon_entity_id
          and r.effect_code in ('shield','robbery_shield','steal') and r.status='applied')) then
    raise exception '088: Revivir could not stop shielding'; end if;
end $$;

notify pgrst,'reload schema';
commit;
