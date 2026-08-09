import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "verify_rc1_review.py"
SPEC = importlib.util.spec_from_file_location("verify_rc1_review", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)

REQUIRED_FILES = review.REQUIRED_FILES
ROOT = review.ROOT
included_files = review.included_files
tree_manifest = review.tree_manifest
verify_no_generated_artifacts = review.verify_no_generated_artifacts
verify_readme = review.verify_readme
verify_required_files = review.verify_required_files


def test_complete_tree_manifest_is_deterministic():
    files = included_files()
    first = tree_manifest(files)
    second = tree_manifest(files)
    assert first == second
    assert first[1] == len(files)


def test_required_review_and_stage_files_are_present():
    files = included_files()
    verify_required_files(files)
    assert REQUIRED_FILES <= {path.as_posix() for path in files}


def test_generated_artifacts_are_excluded():
    files = included_files()
    verify_no_generated_artifacts(files)
    assert all("__pycache__" not in path.parts for path in files)
    assert all(path.suffix not in {".pyc", ".pyo"} for path in files)


def test_readme_states_current_scope_and_rc1_disposition():
    verify_readme()
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Stages 0–10" in text
    assert "RC1 is therefore not approved for freezing" in text


def test_manifest_paths_are_sorted_and_relative():
    files = included_files()
    assert files == sorted(files, key=lambda item: item.as_posix())
    assert all(not path.is_absolute() for path in files)


def test_review_verifier_is_inside_its_own_manifest():
    names = {path.as_posix() for path in included_files()}
    assert "tools/verify_rc1_review.py" in names
    assert "tests/test_rc1_review.py" in names
