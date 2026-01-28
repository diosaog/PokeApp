from __future__ import annotations

# Facade module to keep the public API stable while splitting implementation.

from storage_core import (
    BASE_DIR,
    DATA_DIR,
    SAVES_DIR,
    DB_PATH,
    _cache_data,
    _supabase_enabled,
    _sb,
    _bucket_name,
    _now_iso,
    _db_path,
    _conn,
    _sha256,
    _iso_to_ts,
    init_storage,
)
from storage_saves import (
    _fetch_save_by_id,
    save_upload,
    list_saves,
    set_current_save,
    get_current_save,
    load_save_bytes,
    get_current_save_path,
    list_saves_by_user,
    set_current_save_for_user,
    get_current_save_for_user,
    get_current_save_path_for_user,
)
from storage_purchases import (
    add_purchase,
    total_spent,
    list_purchases,
    list_inventory,
    add_redemption,
    set_purchase_status,
    clear_purchases,
)
from storage_flags import (
    _flags_key,
    _strip_flags_key,
    upsert_pokemon_flags,
    get_flags_by_fingerprints,
    clear_all_pokemon_flags,
    clear_pokemon_flags_for_owner,
)
from storage_settings import (
    settings_set,
    settings_get,
)

