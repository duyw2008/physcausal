."vs.cache" as $vs
| reduce ($vs | to_entries[]) as $node (
    {emergent:0, composed:0, hebbian:0, vs_nodes:($vs|length)};
    . as $acc
    | (($node.value.effects? // []) + ($node.value.causes? // [])) as $edges
    | reduce $edges[] as $e ($acc;
        if (($e | type) == "array" and ($e | length) >= 3 and $e[2] == "emergent") then
          .emergent += 1
          | (($e[0] | tostring) + " " + ($e[1] | tostring) | ascii_downcase) as $blob
          | if ($blob | contains("composed")) then .composed += 1
            elif ($blob | contains("hebbian")) then .hebbian += 1
            else . end
        else . end
      )
  )
| .comp_nodes = ([($vs | keys[]) | select(startswith("comp:"))] | length)
