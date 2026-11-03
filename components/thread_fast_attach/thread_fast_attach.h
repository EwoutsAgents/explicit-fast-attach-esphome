#pragma once

#include "esphome/core/component.h"

namespace esphome::thread_fast_attach {

class ThreadFastAttachComponent : public Component {
 public:
  void set_arm_after_parent_loss(bool value) { this->arm_after_parent_loss_ = value; }
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::AFTER_WIFI; }

 protected:
  bool arm_after_parent_loss_{false};
  bool observed_attached_{false};
  bool detach_handled_{false};
};

}  // namespace esphome::thread_fast_attach
