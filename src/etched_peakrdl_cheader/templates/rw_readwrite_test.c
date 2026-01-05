  // Write-Read from {{field}} bit field
  curr_test_idx = (uint64_t)test_idx | (uint64_t){{test_idx}};
  if(!ignorer->ShouldSkipTestIndex(curr_test_idx)) {
#ifdef ENABLE_WAFERSORT_GPIO
{% if function_name == "BitFieldWriteReadTest256" %}
#ifndef ENABLE_LOGGING
    passed = sival::wafersort::csr::BitFieldWriteReadTest256WithReport(
        {{reg_ptr}},
        {{field_bp}},
        {{field_bw}},
        curr_test_idx,
        nullptr);
#else
    passed = sival::wafersort::csr::BitFieldWriteReadTest256WithReport(
        {{reg_ptr}},
        {{field_bp}},
        {{field_bw}},
        curr_test_idx,
        "{{field}}");
#endif
{% else %}
#ifndef ENABLE_LOGGING
    passed = sival::wafersort::csr::BitFieldWriteReadTest32WithReport(
        {{reg_ptr}},
        {{field_bp}},
        {{field_bw}},
        curr_test_idx,
        nullptr);
#else
    passed = sival::wafersort::csr::BitFieldWriteReadTest32WithReport(
        {{reg_ptr}},
        {{field_bp}},
        {{field_bw}},
        curr_test_idx,
        "{{field}}");
#endif
{% endif %}
#else
    WS_LOG_INFO("Testing {{field}} (0x%llx)",
                (unsigned long long)curr_test_idx);
    passed = fw::testing::{{function_name}}({{reg_ptr}},
                        {{field_bp}},
                        {{field_bw}});
    WS_LOG_INFO("  %s", passed ? "PASS" : "FAIL");
#endif
  }
  if (!passed) {
#ifndef ENABLE_WAFERSORT_GPIO
    fw::testing::TestFail((uint64_t)0xDEAD000000000000 | curr_test_idx);
#endif
    return false;
  }
