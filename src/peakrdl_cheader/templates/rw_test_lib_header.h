#pragma once

#include <cstdint>
#include "fw/soc/sohu/sohu_chip_csr.h"

namespace {{namespace}} {
  bool RwTest(volatile {{struct_type_name}}&, uint64_t);

