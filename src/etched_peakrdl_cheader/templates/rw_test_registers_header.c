{% for dependency in deps %}
{{dependency}}{% endfor %}
#include "fw/soc/sohu/sohu_chip_csr.h"
#include "fw/app/csr_access_test/csr_test_ignorer.h"
{% if hasRegOrRegFile %}#include "fw/testing/bit_field_test.h"
#include "fw/testing/testing.h"
#include "fw/utils/csr_descriptor_helper.h"
#include "fw/utils/log.h"
#ifndef WS_LOG_INFO
#ifndef ENABLE_LOGGING
#define WS_LOG_INFO(...) \
  do {                   \
  } while (0)
#else
#define WS_LOG_INFO(...) LOG_INFO_BLOCKING(__VA_ARGS__)
#endif
#endif
#ifdef ENABLE_WAFERSORT_GPIO
#include "sival/wafersort/csr/csr_test_utils.h"
#endif
{% endif %}
