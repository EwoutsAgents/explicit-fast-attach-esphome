"""Isolated ESPHome integration for OpenThread PR #13121 Fast Attach.

The PR backport is applied by scripts/prepare_ot_overrides.py and selected with
`thread_openthread_source` (group fast-attach); FINAL_VALIDATE_SCHEMA checks it.
"""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["openthread"]
AUTO_LOAD = ["thread_openthread_source"]

thread_fast_attach_ns = cg.esphome_ns.namespace("thread_fast_attach")
ThreadFastAttachComponent = thread_fast_attach_ns.class_("ThreadFastAttachComponent", cg.Component)

CONF_ARM_AFTER_PARENT_LOSS = "arm_after_parent_loss"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(ThreadFastAttachComponent),
        cv.Optional(CONF_ARM_AFTER_PARENT_LOSS, default=False): cv.boolean,
    }
).extend(cv.COMPONENT_SCHEMA)



def FINAL_VALIDATE_SCHEMA(config):
    try:
        from esphome.components.thread_openthread_source import require_features
    except ImportError as err:
        raise cv.Invalid(
            "thread_fast_attach needs a patched OpenThread: add thread_openthread_source to "
            "external_components and configure `thread_openthread_source: group: fast-attach`"
        ) from err
    return require_features("thread_fast_attach", "fast_attach")(config)


async def to_code(config):
    cg.add_build_flag("-DOPENTHREAD_CONFIG_MLE_FAST_ATTACH_ENABLE=1")

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_arm_after_parent_loss(config[CONF_ARM_AFTER_PARENT_LOSS]))
