{% for dependency in deps %}
{{dependency}}{% endfor %}
#include "fw/soc/sohu/sohu_chip_csr.h"
#include "fw/app/csr_access_test/csr_test_ignorer.h"
{% if not hasImports %}#include "fw/testing/bit_field_test.h"
#include "fw/testing/testing.h"
{% endif %}
