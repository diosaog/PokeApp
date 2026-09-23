from copy import deepcopy
from uuid import UUID

from app.repositories.errors import ConflictError, NotFoundError, PersistenceError


class SupabasePokemonIdentityRepository:
    """Backend-only adapter. RPC performs atomic CAS under a PostgreSQL row lock."""
    def __init__(self, client):
        self._client = client

    def _one(self, table, **filters):
        query = self._client.table(table).select('*')
        for key, value in filters.items():
            query = query.eq(key, value)
        rows = query.limit(1).execute().data
        if not rows:
            raise NotFoundError('identity_source_not_found')
        return deepcopy(rows[0])

    def load_context(self, *, season_id, trainer_id, parsed_save_id):
        season_id, trainer_id, parsed_save_id = (str(UUID(v)) for v in (season_id, trainer_id, parsed_save_id))
        try:
            parsed = self._one('parsed_saves', id=parsed_save_id)
            saved = self._one('save_files', id=parsed['save_file_id'], season_id=season_id, trainer_id=trainer_id)
            heads = self._client.table('pokemon_identity_revisions').select('*').eq('season_id', season_id).eq(
                'trainer_id', trainer_id).order('revision_number', desc=True).limit(1).execute().data
            entities, offset = [], 0
            # Explicit pagination avoids silently dropping individuals at PostgREST's row limit.
            while True:
                rows = self._client.table('pokemon_entities').select('*').eq('season_id', season_id).eq(
                    'owner_trainer_id', trainer_id).order('id').range(offset, offset + 499).execute().data
                entities.extend(rows)
                if len(rows) < 500:
                    break
                offset += 500
            return dict(parsed=parsed, save=saved, head=heads[0] if heads else None, entities=entities)
        except NotFoundError:
            raise
        except Exception as exc:
            raise PersistenceError('identity_context_unavailable') from exc

    def commit(self, request):
        try:
            result = self._client.rpc('commit_pokemon_identity', {'p_request': deepcopy(request)}).execute().data
        except Exception as exc:
            error = ConflictError if str(getattr(exc, 'code', '')) == 'PT409' else PersistenceError
            raise error('identity_commit_rejected') from exc
        if not isinstance(result, dict) or result.get('revision', {}).get('save_file_id') != request['save_file_id']:
            raise PersistenceError('invalid_identity_receipt')
        return result

    def authoritative_target(self, *, season_id, trainer_id, observation_id):
        """Future effects must resolve CURRENT observation, not trust a caller's UUID."""
        obs = self._one('pokemon_observations', id=str(UUID(observation_id)),
                        season_id=str(UUID(season_id)), trainer_id=str(UUID(trainer_id)))
        heads = self._client.table('pokemon_identity_revisions').select('id').eq('season_id', season_id).eq(
            'trainer_id', trainer_id).order('revision_number', desc=True).limit(1).execute().data
        if not heads or heads[0]['id'] != obs['revision_id'] or not obs['pokemon_entity_id'] or obs['outcome'] == 'AMBIGUOUS':
            raise ConflictError('identity_target_not_authoritative')
        entity = self._one('pokemon_entities', id=obs['pokemon_entity_id'], season_id=season_id, owner_trainer_id=trainer_id)
        if entity['identity_status'] != 'unambiguous':
            raise ConflictError('identity_target_not_authoritative')
        # This is a read boundary. Future effect RPC must recheck under the same player lock.
        return entity['id']
