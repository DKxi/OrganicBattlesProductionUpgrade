"""
test_boss_images.py - Verifies that all boss asset images specified in
david_klein_organic_chemistry_boss_bestiary.md exist in the 'bosses' directory.
"""

import os
import re
import pytest

BESTIARY_PATH = os.path.join(os.path.dirname(__file__), "..", "AdvancedBestiary.md")
BOSSES_DIR = os.path.join(os.path.dirname(__file__), "..\data\tracks\advanced\", "bosses")


def get_boss_images_from_bestiary(bestiary_path=BESTIARY_PATH):
    """
    Parses david_klein_organic_chemistry_boss_bestiary.md to extract all boss names
    and their corresponding 'Asset Image' filenames.
    Returns a list of dicts: [{'boss': str, 'image': str, 'chapter': str, 'tier': str}]
    """
    assert os.path.isfile(bestiary_path), f"Bestiary file not found at: {bestiary_path}"

    with open(bestiary_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex pattern to extract Chapter, Tier, Boss Name, and Asset Image
    pattern = re.compile(
        r"#### \*\*Tier (\d+): ([^*]+)\*\* \(\*([^*]+)\*\)\s*\n"
        r"(?:- [^\n]+\n)*?"
        r"- \*\*Asset Image:\*\* `([^`]+)`",
        re.MULTILINE
    )

    matches = pattern.findall(content)
    boss_list = []
    for tier, boss_name, role, asset_img in matches:
        boss_list.append({
            "boss": boss_name.strip(),
            "tier": tier.strip(),
            "role": role.strip(),
            "image": asset_img.strip()
        })

    return boss_list


BOSS_ENTRIES = get_boss_images_from_bestiary()


def test_bosses_folder_exists():
    """Verify that the 'bosses' directory exists in the workspace."""
    assert os.path.isdir(BOSSES_DIR), f"Bosses directory '{BOSSES_DIR}' does not exist."


def test_bestiary_boss_count():
    """Verify that all 135 bosses were successfully parsed from the bestiary."""
    assert len(BOSS_ENTRIES) == 135, f"Expected 135 bosses in bestiary, found {len(BOSS_ENTRIES)}."


def test_all_boss_images_exist():
    """
    Master check: Verifies all 135 boss asset images exist in the bosses/ folder.
    Reports all missing files and near-match suggestions in a single detailed assertion error.
    """
    assert os.path.isdir(BOSSES_DIR), f"Bosses directory '{BOSSES_DIR}' not found."
    existing_files = set(os.listdir(BOSSES_DIR))

    missing = []
    near_matches = []

    for entry in BOSS_ENTRIES:
        img = entry["image"]
        boss = entry["boss"]
        if img in existing_files:
            continue

        # Check for common slug variations (e.g. 13- vs 1-3-, hckel vs huckel)
        alt_slug = (
            img.replace("13-", "1-3-")
               .replace("14-", "1-4-")
               .replace("hckel", "huckel")
        )
        if alt_slug in existing_files:
            near_matches.append(f"  - '{boss}': expected '{img}', but found '{alt_slug}' in bosses/")
        else:
            missing.append(f"  - '{boss}': '{img}' not found in bosses/")

    error_messages = []
    if near_matches:
        error_messages.append(
            f"Found {len(near_matches)} boss image(s) with filename discrepancies:\n" + "\n".join(near_matches)
        )
    if missing:
        error_messages.append(
            f"Found {len(missing)} boss image(s) completely missing from bosses/:\n" + "\n".join(missing)
        )

    assert not error_messages, "\n\n".join(error_messages)


@pytest.mark.parametrize("entry", BOSS_ENTRIES, ids=lambda e: e["boss"])
def test_individual_boss_image(entry):
    """
    Tests each individual boss asset image to verify it exists and is non-empty.
    """
    boss_name = entry["boss"]
    img_name = entry["image"]
    img_path = os.path.join(BOSSES_DIR, img_name)

    # Check if file exists under exact name or known slug variant
    alt_slug = (
        img_name.replace("13-", "1-3-")
                .replace("14-", "1-4-")
                .replace("hckel", "huckel")
    )
    alt_path = os.path.join(BOSSES_DIR, alt_slug)

    if not os.path.isfile(img_path) and os.path.isfile(alt_path):
        pytest.fail(
            f"Boss '{boss_name}' asset image mismatch: expected '{img_name}', but '{alt_slug}' exists in bosses/."
        )

    assert os.path.isfile(img_path), (
        f"Boss image missing: '{img_name}' for '{boss_name}' (Tier {entry['tier']}) does not exist in {BOSSES_DIR}."
    )
    assert os.path.getsize(img_path) > 0, (
        f"Boss image '{img_name}' for '{boss_name}' is empty (0 bytes)."
    )


if __name__ == "__main__":
    print("=" * 70)
    print("🔍 VERIFYING BOSS ASSET IMAGES AGAINST BESTIARY")
    print("=" * 70)

    bosses = get_boss_images_from_bestiary()
    print(f"📋 Found {len(bosses)} bosses in {os.path.basename(BESTIARY_PATH)}")

    if not os.path.isdir(BOSSES_DIR):
        print(f"❌ Bosses directory not found: {BOSSES_DIR}")
        exit(1)

    existing = set(os.listdir(BOSSES_DIR))
    print(f"📁 Found {len(existing)} files in bosses/ folder\n")

    exact = []
    near = []
    missing = []

    for b in bosses:
        img = b["image"]
        boss_name = b["boss"]
        if img in existing:
            exact.append((boss_name, img))
        else:
            alt = img.replace("13-", "1-3-").replace("14-", "1-4-").replace("hckel", "huckel")
            if alt in existing:
                near.append((boss_name, img, alt))
            else:
                missing.append((boss_name, img))

    print(f"✅ Exact Matches:     {len(exact)} / {len(bosses)}")
    print(f"⚠️  Filename Variance: {len(near)} / {len(bosses)}")
    print(f"❌ Completely Missing:{len(missing)} / {len(bosses)}")

    if near:
        print("\n⚠️  Filename Variances:")
        for name, exp, actual in near:
            print(f"   • {name}: Bestiary='{exp}' vs Disk='{actual}'")

    if missing:
        print("\n❌ Missing Files:")
        for name, exp in missing:
            print(f"   • {name}: '{exp}'")

    print("=" * 70)
    if not near and not missing:
        print("🎉 ALL 135 BOSS IMAGES VERIFIED SUCCESSFULLY!")
    else:
        print(f"Summary: {len(exact)} valid, {len(near)} name variance, {len(missing)} missing.")
