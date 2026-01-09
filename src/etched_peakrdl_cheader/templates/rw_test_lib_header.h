#pragma once

#include <cstdint>
#include "fw/soc/sohu/sohu_chip_csr.h"
#include "sival/wafersort/csr/csr_test_utils.h"
#include "sival/wafersort/sival_helper.h"

namespace {{namespace}} {
  sival::wafersort::TestResult RwTest(volatile {{struct_type_name}}&);

