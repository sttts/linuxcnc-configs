o<atc_pickup_tool> sub
  #<currentToolPocket> = #1
  #<tool_number_entry_main_panel> = #2
  o<_pick_tool> call [#1]
  o<atc_pickup_tool> return #<_value>
o<atc_pickup_tool> endsub
M2