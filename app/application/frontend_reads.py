"""Safe read composition; mutations remain authoritative in their existing services."""

from app.api.read_models import (
    HallPage,
    OverviewRead,
    PCRead,
    SeasonPage,
    ShopRead,
    TrainerRead,
    InventoryRead,
)
from app.repositories.errors import NotFoundError, PersistenceError
from app.repositories.supabase.frontend_reads import FrontendReadRepository


class FrontendReads:
    def __init__(self, repository: FrontendReadRepository):
        self.repo = repository

    def rows(self, table, columns, **filters):
        # Never silently present a truncated competition as complete.
        rows = self.repo.rows(table, columns, filters=filters, limit=501)
        if len(rows) > 500:
            raise PersistenceError("Read capacity exceeded")
        return rows

    def seasons(self, offset=0):
        rows = self.repo.rows(
            "public_seasons", "id,name,status", offset=offset, limit=51
        )
        return SeasonPage(
            items=rows[:50], next_offset=offset + 50 if len(rows) > 50 else None
        )

    def trainers(self):
        return [
            TrainerRead.model_validate(r)
            for r in self.rows("public_trainers", "id,display_name")
        ]

    def season(self, sid):
        rows = self.rows("seasons", "id,name,status,current_matchday_id", id=sid)
        if not rows or rows[0]["status"] == "discarded":
            raise NotFoundError("Season not found")
        return rows[0]

    def balance(self, sid, tid):
        players = self.rows("season_players", "id", season_id=sid, trainer_id=tid)
        if not players:
            return None
        rows = self.rows(
            "public_coin_balances", "trainer_id,balance", season_id=sid, trainer_id=tid
        )
        return rows[0]["balance"] if rows else 0

    def overview(self, sid, tid):
        season = self.season(sid)
        trainers = {str(t.id): t.display_name for t in self.trainers()}
        players = self.rows(
            "public_season_players", "id,trainer_id,status", season_id=sid
        )
        stats = {
            r["season_player_id"]: r["badges_count"]
            for r in self.rows(
                "public_season_player_stats",
                "season_player_id,badges_count",
                season_id=sid,
            )
        }
        for p in players:
            p.update(
                display_name=trainers.get(p["trainer_id"], "Entrenador no disponible"),
                badges_count=stats.get(p["id"]),
            )
        snapshots = []
        for r in self.rows(
            "public_matchday_snapshots",
            "matchday_id,revision,closed_at,snapshot",
            season_id=sid,
        ):
            snapshot = r.pop("snapshot")
            if snapshot.get("schema_version") != 2:
                raise PersistenceError("Unsupported official snapshot")
            r["standings"] = [
                dict(
                    season_player_id=s["trainer_id"],
                    division=s["division_id"],
                    **{
                        k: s[k]
                        for k in (
                            "position",
                            "division_position",
                            "points_awarded",
                            "score",
                        )
                    },
                )
                for s in snapshot["standings"]
            ]
            snapshots.append(r)
        return OverviewRead(
            season=season,
            players=players,
            snapshots=snapshots,
            points=self.rows(
                "public_sanctioned_points",
                "season_player_id,earned_points,points_reduction,dead_points_penalty,sanctioned_points,source_matchday_id",
                season_id=sid,
            ),
            days=self.rows("public_matchdays", "id,number,status", season_id=sid),
            matches=self.rows(
                "public_matches",
                "id,matchday_id,division_id,player_a_id,player_b_id,winner_id,status",
                season_id=sid,
            ),
            divisions=self.rows("public_divisions", "id,code,name", season_id=sid),
            memberships=self.rows(
                "public_division_memberships",
                "season_player_id,division_id,effective_from_matchday_number,effective_to_matchday_number,eligibility_ends_before_matchday_number",
                season_id=sid,
            ),
            locks=self.rows(
                "public_team_locks",
                "trainer_id,matchday_id,locked_at,is_late,public_team_snapshot",
                season_id=sid,
            ),
            balance=self.balance(sid, tid),
        )

    def pc(self, sid, tid):
        self.season(sid)
        players = self.rows(
            "season_players", "current_save_file_id", season_id=sid, trainer_id=tid
        )
        current = players[0]["current_save_file_id"] if players else None
        saves = (
            self.rows(
                "save_files",
                "id,parser_status,parser_version,uploaded_at,sha256",
                id=current,
                season_id=sid,
                trainer_id=tid,
                deleted_at=None,
            )
            if current
            else []
        )
        if not saves:
            return PCRead(save=None, status="no_current_save", pokemon=[])
        save = saves[0]
        parsed = (
            self.rows(
                "parsed_saves",
                "status,schema_version,payload",
                save_file_id=current,
                parser_version=save["parser_version"],
            )
            if save["parser_status"] == "parsed"
            else []
        )
        if not parsed or parsed[0]["status"] != "parsed":
            return PCRead(save=save, status="not_ready", pokemon=[])
        payload = parsed[0]["payload"]
        if parsed[0]["schema_version"] != 1 or not isinstance(payload, dict):
            return PCRead(save=save, status="unsupported_payload", pokemon=[])
        for key, expected in (
            ("save_record_id", current),
            ("trainer_id", tid),
            ("source_hash", save["sha256"]),
        ):
            if key in payload and payload[key] != expected:
                raise PersistenceError("Parsed identity mismatch")
        # Accept the neutral slotted DTO only; never infer IDs from species/slots.
        party, boxes = payload.get("party", []), payload.get("boxes", [])
        if any("slot_number" not in s or "pokemon" not in s for s in party):
            return PCRead(save=save, status="unsupported_payload", pokemon=[])
        entities = self.observed_entities(sid, tid, current)
        pokemon = [
            dict(
                location=f"Equipo · {s['slot_number']}",
                pokemon=s["pokemon"],
                pokemon_entity_id=entities.get(("party", 0, s["slot_number"])),
            )
            for s in party
            if s.get("pokemon")
        ]
        for box in boxes:
            for slot in box["slots"]:
                if slot.get("pokemon"):
                    pokemon.append(
                        dict(
                            location=f"Caja {box['box_number']} · {slot['slot_number']}",
                            pokemon=slot["pokemon"],
                            pokemon_entity_id=entities.get(
                                ("box", box["box_number"], slot["slot_number"])
                            ),
                        )
                    )
        return PCRead(save=save, status="ready", pokemon=pokemon)

    def shop(self, sid, tid):
        season = self.season(sid)
        promotions = (
            self.rows(
                "public_shop_promotions",
                "id,shop_item_id,status,effective_price,stock_total,stock_used",
                season_id=sid,
                matchday_id=season["current_matchday_id"],
            )
            if season["current_matchday_id"]
            else []
        )
        return ShopRead(
            items=self.rows(
                "public_shop_items", "id,code,name,category,description,base_price"
            ),
            promotions=promotions,
            balance=self.balance(sid, tid),
        )

    def observed_entities(self, sid, tid, save):
        # Look up recorded reconciliations, never manufacture identity from a slot.
        observations = self.rows(
            "pokemon_observations",
            "pokemon_entity_id,source,box_number,slot_number,outcome",
            season_id=sid,
            trainer_id=tid,
            save_file_id=save,
        )
        if not observations:
            return {}
        entities = {
            r["id"]
            for r in self.rows(
                "pokemon_entities",
                "id",
                season_id=sid,
                owner_trainer_id=tid,
                identity_status="unambiguous",
            )
        }
        return {
            (o["source"], o["box_number"], o["slot_number"]): o["pokemon_entity_id"]
            for o in observations
            if o["outcome"] in ("NEW", "MATCHED") and o["pokemon_entity_id"] in entities
        }

    def inventory(self, sid, tid):
        season = self.season(sid)
        pc = self.pc(sid, tid)
        targets = [
            dict(
                pokemon_entity_id=s.pokemon_entity_id,
                trainer_id=tid,
                location=s.location,
                visibility="own",
                pokemon=s.pokemon.model_dump(),
            )
            for s in pc.pokemon
            if s.pokemon_entity_id
        ]
        # Rivals: only the already-public frozen team. Never read a rival parsed save,
        # box contents, private snapshot, raw evidence, flags or candidate keys.
        if season["current_matchday_id"]:
            locks = self.rows(
                "team_locks",
                "trainer_id,save_file_id,public_team_snapshot",
                season_id=sid,
                matchday_id=season["current_matchday_id"],
            )
            for lock in locks:
                if lock["trainer_id"] == tid:
                    continue
                entities = self.observed_entities(
                    sid, lock["trainer_id"], lock["save_file_id"]
                )
                for index, pokemon in enumerate(lock["public_team_snapshot"], 1):
                    entity = entities.get(("party", 0, index))
                    if entity:
                        targets.append(
                            dict(
                                pokemon_entity_id=entity,
                                trainer_id=lock["trainer_id"],
                                location=f"Equipo fijado · {index}",
                                visibility="public_team_lock",
                                pokemon=pokemon,
                            )
                        )
        purchases = self.rows(
            "purchases",
            "id,shop_item_id,status,total_price,purchased_at",
            season_id=sid,
            trainer_id=tid,
        )
        catalog = (
            {i["id"]: i for i in self.rows("shop_items", "id,code,name")}
            if purchases
            else {}
        )
        for purchase in purchases:
            item = catalog[purchase["shop_item_id"]]
            purchase.update(item_name=item["name"], item_code=item["code"])
        return InventoryRead(purchases=purchases, targets=targets)

    def hall(self, offset=0):
        columns = "id,season_id,competition_type,champion_trainer_id,finalist_trainer_id,finalized_at,cup_id,cup_certificate_id,champion_side_id,finalist_side_id,cup_sides,cup_checksum"
        rows = self.repo.rows("public_hall_of_fame", columns, offset=offset, limit=51)
        return HallPage(
            items=rows[:50], next_offset=offset + 50 if len(rows) > 50 else None
        )
