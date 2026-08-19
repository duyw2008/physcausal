{
  K: .K,
  cells: (.cells | length),
  syn_edges: (.synaptic.activations | length),
  tier: (.synaptic.tiers | to_entries | group_by(.value) | map({tier: (.[0].value|tostring), n: length})),
  s_gt_1: ([.synaptic.activations[] | select(.s > 1.0)] | length),
  s_gt_5: ([.synaptic.activations[] | select(.s > 5.0)] | length),
  s_lt_005: ([.synaptic.activations[] | select(.s < 0.05)] | length),
  s_max: ([.synaptic.activations[] | .s] | max),
  s_p50: ([.synaptic.activations[] | .s] | sort | (.[(length/2)|floor])),
  multi_n: ([.synaptic.activations[] | select((.n // 0) >= 2)] | length),
  max_n: ([.synaptic.activations[] | (.n // 0)] | max)
}
