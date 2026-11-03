"""Logging-only OpenThread diagnostic: routers log the Parent Response delay they chose.

The source change itself (patches/canonical/parent-response-delay-diagnostic.patch) is
applied by scripts/prepare_ot_overrides.py and selected with
`thread_openthread_source: group: delay-log` (Fast-Attach groups include it as well).
This component only checks that the selected OpenThread provides it.
"""

import esphome.config_validation as cv

DEPENDENCIES = ["openthread"]
AUTO_LOAD = ["thread_openthread_source"]

CONF_ENABLED = "enabled"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_ENABLED, default=True): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)

def FINAL_VALIDATE_SCHEMA(config):
    if not config[CONF_ENABLED]:
        return config
    try:
        from esphome.components.thread_openthread_source import require_features
    except ImportError as err:
        raise cv.Invalid(
            "thread_parent_response_delay_log needs a patched OpenThread: add thread_openthread_source "
            "to external_components and configure `thread_openthread_source: group: delay-log`"
        ) from err
    return require_features("thread_parent_response_delay_log", "parent_response_delay_log")(config)


async def to_code(config):
    """Nothing to generate: the diagnostic lives in the OpenThread override."""
