#pragma once

#include <cstdint>
#include "fw/soc/sohu/sohu_chip_csr.h"
#include "sival/wafersort/csr/csr_test_utils.h"
#include "sival/wafersort/sival_helper.h"

namespace {{namespace}} {
  void RunAll(sival::wafersort::TestRunner& runner,
              volatile {{struct_type_name}}&);
  sival::wafersort::TestResult RwTest(volatile {{struct_type_name}}&);
