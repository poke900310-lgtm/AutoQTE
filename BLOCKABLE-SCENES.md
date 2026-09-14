# Blockable DIS scenes

Every scene AutoQTE can be told to leave alone, derived from the game's own
containers by asset class (`InteractiveSceneLevelSequence`), not by folder or name.
Regenerate after a game patch with `tools/pak/list_dis_scenes.py`; do not edit
by hand.

**59 scenes.** `BlockAlso` matches a lowercase substring of the scene identity,
and the identity ends in the package path below, so the safe pattern for a
scene is its lowercased file name. Several patterns go on one `BlockAlso` line
separated by commas, or on several `BlockAlso` lines - both accumulate. A
single value must not be wrapped across lines; the parser reads one key per
line and a wrapped value applies only its first line.

## Reference set in `AutoQTE.defaults.ini`

| pattern | scenes it blocks |
|---|---|
| `vasylflogging` | `dis_vasylflogging` |
| `feedingesme` | `dis_feedingesme_long` |
| `forcefeed` | `sq708_dis_forcefeed`, `sq708_dis_forcefeed_2nd` |
| `anca_wounds` | `ls_dis_anca_wounds_a`, `ls_dis_anca_wounds_b`, `ls_dis_anca_wounds_c` |
| `patching_marat` | `dis_q106_patching_marats_wounds` |
| `endurance_trial` | `sq721_endurance_trial_1_ls`, `sq721_endurance_trial_2_ls`, `sq721_endurance_trial_3_ls` |
| `breakritual` | `sq721_breakritual_ls` |
| `eating_mandrake` | `sq717_eating_mandrake` |
| `takerabbit` | `q401_dis_takerabbit` |
| `destroying_skates` | `sq711_destroying_skates` |
| `filling_grave` | `dis_filling_grave` |
| `ringingbells` | `q101_ringingbells_ls` |
| `gettingkey` | `sq710_dis_gettingkey_ls` |

## All scenes, by quest

| pattern (file name) | package |
|---|---|
| **_Open_World** | |
| `dis_digging_treasure_00` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_00` |
| `dis_digging_treasure_01` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_01` |
| `dis_digging_treasure_02` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_02` |
| `dis_digging_treasure_03` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_03` |
| `dis_digging_treasure_04` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_04` |
| `dis_digging_treasure_05` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_05` |
| `dis_digging_treasure_06` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/NanoPOI_treasure/DialogueInteractions/DIS_Digging_Treasure_06` |
| `dis_sequence_npoi_attic04` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/NanoPOIs/npoi_attics/npoi_attic_04/DialogueInteractions/PushingBookshelf/DIS_sequence_NPOI_Attic04` |
| `dis_digging_treasure_poi114` | `_Dawnwalker/Quest/_Open_World/POIs/Act_1/POI114_Silver_Cache/DialogueInteractions/DIS_Digging_Treasure_POI114` |
| **_Side_Quests** | |
| `dis_filling_grave` | `_Dawnwalker/Quest/_Side_Quests/sq001_grave/Dialogues/Cinematic/sq001_05_crina_ending_ns/DIS/DIS_filling_grave` |
| `dis_vasylflogging` | `_Dawnwalker/Quest/_Side_Quests/sq003_nf/DialogueInteractions/VasylFlogging/DIS_VasylFlogging` |
| `dis_hookingworm_long` | `_Dawnwalker/Quest/_Side_Quests/sq004_fishing/DIS/DIS_hookingWorm_Long` |
| `sq708_dis_forcefeed` - also matches `sq708_dis_forcefeed_2nd` | `_Dawnwalker/Quest/_Side_Quests/sq708_ambrus/DIS/sq708_DIS_ForceFeed` |
| `sq708_dis_forcefeed_2nd` | `_Dawnwalker/Quest/_Side_Quests/sq708_ambrus/DIS/sq708_DIS_ForceFeed_2nd` |
| `sq710_dis_gettingkey_ls` | `_Dawnwalker/Quest/_Side_Quests/sq710_bakir/DIS/sq710_DIS_gettingkey_LS` |
| `sq711_chopping_wood` - also matches `sq711_chopping_wood_2`, `sq711_chopping_wood_3`, `sq711_chopping_wood_4` | `_Dawnwalker/Quest/_Side_Quests/sq711_astrologist/DialogueInteractions/ChoppingWood/sq711_chopping_wood` |
| `sq711_chopping_wood_2` | `_Dawnwalker/Quest/_Side_Quests/sq711_astrologist/DialogueInteractions/ChoppingWood/sq711_chopping_wood_2` |
| `sq711_chopping_wood_3` | `_Dawnwalker/Quest/_Side_Quests/sq711_astrologist/DialogueInteractions/ChoppingWood/sq711_chopping_wood_3` |
| `sq711_chopping_wood_4` | `_Dawnwalker/Quest/_Side_Quests/sq711_astrologist/DialogueInteractions/ChoppingWood/sq711_chopping_wood_4` |
| `sq711_destroying_skates` | `_Dawnwalker/Quest/_Side_Quests/sq711_astrologist/DialogueInteractions/DestroyingSkates/sq711_destroying_skates` |
| `dis_sq712_pushingbookshelf_cathedral` | `_Dawnwalker/Quest/_Side_Quests/sq712_florin/DIS/dis_sq712_pushingbookshelf_cathedral` |
| `sq717_eating_mandrake` | `_Dawnwalker/Quest/_Side_Quests/sq717_wisps/DIS/sq717_eating_mandrake` |
| `dis_sq719_boardingwindows` | `_Dawnwalker/Quest/_Side_Quests/sq719_pieters_past/DialogueInteractions/BoardingWindows/DIS_sq719_boardingWindows` |
| `sq719_choppingwood_ls` | `_Dawnwalker/Quest/_Side_Quests/sq719_pieters_past/DialogueInteractions/ChoppingWood/sq719_choppingWood_LS` |
| `dis_sq719_diggingtreasure` | `_Dawnwalker/Quest/_Side_Quests/sq719_pieters_past/DialogueInteractions/DiggingTreasure/DIS_sq719_diggingTreasure` |
| `dis_choppingtree_a_sequence` | `_Dawnwalker/Quest/_Side_Quests/sq720_pixies/DialogueInteractions/DIS_ChoppingTree_A_sequence` |
| `dis_choppingtree_b_sequence` | `_Dawnwalker/Quest/_Side_Quests/sq720_pixies/DialogueInteractions/DIS_ChoppingTree_B_sequence` |
| `dis_cooking_a_sequence` | `_Dawnwalker/Quest/_Side_Quests/sq720_pixies/DialogueInteractions/DIS_Cooking_A_sequence` |
| `dis_cooking_b_sequence` | `_Dawnwalker/Quest/_Side_Quests/sq720_pixies/DialogueInteractions/DIS_Cooking_B_sequence` |
| `sq721_breakritual_ls` | `_Dawnwalker/Quest/_Side_Quests/sq721_anca/DIS/sq721_breakritual_LS` |
| `sq721_endurance_trial_1_ls` | `_Dawnwalker/Quest/_Side_Quests/sq721_anca/DIS/sq721_endurance_trial_1_LS` |
| `sq721_endurance_trial_2_ls` | `_Dawnwalker/Quest/_Side_Quests/sq721_anca/DIS/sq721_endurance_trial_2_LS` |
| `sq721_endurance_trial_3_ls` | `_Dawnwalker/Quest/_Side_Quests/sq721_anca/DIS/sq721_endurance_trial_3_LS` |
| `sq721_move_beam_ls` | `_Dawnwalker/Quest/_Side_Quests/sq721_anca/DIS/sq721_move_beam_LS` |
| **q001_vs** | |
| `dis_liftingbeam_long` | `_Dawnwalker/Quest/q001_vs/Dialog/DIS_Sequences/DIS_liftingBeam_long` |
| **q002_prologue** | |
| `ls_dis_woodchopping_long` | `_Dawnwalker/Quest/q002_prologue/DialogueInteractions/WoodChopping/LS_DIS_WoodChopping_Long` |
| `dis_feedingesme_long` | `_Dawnwalker/Quest/q002_prologue/Dialogues/Cinematic/q002_03_family_breakfast/DIS/DIS_feedingEsme_Long` |
| `ls_dis_anca_wounds_a` | `_Dawnwalker/Quest/q002_prologue/Dialogues/Cinematic/q002_07_back_with_herbs/DIS/LS_DIS_Anca_Wounds_A` |
| `ls_dis_anca_wounds_b` | `_Dawnwalker/Quest/q002_prologue/Dialogues/Cinematic/q002_07_back_with_herbs/DIS/LS_DIS_Anca_Wounds_B` |
| `ls_dis_anca_wounds_c` | `_Dawnwalker/Quest/q002_prologue/Dialogues/Cinematic/q002_07_back_with_herbs/DIS/LS_DIS_Anca_Wounds_C` |
| **q101_st_tyna** | |
| `q101_invisibleink` | `_Dawnwalker/Quest/q101_st_tyna/DialogueInteractions/InvinsibleInk/q101_invisibleInk` |
| `q101_preparinginfusion` | `_Dawnwalker/Quest/q101_st_tyna/DialogueInteractions/PreparingInfusion/q101_PreparingInfusion` |
| `q101_pushingbookshelf_ls` | `_Dawnwalker/Quest/q101_st_tyna/DialogueInteractions/PushingBookshelf/q101_pushingBookshelf_LS` |
| `q101_ringingbells_ls` | `_Dawnwalker/Quest/q101_st_tyna/DialogueInteractions/RingingBells/q101_RingingBells_LS` |
| **q102_st_mihai** | |
| `q102_pushingbookshelf_ls` | `_Dawnwalker/Quest/q102_st_mihai/DialogueInteractions/PushingBookshelf/q102_pushingBookshelf_LS` |
| `q102_pushingstone` | `_Dawnwalker/Quest/q102_st_mihai/DialogueInteractions/PushingStone/q102_PushingStone` |
| `q102_pushingwelllid` | `_Dawnwalker/Quest/q102_st_mihai/DialogueInteractions/PushingWellLid/q102_PushingWellLid` |
| **q105_rebels** | |
| `dis_q105_fixing_cart` | `_Dawnwalker/Quest/q105_rebels/DialogueInteractions/DIS_q105_fixing_cart` |
| **q106_rebel_issues** | |
| `dis_q106_patching_marats_wounds` | `_Dawnwalker/Quest/q106_rebel_issues/DialogueInteractions/DIS_q106_patching_Marats_wounds` |
| `dis_q106_unblocking_church_gate` | `_Dawnwalker/Quest/q106_rebel_issues/DialogueInteractions/DIS_q106_unblocking_church_gate` |
| `q106_pushingbookshelf_ls` | `_Dawnwalker/Quest/q106_rebel_issues/DialogueInteractions/PushingBookshelf/q106_pushingBookshelf_LS` |
| **q300_shared_files** | |
| `dis_shelf` - also matches `q302_dis_shelf`, `q303_dis_shelf` | `_Dawnwalker/Quest/q300_shared_files/DIS/dis_shelf` |
| `q302_dis_shelf` | `_Dawnwalker/Quest/q300_shared_files/DIS/q302_dis_shelf` |
| `q303_dis_shelf` | `_Dawnwalker/Quest/q300_shared_files/DIS/q303_dis_shelf` |
| **q302_rebel_attack** | |
| `dis_tie_rope` | `_Dawnwalker/Quest/q302_rebel_attack/DIS/dis_tie_rope` |
| `dis_turning_wheel` | `_Dawnwalker/Quest/q302_rebel_attack/DIS/dis_turning_wheel` |
| `dis_wardrobe_secretentrance` | `_Dawnwalker/Quest/q302_rebel_attack/DIS/dis_wardrobe_secretentrance` |
| **q401_epilogue** | |
| `q401_dis_puttingindoors` | `_Dawnwalker/Quest/q401_epilogue/DIS/Q401_DIS_PuttingInDoors` |
| `q401_dis_takerabbit` | `_Dawnwalker/Quest/q401_epilogue/DIS/Q401_DIS_TakeRabbit` |

## Choosing a pattern

Longer is safer. `dis_shelf` also matches `q302_dis_shelf` and `q303_dis_shelf`;
`sq711_chopping_wood` matches all four of that quest's chopping scenes. If you
mean one scene, use its whole file name. If you mean the family, the shared
stem is the point. Press INS during a scene to see its exact identity.
