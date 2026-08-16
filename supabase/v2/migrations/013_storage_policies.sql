-- PokeApp Supabase V2 security layer.
-- 013_storage_policies: private raw-saves bucket access rules.

begin;

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'storage'
      and table_name = 'objects'
  ) then
    execute 'alter table storage.objects enable row level security';

    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute 'revoke all on table storage.objects from anon';
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute 'grant select, insert, update, delete on table storage.objects to authenticated';
    end if;

    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute 'grant all privileges on table storage.objects to service_role';
    end if;

    execute $policy$
      create policy raw_saves_select_own_or_admin
      on storage.objects
      for select
      using (
        bucket_id = 'raw-saves'
        and (
          public.is_current_user_admin()
          or split_part(name, '/', 1) = public.current_trainer_id()::text
        )
      )
    $policy$;

    execute $policy$
      create policy raw_saves_insert_own_or_admin
      on storage.objects
      for insert
      with check (
        bucket_id = 'raw-saves'
        and (
          public.is_current_user_admin()
          or split_part(name, '/', 1) = public.current_trainer_id()::text
        )
      )
    $policy$;

    execute $policy$
      create policy raw_saves_update_own_or_admin
      on storage.objects
      for update
      using (
        bucket_id = 'raw-saves'
        and (
          public.is_current_user_admin()
          or split_part(name, '/', 1) = public.current_trainer_id()::text
        )
      )
      with check (
        bucket_id = 'raw-saves'
        and (
          public.is_current_user_admin()
          or split_part(name, '/', 1) = public.current_trainer_id()::text
        )
      )
    $policy$;

    execute $policy$
      create policy raw_saves_delete_own_or_admin
      on storage.objects
      for delete
      using (
        bucket_id = 'raw-saves'
        and (
          public.is_current_user_admin()
          or split_part(name, '/', 1) = public.current_trainer_id()::text
        )
      )
    $policy$;
  end if;
end;
$$;

commit;
