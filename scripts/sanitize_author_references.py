#!/usr/bin/env python3
"""
Sanitize author and textbook references (David, Klein, McMurry, McCurry)
in PostgreSQL and SQLite database records.
"""
import sys
import re
import argparse
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import text
from app.infrastructure.database.engine import build_engine, normalize_db_url
from app.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("organicbattles.sanitize")


def sanitize_database(db_url: str) -> int:
    """Sanitize questions and track tables in the target database."""
    normalized_url = normalize_db_url(db_url)
    logger.info("Connecting to database: %s", normalized_url.split("@")[-1] if "@" in normalized_url else normalized_url)
    engine = build_engine(normalized_url)

    updated_count = 0
    with engine.begin() as conn:
        # Check if questions table exists (OB_questions or questions)
        if normalized_url.startswith("sqlite"):
            existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        else:
            existing = {row[0] for row in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")).fetchall()}

        if "OB_questions" in existing:
            q_table = "OB_questions"
        elif "questions" in existing:
            q_table = "questions"
        else:
            logger.warning("Table 'OB_questions' or 'questions' does not exist in target database.")
            return 0

        t_table = "OB_tracks" if "OB_tracks" in existing else "tracks"

        # 1. Sanitize explanations
        logger.info("Sanitizing question explanations in '%s'...", q_table)
        res_exp1 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET explanation = REPLACE(explanation, 'In David Klein''s Organic Chemistry, ', 'In organic chemistry, ')
                WHERE explanation LIKE '%David Klein%'
            """)
        )
        updated_count += res_exp1.rowcount if res_exp1.rowcount != -1 else 0

        res_exp2 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET explanation = REPLACE(
                    explanation,
                    'Klein establishes four universal arrow-pushing primitives: nucleophilic attack, leaving group loss, proton transfer, and rearrangement.',
                    'Standard organic chemistry establishes four universal arrow-pushing primitives: nucleophilic attack, leaving group loss, proton transfer, and rearrangement.'
                )
                WHERE explanation LIKE '%Klein establishes%'
            """)
        )
        updated_count += res_exp2.rowcount if res_exp2.rowcount != -1 else 0

        # 2. Sanitize prompts
        logger.info("Sanitizing question prompts in '%s'...", q_table)
        # ARIO
        res_p1 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET prompt = REPLACE(
                    prompt,
                    'Using Klein''s 4-step ARIO SkillBuilder decision tree, how do you determine which side of an acid-base equilibrium is favored?',
                    'Using the 4-step ARIO decision tree, how do you determine which side of an acid-base equilibrium is favored?'
                )
                WHERE prompt LIKE '%Klein%ARIO%'
            """)
        )
        updated_count += res_p1.rowcount if res_p1.rowcount != -1 else 0

        # Carbocation stability
        res_p2 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET prompt = REPLACE(
                    prompt,
                    'Following Klein''s carbocation stability guidelines, which factor provides greater stabilization to a positive charge?',
                    'Following fundamental carbocation stability guidelines, which factor provides greater stabilization to a positive charge?'
                )
                WHERE prompt LIKE '%Klein%carbocation%'
            """)
        )
        updated_count += res_p2.rowcount if res_p2.rowcount != -1 else 0

        # Resonance structures
        res_p3 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET prompt = REPLACE(
                    prompt,
                    'Applying Klein''s rules for drawing resonance structures, which curved-arrow movement is strictly forbidden?',
                    'Applying the fundamental rules for drawing resonance structures, which curved-arrow movement is strictly forbidden?'
                )
                WHERE prompt LIKE '%Klein%resonance%'
            """)
        )
        updated_count += res_p3.rowcount if res_p3.rowcount != -1 else 0

        # Newman projections
        res_p4 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET prompt = REPLACE(
                    prompt,
                    'Under Klein''s conformation analysis protocol, what is the dihedral angle in an anti conformation of butane?',
                    'Under standard conformational analysis protocol, what is the dihedral angle in an anti conformation of butane?'
                )
                WHERE prompt LIKE '%Klein%conformation%'
            """)
        )
        updated_count += res_p4.rowcount if res_p4.rowcount != -1 else 0

        # Chair flips
        res_p5 = conn.execute(
            text(f"""
                UPDATE {q_table}
                SET prompt = REPLACE(
                    prompt,
                    'In Klein''s SkillBuilder for substituted cyclohexanes, how do axial and equatorial substituents change upon a chair flip?',
                    'In the SkillBuilder for substituted cyclohexanes, how do axial and equatorial substituents change upon a chair flip?'
                )
                WHERE prompt LIKE '%Klein%chair flip%'
            """)
        )
        updated_count += res_p5.rowcount if res_p5.rowcount != -1 else 0

        # Chapter XX SkillBuilder algorithms (Chapters 02 to 27)
        for ch in range(1, 35):
            ch_str = f"{ch:02d}"
            res_pch = conn.execute(
                text(f"""
                    UPDATE {q_table}
                    SET prompt = REPLACE(
                        prompt,
                        'In Klein''s 3-step SkillBuilder algorithm for Chapter {ch_str} problems, what is the objective of Step 1: Analyze the Problem?',
                        'In the 3-step SkillBuilder algorithm for Chapter {ch_str} problems, what is the objective of Step 1: Analyze the Problem?'
                    )
                    WHERE prompt LIKE '%Klein%Chapter {ch_str}%'
                """)
            )
            updated_count += res_pch.rowcount if res_pch.rowcount != -1 else 0

        # 3. Any remaining questions with terms in prompt or explanation
        remaining = conn.execute(
            text(f"""
                SELECT id, prompt, explanation FROM {q_table}
                WHERE LOWER(prompt) LIKE '%klein%' OR LOWER(explanation) LIKE '%klein%'
                   OR LOWER(prompt) LIKE '%david%' OR LOWER(explanation) LIKE '%david%'
                   OR LOWER(prompt) LIKE '%mcmurry%' OR LOWER(explanation) LIKE '%mcmurry%'
                   OR LOWER(prompt) LIKE '%mccurry%' OR LOWER(explanation) LIKE '%mccurry%'
            """)
        ).fetchall()

        if remaining:
            logger.info("Found %d remaining rows requiring general regex cleanup...", len(remaining))
            for row_id, prompt, explanation in remaining:
                new_prompt = re.sub(r"In Klein\x27s\s+", "In the ", prompt) if prompt else prompt
                new_prompt = re.sub(r"Klein\x27s\s+", "the ", new_prompt) if new_prompt else new_prompt
                new_explanation = re.sub(r"In David Klein\x27s Organic Chemistry,\s*", "In organic chemistry, ", explanation) if explanation else explanation
                new_explanation = re.sub(r"David Klein\x27s\s+", "", new_explanation) if new_explanation else new_explanation
                new_explanation = re.sub(r"David Klein\s+", "", new_explanation) if new_explanation else new_explanation
                new_explanation = re.sub(r"John McMurry\s*", "", new_explanation) if new_explanation else new_explanation

                conn.execute(
                    text(f"UPDATE {q_table} SET prompt = :prompt, explanation = :explanation WHERE id = :id"),
                    {"prompt": new_prompt, "explanation": new_explanation, "id": row_id}
                )
                updated_count += 1

        # 4. Sanitize tracks if applicable
        if t_table in existing:
            conn.execute(
                text(f"""
                    UPDATE {t_table}
                    SET title = REPLACE(title, 'Klein Organic Chemistry', 'Comprehensive Organic Chemistry')
                    WHERE title LIKE '%Klein%'
                """)
            )

        # 5. Verification query
        verify_count = conn.execute(
            text(f"""
                SELECT COUNT(*) FROM {q_table}
                WHERE LOWER(prompt) LIKE '%klein%' OR LOWER(explanation) LIKE '%klein%'
                   OR LOWER(prompt) LIKE '%david%' OR LOWER(explanation) LIKE '%david%'
                   OR LOWER(prompt) LIKE '%mcmurry%' OR LOWER(explanation) LIKE '%mcmurry%'
                   OR LOWER(prompt) LIKE '%mccurry%' OR LOWER(explanation) LIKE '%mccurry%'
            """)
        ).scalar()

        logger.info("Sanitization complete. Remaining matching records in database: %d", verify_count)

    return updated_count


def main():
    parser = argparse.ArgumentParser(description="Sanitize author/textbook references in DB.")
    parser.add_argument("--db-url", type=str, default=settings.database_url, help="Target database connection URL")
    args = parser.parse_args()

    sanitize_database(args.db_url)


if __name__ == "__main__":
    main()
