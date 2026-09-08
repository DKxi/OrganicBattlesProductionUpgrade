import logging
from typing import Dict, Any, Union
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session
from app.infrastructure.database.models import (
    Base,
    User,
    VerificationCode,
    AuthSession,
    GameSession,
    Curriculum,
    Track,
    Question,
)
from app.infrastructure.database.engine import build_engine

logger = logging.getLogger("organicbattles.migration")


def _row_to_dict(model_cls, row) -> Dict[str, Any]:
    """Extract model columns as a dictionary."""
    return {col.name: getattr(row, col.name) for col in model_cls.__table__.columns}


def migrate_sqlite_to_postgres(
    source_engine: Union[Engine, str],
    target_engine: Union[Engine, str],
) -> Dict[str, int]:
    """
    Copy all user accounts, credentials, auth tokens, battle sessions,
    curricula, track configurations, and question banks from source engine into target engine
    with preserved foreign keys and relationships.
    Idempotent: merges/updates existing records without creating duplicates.
    """
    if isinstance(source_engine, str):
        source_engine = build_engine(source_engine)
    if isinstance(target_engine, str):
        target_engine = build_engine(target_engine)

    # Ensure schema exists on target database
    Base.metadata.create_all(bind=target_engine)

    stats = {
        "users": 0,
        "verification_codes": 0,
        "auth_sessions": 0,
        "game_sessions": 0,
        "curricula": 0,
        "tracks": 0,
        "questions": 0,
    }

    with Session(source_engine) as src, Session(target_engine) as dst:
        # 1. Curricula (Top-level content configuration)
        curricula = src.query(Curriculum).all()
        for c in curricula:
            c_data = _row_to_dict(Curriculum, c)
            existing_c = dst.query(Curriculum).filter(Curriculum.id == c.id).first()
            if not existing_c:
                dst.add(Curriculum(**c_data))
                stats["curricula"] += 1
            else:
                for k, v in c_data.items():
                    setattr(existing_c, k, v)
        dst.commit()

        # 3. Tracks (FK: curricula.id)
        tracks = src.query(Track).all()
        for t in tracks:
            t_data = _row_to_dict(Track, t)
            existing_t = dst.query(Track).filter(Track.id == t.id).first()
            if not existing_t:
                dst.add(Track(**t_data))
                stats["tracks"] += 1
            else:
                for k, v in t_data.items():
                    setattr(existing_t, k, v)
        dst.commit()

        # 4. Questions (FK: tracks.id)
        q_count = src.query(Question).count()
        if q_count > 0:
            logger.info("Migrating %d questions in batches of 1000...", q_count)
            # Clear target questions if re-migrating to avoid duplicates
            dst.query(Question).delete()
            dst.commit()

            offset = 0
            batch_size = 1000
            while offset < q_count:
                q_rows = (
                    src.query(Question)
                    .order_by(Question.id.asc())
                    .offset(offset)
                    .limit(batch_size)
                    .all()
                )
                if not q_rows:
                    break
                mappings = [_row_to_dict(Question, q) for q in q_rows]
                dst.bulk_insert_mappings(Question, mappings)
                dst.commit()
                stats["questions"] += len(mappings)
                offset += len(q_rows)

        # 5. Users (Primary account entity)
        users = src.query(User).all()
        for u in users:
            u_data = _row_to_dict(User, u)
            existing_user = dst.query(User).filter(User.id == u.id).first()
            if not existing_user:
                dst.add(User(**u_data))
                stats["users"] += 1
            else:
                for k, v in u_data.items():
                    setattr(existing_user, k, v)
        dst.commit()

        # 6. Verification Codes (FK: users.id)
        codes = src.query(VerificationCode).all()
        for vc in codes:
            vc_data = _row_to_dict(VerificationCode, vc)
            existing_vc = dst.query(VerificationCode).filter(
                VerificationCode.id == vc.id
            ).first()
            if not existing_vc:
                dst.add(VerificationCode(**vc_data))
                stats["verification_codes"] += 1
            else:
                for k, v in vc_data.items():
                    setattr(existing_vc, k, v)
        dst.commit()

        # 7. Auth Sessions (FK: users.id)
        sessions = src.query(AuthSession).all()
        for s in sessions:
            s_data = _row_to_dict(AuthSession, s)
            existing_session = dst.query(AuthSession).filter(
                AuthSession.token_hash == s.token_hash
            ).first()
            if not existing_session:
                dst.add(AuthSession(**s_data))
                stats["auth_sessions"] += 1
            else:
                for k, v in s_data.items():
                    setattr(existing_session, k, v)
        dst.commit()

        # 8. Game Sessions (FK: users.id, unique: user_id)
        game_sessions = src.query(GameSession).all()
        for gs in game_sessions:
            gs_data = _row_to_dict(GameSession, gs)
            existing_gs = dst.query(GameSession).filter(
                (GameSession.id == gs.id) | (GameSession.user_id == gs.user_id)
            ).first()
            if not existing_gs:
                dst.add(GameSession(**gs_data))
                stats["game_sessions"] += 1
            else:
                for k, v in gs_data.items():
                    setattr(existing_gs, k, v)
        dst.commit()

    # Synchronize sequence generator for PostgreSQL if applicable
    if target_engine.dialect.name == "postgresql":
        try:
            with target_engine.begin() as conn:
                conn.execute(text(
                    "SELECT setval("
                    "  pg_get_serial_sequence('verification_codes', 'id'), "
                    "  coalesce((SELECT max(id) FROM verification_codes), 1)"
                    ");"
                ))
                conn.execute(text(
                    "SELECT setval("
                    "  pg_get_serial_sequence('questions', 'id'), "
                    "  coalesce((SELECT max(id) FROM questions), 1)"
                    ");"
                ))
        except Exception as seq_err:
            logger.warning("Could not synchronize PostgreSQL sequence: %s", seq_err)

    logger.info(
        "Successfully migrated data to target: %d curricula, %d tracks, %d questions, %d users, %d codes, %d auth sessions, %d game sessions.",
        stats["curricula"],
        stats["tracks"],
        stats["questions"],
        stats["users"],
        stats["verification_codes"],
        stats["auth_sessions"],
        stats["game_sessions"],
    )
    return stats


# Alias for general cross-database migration
migrate_database = migrate_sqlite_to_postgres

