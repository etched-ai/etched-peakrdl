  // Write-Read from {{field}} bit field
{% if function_name == "BitFieldWriteReadTest256" %}
#ifndef ENABLE_LOGGING
  result = sival::wafersort::csr::BitFieldWriteReadTest256(
      {{reg_ptr}},
      {{field_bp}},
      {{field_bw}},
      nullptr,
      {{ip_index}});
#else
  result = sival::wafersort::csr::BitFieldWriteReadTest256(
      {{reg_ptr}},
      {{field_bp}},
      {{field_bw}},
      "{{field}}",
      {{ip_index}});
#endif
{% else %}
#ifndef ENABLE_LOGGING
  result = sival::wafersort::csr::BitFieldWriteReadTest32(
      {{reg_ptr}},
      {{field_bp}},
      {{field_bw}},
      nullptr,
      {{ip_index}});
#else
  result = sival::wafersort::csr::BitFieldWriteReadTest32(
      {{reg_ptr}},
      {{field_bp}},
      {{field_bw}},
      "{{field}}",
      {{ip_index}});
#endif
{% endif %}
  if (!result.passed) {
    return result;
  }

