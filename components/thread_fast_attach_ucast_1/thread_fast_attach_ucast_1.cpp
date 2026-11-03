#include "thread_fast_attach_ucast_1.h"

#include "esphome/core/log.h"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace esphome {
namespace thread_fast_attach_ucast_1 {

static const char *const TAG = "thread_fast_attach_ucast_1";

void ThreadFastAttachUcast1Component::setup() {
  auto lock = esphome::openthread::InstanceLock::try_acquire(100);
  if (!lock) {
    ESP_LOGE(TAG, "Cannot register OpenThread preferred-parent event callback");
    this->mark_failed();
    return;
  }

  const otError error = otThreadPreferredParentSetCallback(
      lock.get_instance(), &ThreadFastAttachUcast1Component::preferred_parent_callback_, this);
  if (error != OT_ERROR_NONE) {
    ESP_LOGE(TAG, "Cannot register OpenThread preferred-parent event callback: %s", otThreadErrorToString(error));
    this->mark_failed();
  }
}

void ThreadFastAttachUcast1Component::dump_config() {
  ESP_LOGCONFIG(TAG, "Thread Fast Attach unicast 1 (OpenThread-owned controller):");
  ESP_LOGCONFIG(TAG, "  Target: %s", this->target_type_ == TargetType::EXTADDR
                                      ? extaddr_to_string_(this->target_extaddr_).c_str()
                                      : this->target_type_ == TargetType::RLOC16 ? "RLOC16 (resolved from neighbor table)"
                                                                               : "not configured");
  if (this->target_type_ == TargetType::RLOC16) {
    ESP_LOGCONFIG(TAG, "  Target RLOC16: 0x%04x", this->target_rloc16_);
  }
  ESP_LOGCONFIG(TAG, "  Mode: unicast");
  ESP_LOGCONFIG(TAG, "  Max attempts: %u", this->max_attempts_);
  ESP_LOGCONFIG(TAG, "  Retry interval: %u ms", this->retry_interval_ms_);
  ESP_LOGCONFIG(TAG, "  Attach timeout: %u ms", this->attach_timeout_ms_);
}

void ThreadFastAttachUcast1Component::set_parent_rloc16(uint16_t rloc16) {
  this->target_type_ = TargetType::RLOC16;
  this->target_rloc16_ = rloc16;
  this->target_extaddr_ = {};
}

bool ThreadFastAttachUcast1Component::set_parent_rloc16(const std::string &text) {
  uint16_t rloc16;
  if (!parse_rloc16_(text, &rloc16)) {
    ESP_LOGW(TAG, "Invalid preferred-parent RLOC16: %s", text.c_str());
    return false;
  }
  this->set_parent_rloc16(rloc16);
  return true;
}

bool ThreadFastAttachUcast1Component::set_parent_extaddr(const std::string &text) {
  otExtAddress extaddr{};
  if (!parse_extaddr_(text, &extaddr)) {
    ESP_LOGW(TAG, "Invalid preferred-parent extended address: %s", text.c_str());
    return false;
  }
  this->target_type_ = TargetType::EXTADDR;
  this->target_extaddr_ = extaddr;
  this->target_rloc16_ = 0xfffe;
  return true;
}

void ThreadFastAttachUcast1Component::request_switch() {
  auto lock = esphome::openthread::InstanceLock::try_acquire(100);
  if (!lock) {
    ESP_LOGW(TAG, "Cannot acquire OpenThread instance lock");
    return;
  }

  otExtAddress extaddr{};
  if (!this->resolve_target_(lock.get_instance(), &extaddr)) {
    ESP_LOGW(TAG, "Preferred-parent target is missing or its RLOC16 is not in the neighbor table");
    return;
  }

  otThreadPreferredParentConfig config{};
  config.mExtAddress = extaddr;
  config.mMode = OT_THREAD_PREFERRED_PARENT_MODE_UNICAST;
  config.mMaxAttempts = this->max_attempts_;
  config.mFastAttach = true;
  config.mRetryInterval = this->retry_interval_ms_;
  config.mAttachTimeout = this->attach_timeout_ms_;

  const otError error = otThreadPreferredParentStart(lock.get_instance(), &config);
  if (error != OT_ERROR_NONE) {
    ESP_LOGW(TAG, "FAST_ATTACH_UCAST_1 event=start_rejected target=%s mode=unicast error=%s",
             extaddr_to_string_(extaddr).c_str(), otThreadErrorToString(error));
  }
}

void ThreadFastAttachUcast1Component::request_switch(uint16_t rloc16) {
  this->set_parent_rloc16(rloc16);
  this->request_switch();
}

void ThreadFastAttachUcast1Component::request_switch(const std::string &extaddr) {
  if (this->set_parent_extaddr(extaddr)) this->request_switch();
}

void ThreadFastAttachUcast1Component::cancel_switch() {
  auto lock = esphome::openthread::InstanceLock::try_acquire(100);
  if (!lock) return;
  const otError error = otThreadPreferredParentCancel(lock.get_instance());
  if (error != OT_ERROR_NONE) ESP_LOGW(TAG, "Preferred-parent cancel failed: %s", otThreadErrorToString(error));
}

void ThreadFastAttachUcast1Component::clear_target() {
  auto lock = esphome::openthread::InstanceLock::try_acquire(100);
  if (lock) {
    otThreadPreferredParentStatus status{};
    otThreadPreferredParentGetStatus(lock.get_instance(), &status);
    if (status.mState != OT_THREAD_PREFERRED_PARENT_STATE_IDLE &&
        status.mState != OT_THREAD_PREFERRED_PARENT_STATE_SUCCEEDED &&
        status.mState != OT_THREAD_PREFERRED_PARENT_STATE_FAILED &&
        status.mState != OT_THREAD_PREFERRED_PARENT_STATE_TIMED_OUT &&
        status.mState != OT_THREAD_PREFERRED_PARENT_STATE_CANCELLED) {
      otThreadPreferredParentCancel(lock.get_instance());
    }
    otThreadPreferredParentClear(lock.get_instance());
  }
  this->target_type_ = TargetType::NONE;
  this->target_extaddr_ = {};
  this->target_rloc16_ = 0xfffe;
}

std::string ThreadFastAttachUcast1Component::current_parent_extaddr() const {
  auto lock = esphome::openthread::InstanceLock::try_acquire(100);
  if (!lock) return {};
  otRouterInfo info{};
  return otThreadGetParentInfo(lock.get_instance(), &info) == OT_ERROR_NONE ? extaddr_to_string_(info.mExtAddress)
                                                                            : std::string{};
}

bool ThreadFastAttachUcast1Component::resolve_target_(otInstance *instance, otExtAddress *extaddr) const {
  if (this->target_type_ == TargetType::EXTADDR) {
    *extaddr = this->target_extaddr_;
    return true;
  }
  if (this->target_type_ != TargetType::RLOC16) return false;

  otNeighborInfoIterator iterator = OT_NEIGHBOR_INFO_ITERATOR_INIT;
  otNeighborInfo neighbor{};
  while (otThreadGetNextNeighborInfo(instance, &iterator, &neighbor) == OT_ERROR_NONE) {
    if (neighbor.mRloc16 == this->target_rloc16_) {
      *extaddr = neighbor.mExtAddress;
      return true;
    }
  }
  return false;
}

void ThreadFastAttachUcast1Component::preferred_parent_callback_(const otThreadPreferredParentEventInfo *info,
                                                                void *context) {
  auto *self = static_cast<ThreadFastAttachUcast1Component *>(context);
  if (info == nullptr || self == nullptr) return;
  const std::string target = extaddr_to_string_(info->mStatus.mExtAddress);
  switch (info->mEvent) {
    case OT_THREAD_PREFERRED_PARENT_EVENT_REQUESTED:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=requested target=%s mode=unicast", target.c_str());
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_PARENT_REQUEST_STARTED:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=parent_request_started attempt=%u/%u", info->mStatus.mAttempt,
               info->mStatus.mMaxAttempts);
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_TARGET_RESPONSE:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=target_response parent=%s rloc16=%04x rssi=%d", target.c_str(),
               info->mParentRloc16, info->mParentRssi);
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_CHILD_ID_REQUEST_STARTED:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=child_id_request_started parent=%s", target.c_str());
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_SUCCEEDED:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=succeeded parent=%s", target.c_str());
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_FAILED:
    case OT_THREAD_PREFERRED_PARENT_EVENT_TIMED_OUT:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=%s reason=%s error=%s", event_to_string_(info->mEvent),
               result_to_string_(info->mStatus.mResult), otThreadErrorToString(info->mStatus.mError));
      break;
    case OT_THREAD_PREFERRED_PARENT_EVENT_CANCELLED:
    case OT_THREAD_PREFERRED_PARENT_EVENT_CLEARED:
      ESP_LOGI(TAG, "FAST_ATTACH_UCAST_1 event=%s", event_to_string_(info->mEvent));
      break;
  }
}

bool ThreadFastAttachUcast1Component::parse_extaddr_(const std::string &text, otExtAddress *extaddr) {
  std::string compact;
  for (char ch : text) if (ch != ':' && ch != '-' && ch != ' ' && ch != '_') compact.push_back(ch);
  if (compact.size() == 18 && compact.rfind("0x", 0) == 0) compact.erase(0, 2);
  if (compact.size() != 16) return false;
  for (size_t i = 0; i < 8; ++i) {
    char byte[3] = {compact[i * 2], compact[i * 2 + 1], '\0'};
    char *end = nullptr;
    errno = 0;
    const unsigned long value = std::strtoul(byte, &end, 16);
    if (errno != 0 || end != byte + 2 || value > 0xff) return false;
    extaddr->m8[i] = static_cast<uint8_t>(value);
  }
  return true;
}

bool ThreadFastAttachUcast1Component::parse_rloc16_(const std::string &text, uint16_t *rloc16) {
  if (text.empty()) return false;
  char *end = nullptr;
  errno = 0;
  const unsigned long value = std::strtoul(text.c_str(), &end, 16);
  if (errno != 0 || end == text.c_str() || *end != '\0' || value > 0xfffd) return false;
  *rloc16 = static_cast<uint16_t>(value);
  return true;
}

std::string ThreadFastAttachUcast1Component::extaddr_to_string_(const otExtAddress &extaddr) {
  char text[17];
  std::snprintf(text, sizeof(text), "%02x%02x%02x%02x%02x%02x%02x%02x", extaddr.m8[0], extaddr.m8[1],
                extaddr.m8[2], extaddr.m8[3], extaddr.m8[4], extaddr.m8[5], extaddr.m8[6], extaddr.m8[7]);
  return text;
}

const char *ThreadFastAttachUcast1Component::state_to_string_(otThreadPreferredParentState state) {
  static const char *const names[] = {"idle", "starting_discovery", "waiting_parent_request",
      "waiting_target_response", "continuing_selected_attach", "waiting_child_id_response", "succeeded",
      "failed", "timed_out", "cancelled"};
  return static_cast<unsigned>(state) < sizeof(names) / sizeof(names[0]) ? names[state] : "unknown";
}

const char *ThreadFastAttachUcast1Component::result_to_string_(otThreadPreferredParentResult result) {
  static const char *const names[] = {"none", "success", "start_failed", "target_timeout", "attach_timeout",
                                      "role_changed", "cancelled"};
  return static_cast<unsigned>(result) < sizeof(names) / sizeof(names[0]) ? names[result] : "unknown";
}

const char *ThreadFastAttachUcast1Component::event_to_string_(otThreadPreferredParentEvent event) {
  static const char *const names[] = {"requested", "parent_request_started", "target_response",
      "child_id_request_started", "succeeded", "failed", "timed_out", "cancelled", "cleared"};
  return static_cast<unsigned>(event) < sizeof(names) / sizeof(names[0]) ? names[event] : "unknown";
}

}  // namespace thread_fast_attach_ucast_1
}  // namespace esphome
