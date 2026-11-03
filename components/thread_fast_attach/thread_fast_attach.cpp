#include "thread_fast_attach.h"

#include "esphome/components/openthread/openthread.h"
#include "esphome/core/log.h"

#include <openthread/thread.h>

// PlatformIO scans public headers before the post-resolution patch action runs,
// so declare the two PR #13121 APIs for this translation unit as well.
extern "C" otError otThreadSetFastAttachEnabled(otInstance *aInstance, bool aEnabled);
extern "C" bool otThreadIsFastAttachEnabled(otInstance *aInstance);

namespace esphome::thread_fast_attach {

static const char *const TAG = "thread_fast_attach";

void ThreadFastAttachComponent::setup() {
  ESP_LOGI(TAG, "FAST_ATTACH variant=fast-attach compile_enabled=%d arm_after_parent_loss=%d",
           OPENTHREAD_CONFIG_MLE_FAST_ATTACH_ENABLE, this->arm_after_parent_loss_);
}

void ThreadFastAttachComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "Thread Fast Attach (OpenThread PR #13121 backport)");
  ESP_LOGCONFIG(TAG, "  Arm after parent loss: %s", YESNO(this->arm_after_parent_loss_));
}

void ThreadFastAttachComponent::loop() {
  if (!this->arm_after_parent_loss_)
    return;

  auto lock = esphome::openthread::InstanceLock::try_acquire(0);
  if (!lock)
    return;

  otInstance *instance = lock.get_instance();
  const otDeviceRole role = otThreadGetDeviceRole(instance);
  if (role >= OT_DEVICE_ROLE_CHILD) {
    this->observed_attached_ = true;
    this->detach_handled_ = false;
    return;
  }

  if (role != OT_DEVICE_ROLE_DETACHED || !this->observed_attached_ || this->detach_handled_)
    return;

  const otError error = otThreadSetFastAttachEnabled(instance, true);
  const bool enabled = otThreadIsFastAttachEnabled(instance);
  this->detach_handled_ = true;
  ESP_LOGI(TAG, "FAST_ATTACH event=arm_after_detach api_error=%d enabled=%d", error, enabled);
  if (error != OT_ERROR_NONE || !enabled)
    this->status_set_error(LOG_STR("Fast Attach re-arm failed"));
}

}  // namespace esphome::thread_fast_attach
