  // Write-Read from {{field}} bit field
  curr_test_idx = (uint64_t)test_idx | (uint64_t){{test_idx}};
  if (!ignorer->ShouldSkipTestIndex(curr_test_idx)) {
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
      // Report failure but continue running remaining fields.
      result.reported = true;
      sival::wafersort::TestCsrSramStatusGpio128(true, result.ip_index,
                                                 result.address, result.data);
      if (first_failure.passed) {
        first_failure = result;
      }
    }
  }
