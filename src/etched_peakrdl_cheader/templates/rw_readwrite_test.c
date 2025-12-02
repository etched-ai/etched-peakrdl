  // Write-Read from {{field}} bit field
  curr_test_idx = (uint64_t)test_idx | (uint64_t){{test_idx}};
  if(!ignorer->ShouldSkipTestIndex(curr_test_idx)) {
#ifdef ENABLE_WAFERSORT_GPIO
    sival::wafersort::TestProgressGpio(curr_test_idx & 0xFF);
    WS_LOG_INFO("Testing {{field}} (0x%llx)", (unsigned long long)curr_test_idx);
#endif
    passed = fw::testing::{{function_name}}({{reg_ptr}},
                        {{field_bp}},
                        {{field_bw}});
#ifdef ENABLE_WAFERSORT_GPIO
    WS_LOG_INFO("  %s", passed ? "PASS" : "FAIL");
#endif
  }
  if (!passed) {
    fw::testing::TestFail((uint64_t)0xDEAD000000000000 | curr_test_idx);
    return false;
  }
