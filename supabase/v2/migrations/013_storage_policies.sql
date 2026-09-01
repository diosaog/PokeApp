-- PokeApp Supabase V2 security layer.
-- 013_storage_policies: private raw-saves bucket access rules.
-- Supabase Cloud already owns storage.objects; keep this migration policy-only.

begin;

do $$
begin
  if exists (
    select 1
    from information_schema.tables
    where table_schema = 'storage'
      and table_name = 'objects'
  ) then
    execute 'drop policy if exists raw_saves_select_own_or_admin on storage.objects';
    execute 'drop policy if exists raw_saves_insert_own_or_admin on storage.objects';
    execute 'drop policy if exists raw_saves_update_own_or_admin on storage.objects';
    execute 'drop policy if exists raw_saves_delete_own_or_admin on storage.objects';

    execute $policy$
      create policy raw_saves_select_own_or_admin
      on storage.objects
      for select
      to authenticated
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
      to authenticated
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
      to authenticated
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
      to authenticated
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
