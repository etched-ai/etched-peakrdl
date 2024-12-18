  // Write-Read from {{field}} bit field
  curr_test_idx = (uint64_t)test_idx | (uint64_t){{test_idx}};
  if(!ignorer->ShouldSkipTestIndex(curr_test_idx)) {
    passed = fw::testing::{{function_name}}({{reg_ptr}},
                        {{field_bp}},
                        {{field_bw}});
  }
  if (!passed) {
    fw::testing::TestFail((uint64_t)0xDEAD000000000000 | curr_test_idx);
    return false;
  }
