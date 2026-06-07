from pathlib import Path

from skills_utils.hash import dir_hash, hash_from_map, remote_fingerprint


def test_hash_from_map_deterministic():
    mapping = {"SKILL.md": "abc", "scripts/run.py": "def"}
    assert hash_from_map(mapping) == hash_from_map(dict(reversed(list(mapping.items()))))


def test_remote_fingerprint_matches_dir_hash_for_same_content(tmp_path: Path):
    skill = tmp_path / "pdf"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: pdf\n---\nbody\n", encoding="utf-8")
    (skill / "scripts").mkdir()
    (skill / "scripts" / "run.py").write_text("print('hi')\n", encoding="utf-8")

    file_hashes = {}
    for file_path in sorted(skill.rglob("*")):
        if file_path.is_file():
            rel = file_path.relative_to(skill).as_posix()
            import hashlib

            file_hashes[rel] = hashlib.sha256(file_path.read_bytes()).hexdigest()

    assert remote_fingerprint(file_hashes) == dir_hash(skill)
