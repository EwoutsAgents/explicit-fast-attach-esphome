"""Build this firmware against a patched OpenThread, prepared automatically.

During `esphome compile` this component copies ESP-IDF's `openthread` component into
the project's own build folder (`.esphome/build/<device>/ot-override/<group>/`), applies
the variant group's patches from this repository's `patches/` folder, and registers the
copy as a local ESP-IDF component named `openthread` (`esp32.add_idf_component`), which
takes precedence over the built-in one. ESP-IDF itself is only read, never modified, so
devices that do not use this component build with an unmodified OpenThread.

The group is inferred from the feature components in the config, or set explicitly:

    thread_openthread_source:
      group: explicit-attach        # optional

The patches only fit OpenThread 43cc05a9 (ESP-IDF 5.5.6) and the components are tested
with ESPHome 2026.10.x; other versions are rejected during config validation.

(Registering the copy through EXTRA_COMPONENT_DIRS does not work: on rebuilds ESPHome
derives its sources' REQUIRES from components under ESP-IDF's own folder only, drops
`openthread` and loses the OpenThread include paths.)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
import esphome.final_validate as fv
from esphome.components.esp32 import add_idf_component
from esphome.const import CONF_ID, __version__ as ESPHOME_VERSION
from esphome.core import CORE, EsphomeError

from . import ot_override  # plain module, also used by scripts/prepare_ot_overrides.py

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ["openthread"]
DOMAIN = "thread_openthread_source"

CONF_GROUP = "group"
CONF_OVERRIDE_ROOT = "override_root"
CONF_ALLOW_UNTESTED_ESPHOME = "allow_untested_esphome"

# Feature component -> group it needs (used when `group:` is omitted).
GROUP_FOR_COMPONENT = {
    "thread_fast_attach_ucast_1": "explicit-fast-attach",
    "thread_fast_attach_ucast_32": "fast-attach-ucast-32",
    "thread_fast_attach": "fast-attach",
    "thread_preferred_parent": "explicit-attach",
}

thread_openthread_source_ns = cg.esphome_ns.namespace("thread_openthread_source")
ThreadOpenThreadSource = thread_openthread_source_ns.class_("ThreadOpenThreadSource", cg.Component)


def _check_esphome_version(config):
    series = ".".join(ESPHOME_VERSION.split(".")[:2])
    if series != ot_override.TESTED_ESPHOME_SERIES:
        message = (
            f"{DOMAIN} is tested with ESPHome {ot_override.TESTED_ESPHOME_SERIES}.x, but this is ESPHome "
            f"{ESPHOME_VERSION}. Install esphome=={ot_override.TESTED_ESPHOME_SERIES}.* or use a release of "
            "this component made for your ESPHome version."
        )
        if not config[CONF_ALLOW_UNTESTED_ESPHOME]:
            raise cv.Invalid(message + f" (Set `{CONF_ALLOW_UNTESTED_ESPHOME}: true` to try anyway.)")
        _LOGGER.warning("%s Continuing because %s is set.", message, CONF_ALLOW_UNTESTED_ESPHOME)
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(ThreadOpenThreadSource),
            cv.Optional(CONF_GROUP): cv.one_of(*ot_override.GROUPS, lower=True),
            cv.Optional(CONF_OVERRIDE_ROOT): cv.string_strict,
            cv.Optional(CONF_ALLOW_UNTESTED_ESPHOME, default=False): cv.boolean,
        }
    ).extend(cv.COMPONENT_SCHEMA),
    _check_esphome_version,
)


def resolve_group(full_config: dict) -> str:
    """The group from `thread_openthread_source: group:`, or inferred from the feature components."""
    source = full_config.get(DOMAIN) or {}
    if source.get(CONF_GROUP):
        return source[CONF_GROUP]
    wanted = {GROUP_FOR_COMPONENT[c] for c in GROUP_FOR_COMPONENT if c in full_config}
    if len(wanted) > 1:
        raise cv.Invalid(
            f"These components need different patched OpenThreads ({', '.join(sorted(wanted))}); "
            "a firmware can use only one. Keep one of them."
        )
    if wanted:
        return wanted.pop()
    if "thread_parent_response_delay_log" in full_config:
        return "delay-log"
    raise cv.Invalid(f"Set `{DOMAIN}: group:` (one of {', '.join(ot_override.GROUPS)}).")


def _final_validate(config):
    resolve_group(fv.full_config.get())
    idf_version = str(CORE.data.get("esp32", {}).get("idf_version", ""))
    if idf_version != ot_override.ESP_IDF_VERSION:
        raise cv.Invalid(
            f"{DOMAIN} needs ESP-IDF {ot_override.ESP_IDF_VERSION} (the patches only fit OpenThread "
            f"{ot_override.OPENTHREAD_BASE[:8]}), but this firmware uses ESP-IDF {idf_version or 'unknown'}. "
            f"Set `esp32: framework: version: {ot_override.ESP_IDF_VERSION}`."
        )
    if not CORE.using_toolchain_esp_idf:
        raise cv.Invalid(
            f"{DOMAIN} needs ESPHome's native ESP-IDF toolchain. Remove `esp32: toolchain: platformio` "
            "(or set `toolchain: esp-idf`)."
        )
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


def require_features(component: str, *features: str):
    """FINAL_VALIDATE helper for feature components: the group must provide `features`."""

    def validator(config):
        full_config = fv.full_config.get()
        if DOMAIN not in full_config:
            raise cv.Invalid(
                f"{component} needs a patched OpenThread: add {DOMAIN} to the external_components "
                f"`components:` list and add `{DOMAIN}:` to the config"
            )
        group = resolve_group(full_config)
        provided = ot_override.GROUPS[group]["features"]
        missing = [f for f in features if f not in provided]
        if missing:
            raise cv.Invalid(
                f"{component} needs OpenThread feature(s) {missing}, but {DOMAIN} group '{group}' "
                f"provides {provided}"
            )
        return config

    return validator


def _esp_idf_openthread_component() -> Path:
    # The ESP-IDF this build uses: the user's IDF_PATH, or ESPHome's managed install
    # (downloaded on first use, limited to the configured chip, like ESPHome does itself).
    from esphome.espidf.toolchain import _get_idf_path

    return Path(_get_idf_path(ot_override.ESP_IDF_VERSION)) / "components" / "openthread"


def _prepare_override(group: str, root: str | None) -> tuple[Path, dict]:
    if root:  # pre-prepared copy (scripts/prepare_ot_overrides.py)
        group_dir = Path(root) / group
        try:
            provenance = json.loads((group_dir / "PROVENANCE.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as err:
            raise EsphomeError(f"No prepared OpenThread for group '{group}' in {root}: {err}") from err
        return group_dir, provenance

    group_dir = Path(CORE.relative_build_path("ot-override")) / group
    try:
        if ot_override.is_current(group_dir, group):
            provenance = json.loads((group_dir / "PROVENANCE.json").read_text(encoding="utf-8"))
        else:
            source = _esp_idf_openthread_component()
            _LOGGER.info("Preparing patched OpenThread (group %s) from %s", group, source)
            provenance = ot_override.prepare(group, source, group_dir)
    except ot_override.OverrideError as err:
        raise EsphomeError(str(err)) from err
    return group_dir, provenance


async def to_code(config):
    group = resolve_group(CORE.config)
    group_dir, provenance = _prepare_override(group, config.get(CONF_OVERRIDE_ROOT))
    add_idf_component(name="openthread", path=str((group_dir / "openthread").resolve()))

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(
        var.set_info(
            provenance["group"],
            provenance["esp_idf_version"],
            provenance["openthread_base"][:12],
            provenance["patched_content_sha256"][:16],
        )
    )
