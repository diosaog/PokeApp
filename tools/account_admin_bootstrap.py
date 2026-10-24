"""Render a private operator transaction; never executes SQL or loads secrets.

Only postgres can run it. The operator must independently verify the exact new
trainer/Auth binding. Neither name, PIN, invitation nor first-registration order
is authority. The existing private command journal records one promotion.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from uuid import UUID


def bootstrap_sql(trainer, auth, operation, verification_reference, registered_after):
    trainer, auth, operation = map(
        lambda v: str(UUID(str(v))), (trainer, auth, operation)
    )
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9 /:._-]{0,199}", verification_reference):
        raise ValueError("Independent verification reference required")
    since = datetime.fromisoformat(registered_after)
    if since.tzinfo is None:
        raise ValueError("Registration boundary requires an explicit timezone")
    since = since.astimezone(timezone.utc).isoformat()
    digest = hashlib.sha256(
        json.dumps(
            [trainer, auth, operation, verification_reference, since],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    reference = "'" + verification_reference.replace("'", "''") + "'"
    return f"""begin;
set local lock_timeout='5s';
set local statement_timeout='30s';
do $bootstrap$
declare receipt public.account_commands;
begin
 if current_user<>'postgres' then raise exception 'operator_required'; end if;
 perform pg_advisory_xact_lock(hashtextextended('operator-admin-bootstrap',0));
 lock table public.trainers in share row exclusive mode;
 select * into receipt from public.account_commands where operation_id='{operation}';
 if found then
   if receipt.kind<>'operator_admin_bootstrap' or receipt.request_hash<>'{digest}'
     or receipt.target_id<>'{trainer}' or not exists(select 1 from public.trainers
       where id='{trainer}' and auth_user_id='{auth}' and is_admin and globally_enabled)
     then raise exception 'bootstrap_conflict'; end if;
   return;
 end if;
 if exists(select 1 from public.trainers where is_admin)
   or exists(select 1 from public.account_commands where kind='operator_admin_bootstrap')
   then raise exception 'bootstrap_already_consumed'; end if;
 if not exists(select 1 from public.trainers t
   join public.account_credentials c on c.trainer_id=t.id
   join public.account_registrations r on r.trainer_id=t.id
   join auth.users u on u.id=t.auth_user_id
   left join public.account_session_guards g on g.trainer_id=t.id
   where t.id='{trainer}' and t.auth_user_id='{auth}' and t.globally_enabled
     and c.version=2 and not c.reset_required and not coalesce(g.blocked,false)
     and r.auth_user_id='{auth}' and r.status='complete'
     and r.credential_version=2 and r.created_at>='{since}'::timestamptz)
   then raise exception 'bootstrap_identity_unverified'; end if;
 update public.trainers set is_admin=true where id='{trainer}' and auth_user_id='{auth}';
 insert into public.account_commands(operation_id,actor_id,target_id,kind,request_hash,result)
 values('{operation}','{trainer}','{trainer}','operator_admin_bootstrap','{digest}',
   jsonb_build_object('auth_user_id','{auth}','verification_reference',{reference},
     'authority','private-postgres-operator','registered_after','{since}'));
end $bootstrap$;
commit;
"""


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in (
        "trainer",
        "auth",
        "operation",
        "verification-reference",
        "registered-after",
        "output",
    ):
        p.add_argument("--" + arg, required=True)
    a = p.parse_args()
    sql = bootstrap_sql(
        a.trainer, a.auth, a.operation, a.verification_reference, a.registered_after
    )
    # Never replace an earlier reviewed operator instruction.
    with Path(a.output).open("x", encoding="utf-8") as f:
        f.write(sql)
