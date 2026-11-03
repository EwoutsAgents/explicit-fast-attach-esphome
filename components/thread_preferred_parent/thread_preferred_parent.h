#pragma once

#include "esphome/components/openthread/openthread.h"
#include "esphome/core/component.h"

#include <openthread/preferred_parent.h>
#include <openthread/thread.h>

#include <cstdint>
#include <string>

namespace esphome {
namespace thread_preferred_parent {

// Thin ESPHome adapter. OpenThread owns discovery, candidate selection,
// retries, timeouts, attach continuation, cancellation, and terminal state.
class ThreadPreferredParentComponent : public Component {
 public:
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::WIFI - 1.0f; }

  void set_parent_rloc16(uint16_t rloc16);
  bool set_parent_rloc16(const std::string &rloc16);
  bool set_parent_extaddr(const std::string &extaddr);

  void request_switch();
  void request_switch(uint16_t rloc16);
  void request_switch(const std::string &extaddr);
  void cancel_switch();
  void clear_target();

  std::string current_parent_extaddr() const;

  void set_max_attempts(uint8_t value) { this->max_attempts_ = value; }
  void set_retry_interval(uint32_t value) { this->retry_interval_ms_ = value; }
  void set_selected_attach_timeout(uint32_t value) { this->attach_timeout_ms_ = value; }
  void set_require_selected_parent_hook(bool) {}
  void set_log_parent_responses(bool) {}

 protected:
  enum class TargetType : uint8_t { NONE, EXTADDR, RLOC16 };

  static void preferred_parent_callback_(const otThreadPreferredParentEventInfo *event, void *context);
  static bool parse_extaddr_(const std::string &text, otExtAddress *extaddr);
  static bool parse_rloc16_(const std::string &text, uint16_t *rloc16);
  static const char *state_to_string_(otThreadPreferredParentState state);
  static const char *result_to_string_(otThreadPreferredParentResult result);
  static const char *event_to_string_(otThreadPreferredParentEvent event);
  static std::string extaddr_to_string_(const otExtAddress &extaddr);

  bool resolve_target_(otInstance *instance, otExtAddress *extaddr) const;

  TargetType target_type_{TargetType::NONE};
  otExtAddress target_extaddr_{};
  uint16_t target_rloc16_{0xfffe};
  uint8_t max_attempts_{5};
  uint32_t retry_interval_ms_{8000};
  uint32_t attach_timeout_ms_{16000};
};

}  // namespace thread_preferred_parent
}  // namespace esphome
