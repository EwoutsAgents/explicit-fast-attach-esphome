#include "thread_openthread_source.h"

#include <openthread/link.h>

#include "esphome/components/openthread/openthread.h"
#include "esphome/core/log.h"

namespace esphome::thread_openthread_source {

static const char *const TAG = "thread_openthread_source";
static const uint32_t IDENTITY_INTERVAL_MS = 30000;

void ThreadOpenThreadSource::log_source_() const {
  ESP_LOGI(TAG, "OT_SOURCE group=%s esp_idf=%s openthread_base=%s patched_sha256=%s", this->group_, this->esp_idf_,
           this->openthread_base_, this->patched_sha256_);
}

void ThreadOpenThreadSource::log_identity_() {
  this->log_source_();
  // Never block the main loop for the OpenThread lock; skip this round instead.
  auto lock = esphome::openthread::InstanceLock::try_acquire(0);
  if (!lock) {
    return;
  }
  const otExtAddress *ext = otLinkGetExtendedAddress(lock.get_instance());
  if (ext == nullptr) {
    return;
  }
  char hex[2 * OT_EXT_ADDRESS_SIZE + 1];
  for (size_t i = 0; i < OT_EXT_ADDRESS_SIZE; i++) {
    snprintf(hex + 2 * i, 3, "%02x", ext->m8[i]);
  }
  // Same format as the configs' text_sensor line; the test runners parse it.
  ESP_LOGI(TAG, "Own Thread ExtAddr: %s", hex);
}

void ThreadOpenThreadSource::setup() {
  this->log_source_();
  this->set_interval("identity", IDENTITY_INTERVAL_MS, [this]() { this->log_identity_(); });
}

void ThreadOpenThreadSource::dump_config() { this->log_source_(); }

}  // namespace esphome::thread_openthread_source
