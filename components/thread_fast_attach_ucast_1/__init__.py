"""ESPHome configuration glue for the Thread preferred-parent component.

This module validates YAML options and wires the generated C++ component into the
ESPHome codegen pipeline. The OpenThread patch set (Fast Attach PR, controller and
this variant's delta) is applied by scripts/prepare_ot_overrides.py and selected with
`thread_openthread_source` (group explicit-fast-attach); FINAL_VALIDATE_SCHEMA checks it.
"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["openthread"]
AUTO_LOAD = ["thread_openthread_source"]

thread_fast_attach_ucast_1_ns = cg.esphome_ns.namespace("thread_fast_attach_ucast_1")
ThreadFastAttachUcast1Component = thread_fast_attach_ucast_1_ns.class_(
    "ThreadFastAttachUcast1Component", cg.Component
)

# Configuration keys exposed in YAML.
CONF_PARENT_RLOC = "parent_rloc"
CONF_PARENT_EXTADDR = "parent_extaddr"
CONF_MAX_ATTEMPTS = "max_attempts"
CONF_RETRY_INTERVAL = "retry_interval"
CONF_SELECTED_ATTACH_TIMEOUT = "selected_attach_timeout"
CONF_REQUIRE_SELECTED_PARENT_HOOK = "require_selected_parent_hook"
CONF_LOG_PARENT_RESPONSES = "log_parent_responses"



def validate_rloc16(value):
    """Validate an RLOC16 as either 0x1234 / 1234 hex string or integer."""
    if isinstance(value, int):
        return cv.int_range(min=0x0000, max=0xFFFD)(value)

    value = cv.string_strict(value).strip().lower()
    if value.startswith("0x"):
        value = value[2:]

    try:
        parsed = int(value, 16)
    except ValueError as err:
        raise cv.Invalid("RLOC16 must be a 16-bit hex value, e.g. 0x5800 or 5800") from err

    return cv.int_range(min=0x0000, max=0xFFFD)(parsed)


def validate_extaddr(value):
    """Validate and normalize an IEEE 802.15.4 extended address.

    Accepted formats:
      * 00124b0001abcdef
      * 00:12:4b:00:01:ab:cd:ef
      * 00-12-4b-00-01-ab-cd-ef
      * 0x00124b0001abcdef
    """
    value = cv.string_strict(value).strip().lower()
    if value.startswith("0x"):
        value = value[2:]

    compact = "".join(ch for ch in value if ch not in ":- _")
    if len(compact) != 16:
        raise cv.Invalid("Extended address must contain exactly 8 bytes / 16 hex digits")

    try:
        int(compact, 16)
    except ValueError as err:
        raise cv.Invalid("Extended address must be hexadecimal, e.g. 00124b0001abcdef") from err

    return compact


def validate_identifier(config):
    """Require exactly zero or one preferred-parent identifier fields.

    The component can target a parent by either RLOC16 or extended address, but
    not both at the same time.
    """
    has_rloc = CONF_PARENT_RLOC in config
    has_extaddr = CONF_PARENT_EXTADDR in config
    if has_rloc and has_extaddr:
        raise cv.Invalid("Specify only one of parent_rloc or parent_extaddr")
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(ThreadFastAttachUcast1Component),
            cv.Optional(CONF_PARENT_RLOC): validate_rloc16,
            cv.Optional(CONF_PARENT_EXTADDR): validate_extaddr,
            cv.Optional(CONF_MAX_ATTEMPTS, default=5): cv.int_range(min=1, max=20),
            cv.Optional(CONF_RETRY_INTERVAL, default="8s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_SELECTED_ATTACH_TIMEOUT, default="16s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_REQUIRE_SELECTED_PARENT_HOOK, default=True): cv.boolean,
            cv.Optional(CONF_LOG_PARENT_RESPONSES, default=True): cv.boolean,
        }
    ).extend(cv.COMPONENT_SCHEMA),
    validate_identifier,
)



def FINAL_VALIDATE_SCHEMA(config):
    try:
        from esphome.components.thread_openthread_source import require_features
    except ImportError as err:
        raise cv.Invalid(
            "thread_fast_attach_ucast_1 needs a patched OpenThread: add thread_openthread_source to "
            "external_components and configure `thread_openthread_source: group: explicit-fast-attach`"
        ) from err
    return require_features("thread_fast_attach_ucast_1", "fast_attach_ucast_1")(config)


async def to_code(config):
    """Generate the C++ component."""

    cg.add_build_flag("-DOPENTHREAD_CONFIG_EXPERIMENTAL_PREFERRED_PARENT_ENABLE=1")
    cg.add_build_flag("-DOPENTHREAD_CONFIG_MLE_FAST_ATTACH_ENABLE=1")

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    if CONF_PARENT_RLOC in config:
        cg.add(var.set_parent_rloc16(config[CONF_PARENT_RLOC]))
    if CONF_PARENT_EXTADDR in config:
        cg.add(var.set_parent_extaddr(config[CONF_PARENT_EXTADDR]))

    cg.add(var.set_max_attempts(config[CONF_MAX_ATTEMPTS]))
    cg.add(var.set_retry_interval(config[CONF_RETRY_INTERVAL].total_milliseconds))
    cg.add(var.set_selected_attach_timeout(config[CONF_SELECTED_ATTACH_TIMEOUT].total_milliseconds))
    cg.add(var.set_require_selected_parent_hook(config[CONF_REQUIRE_SELECTED_PARENT_HOOK]))
    cg.add(var.set_log_parent_responses(config[CONF_LOG_PARENT_RESPONSES]))
