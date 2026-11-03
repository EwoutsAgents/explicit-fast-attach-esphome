"""Prepare a patched copy of ESP-IDF's `openthread` component for one variant group.

Shared by the `thread_openthread_source` ESPHome component (which prepares the copy
inside each project's own build folder during `esphome compile`) and by
`scripts/prepare_ot_overrides.py` (maintainer tool, prepares into build/ot-override/).

Nothing here modifies ESP-IDF itself: the source component is only read, the patches
are applied to a copy.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

try:  # POSIX (Linux, macOS, the Home Assistant add-on); no locking elsewhere
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

# ---- Tested versions (one place) --------------------------------------------------
TESTED_ESPHOME_SERIES = "2026.10"           # any 2026.10.x
ESP_IDF_VERSION = "5.5.6"
OPENTHREAD_BASE = "43cc05a9bcf780bd758bad53d897e2d88cf8cb75"
# sha256 over OpenThread src/ and include/ (paths + contents) at OPENTHREAD_BASE;
# identical for the upstream commit and ESPHome's ESP-IDF 5.5.6 download.
PRISTINE_CONTENT_SHA256 = "a23aa79fe9dcd0e839f05fc17a58874392bfc0702f731e0e56a3490d31def37b"
FAST_ATTACH_PR = {"number": 13121, "head": "2b274799817da3f26207edcb7bea0dbc3894c910"}

# components/thread_openthread_source/ot_override.py -> repository root
REPO_ROOT = Path(__file__).resolve().parents[2]
PATCHES_DIR = REPO_ROOT / "patches"

PREFERRED_PARENT_DEFINE = "OPENTHREAD_CONFIG_EXPERIMENTAL_PREFERRED_PARENT_ENABLE"
MTD_CONFIG = "private_include/openthread-core-esp32x-mtd-config.h"

# group -> patches applied in order, defines appended to the MTD config, features provided
GROUPS: dict[str, dict] = {
    "delay-log": {
        "patches": ["canonical/parent-response-delay-diagnostic.patch"],
        "mtd_defines": {},
        "features": ["parent_response_delay_log"],
    },
    "explicit-attach": {
        "patches": ["canonical/openthread-preferred-parent-controller.patch"],
        "mtd_defines": {PREFERRED_PARENT_DEFINE: 1},
        "features": ["preferred_parent"],
    },
    "fast-attach": {
        "patches": ["fast-attach/openthread-fast-attach-pr13121.patch"],
        "mtd_defines": {},
        "features": ["fast_attach", "parent_response_delay_log"],
    },
    "explicit-fast-attach": {
        "patches": ["fast-attach-ucast-1/openthread-fast-attach-pr13121.patch",
                    "fast-attach-ucast-1/openthread-preferred-parent-controller.patch",
                    "fast-attach-ucast-1/fast-attach-ucast-1-delta.patch"],
        "mtd_defines": {PREFERRED_PARENT_DEFINE: 1},
        "features": ["fast_attach", "preferred_parent", "fast_attach_ucast_1"],
    },
    "fast-attach-ucast-32": {
        "patches": ["fast-attach-ucast-32/openthread-fast-attach-pr13121.patch",
                    "fast-attach-ucast-32/openthread-preferred-parent-controller.patch",
                    "fast-attach-ucast-32/fast-attach-ucast-32-delta.patch"],
        "mtd_defines": {PREFERRED_PARENT_DEFINE: 1},
        "features": ["fast_attach", "preferred_parent", "fast_attach_ucast_32"],
    },
}


class OverrideError(Exception):
    """A patched OpenThread copy cannot be prepared; the message says why and how to fix it."""


def content_sha256(openthread_root: Path) -> str:
    h = hashlib.sha256()
    for sub in ("src", "include"):
        for p in sorted((openthread_root / sub).rglob("*")):
            if p.is_file():
                h.update(p.relative_to(openthread_root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def patch_hashes(group: str) -> list[dict]:
    if not PATCHES_DIR.is_dir():
        raise OverrideError(
            f"Patch folder not found at {PATCHES_DIR}. Use the component from the full "
            "explicit-fast-attach-dev repository (a git external component includes it)."
        )
    out = []
    for rel in GROUPS[group]["patches"]:
        patch = PATCHES_DIR / rel
        if not patch.is_file():
            raise OverrideError(f"Patch file missing: {patch}")
        out.append({"path": f"patches/{rel}", "sha256": file_sha256(patch)})
    return out


def verify_source(source_component: Path) -> None:
    ot_root = source_component / "openthread"
    if not (ot_root / "src").is_dir():
        raise OverrideError(f"ESP-IDF openthread component not found at {source_component}")
    actual = content_sha256(ot_root)
    if actual != PRISTINE_CONTENT_SHA256:
        raise OverrideError(
            f"{source_component} is not unmodified OpenThread {OPENTHREAD_BASE[:8]} "
            f"(content sha256 {actual[:16]}…). The patches only fit that revision (ESP-IDF {ESP_IDF_VERSION})."
        )


def tree_manifest_sha256(component: Path) -> str:
    """sha256 over every file's relative path and size in the copied component.

    Cheap enough to check on every compile, and it catches a copy that lost files
    (for example `linker.lf`) after it was prepared.
    """
    h = hashlib.sha256()
    for root, dirs, files in os.walk(component):
        dirs.sort()
        for name in sorted(files):
            path = Path(root, name)
            h.update(f"{path.relative_to(component).as_posix()}\0{path.stat().st_size}\0".encode())
    return h.hexdigest()


def is_current(target_dir: Path, group: str) -> bool:
    """True if `target_dir` holds a complete override for this group from the current patches."""
    try:
        provenance = json.loads((target_dir / "PROVENANCE.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not (
        provenance.get("group") == group
        and provenance.get("openthread_base_content_sha256") == PRISTINE_CONTENT_SHA256
        and provenance.get("patches") == patch_hashes(group)
        and provenance.get("mtd_config_defines") == GROUPS[group]["mtd_defines"]
        and (target_dir / "openthread" / "CMakeLists.txt").is_file()
    ):
        return False
    try:
        return provenance.get("tree_manifest_sha256") == tree_manifest_sha256(target_dir / "openthread")
    except OSError:
        return False


@contextlib.contextmanager
def _lock(target_dir: Path):
    """Serialise preparation of one group's copy between concurrent compiles."""
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:
        yield
        return
    with open(target_dir.parent / f".{target_dir.name}.lock", "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def ensure(group: str, source_component: Path, target_dir: Path, *, repo_revision: dict | None = None) -> tuple[dict, bool]:
    """Return (provenance, prepared_now): reuse a complete copy, else prepare one. Concurrency-safe."""
    with _lock(target_dir):
        if is_current(target_dir, group):
            return json.loads((target_dir / "PROVENANCE.json").read_text(encoding="utf-8")), False
        return prepare(group, source_component, target_dir, repo_revision=repo_revision), True


def _git_apply(ot_root: Path, patch: Path) -> None:
    git = shutil.which("git")
    if git is None:
        raise OverrideError("`git` is required to apply the OpenThread patches but was not found on PATH.")
    env = {"GIT_CEILING_DIRECTORIES": str(ot_root.parent), "PATH": str(Path(git).parent)}
    for args in (["--check"], []):  # strict: no fuzz, exact context
        proc = subprocess.run([git, "apply", *args, str(patch)], cwd=ot_root, capture_output=True, text=True, env=env)
        if proc.returncode != 0:
            raise OverrideError(f"{patch.name} does not apply to OpenThread {OPENTHREAD_BASE[:8]}:\n{proc.stderr}")


def prepare(group: str, source_component: Path, target_dir: Path, *, repo_revision: dict | None = None) -> dict:
    """(Re)create `target_dir`/openthread as the patched copy for `group`; return its provenance."""
    if group not in GROUPS:
        raise OverrideError(f"Unknown OpenThread group '{group}'. Known: {', '.join(GROUPS)}")
    spec = GROUPS[group]
    applied = patch_hashes(group)
    verify_source(source_component)

    # Build the copy next to the target and swap it in at the end, so a build never
    # sees a half-written or half-deleted folder.
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = target_dir.parent / f".{target_dir.name}.staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir()
    component = staging / "openthread"
    shutil.copytree(source_component, component, symlinks=True)
    # ESP-IDF's tarball keeps submodule `.git` pointer files whose targets don't exist;
    # drop them from the copy so `git apply` runs as a plain, repository-less patcher.
    for gitfile in component.rglob(".git"):
        if gitfile.is_file():
            gitfile.unlink()

    ot_root = component / "openthread"
    for rel in spec["patches"]:
        _git_apply(ot_root, PATCHES_DIR / rel)

    if spec["mtd_defines"]:
        config = component / MTD_CONFIG
        lines = ["", "// Added by thread_openthread_source (ot_override.py)"]
        for name, value in spec["mtd_defines"].items():
            lines += [f"#undef {name}", f"#define {name} {value}"]
        config.write_text(config.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")

    provenance = {
        "group": group,
        "features": spec["features"],
        "esp_idf_version": ESP_IDF_VERSION,
        "openthread_base": OPENTHREAD_BASE,
        "openthread_base_content_sha256": PRISTINE_CONTENT_SHA256,
        "fast_attach_pr": FAST_ATTACH_PR if "fast_attach" in spec["features"] else None,
        "patches": applied,
        "mtd_config_defines": spec["mtd_defines"],
        "patched_content_sha256": content_sha256(ot_root),
        "tree_manifest_sha256": tree_manifest_sha256(component),
        "source_component": str(source_component),
        "repository": repo_revision,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    (staging / "PROVENANCE.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

    retired = None
    if target_dir.exists():
        retired = target_dir.parent / f".{target_dir.name}.retired-{os.getpid()}"
        os.replace(target_dir, retired)
    os.replace(staging, target_dir)
    if retired is not None:
        shutil.rmtree(retired, ignore_errors=True)
    return provenance
