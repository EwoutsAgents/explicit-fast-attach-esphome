#pragma once

#include "esphome/core/component.h"

namespace esphome::thread_openthread_source {

// Logs which patched OpenThread this firmware was built with (see __init__.py), and
// repeats it together with the device's own Thread extended address every 30 s. The
// repetition matters because the test runners start reading a board's log only after
// flashing it, which can miss the boot output.
class ThreadOpenThreadSource : public Component {
 public:
  void set_info(const char *group, const char *esp_idf, const char *openthread_base, const char *patched_sha256) {
    this->group_ = group;
    this->esp_idf_ = esp_idf;
    this->openthread_base_ = openthread_base;
    this->patched_sha256_ = patched_sha256;
  }
  void setup() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_CONNECTION; }

 protected:
  void log_source_() const;
  void log_identity_();
  const char *group_{""};
  const char *esp_idf_{""};
  const char *openthread_base_{""};
  const char *patched_sha256_{""};
};

}  // namespace esphome::thread_openthread_source
