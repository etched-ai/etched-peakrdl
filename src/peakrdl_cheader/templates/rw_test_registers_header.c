{% for dependency in deps %}
{{dependency}}{% endfor %}
#include "fw/soc/sohu/sohu_chip_csr.h"
#include "fw/app/csr_access_test/csr_test_ignorer.h"
{% if hasRegOrRegFile %}#include "fw/testing/bit_field_test.h"
#include "fw/testing/testing.h"
#include "fw/utils/csr_descriptor_helper.h"
{% endif %}
