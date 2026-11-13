# CHANGELOG

## 2026-11-12 — Blockout v001 (Phase 0 / Phase 1a)
- Project structure created (`00_MASTER` … `99_ARCHIVE`); reference board saved as `REFERENCE_MASTER_VISION.webp`.
- Environment check: Blender 5.3.0, EEVEE + Cycles (OptiX on RTX 3060 Ti), FBX/glTF importers enabled; 16 GB RAM.
- Scripts in `00_MASTER/SCRIPTS/`:
  - `config_layout.py`: all layout data (roads, river, plots, fields, cameras, palette)
  - `geo.py`: analytic terrain height, paths, footprint collision
  - `layout_solver.py`: deterministic plot placement with road, river and overlap checks
  - `bld_meshes.py`: blockout builders for 11 building families
  - `build_blockout.py`: full scene rebuild (archives the previous master first)
  - `render_reviews.py`: G1 review renders
- Built `MASTER_WORLD.blend`: terrain 1.6 × 2.0 km plus a 7 km horizon ring, river, bridge, ghat, 11 roads, chowk, gate, 50 building plots, 271 field patches, 420 instanced trees, review cameras, day lighting.
- Three internal iterations before review: fixed the sky gap at the world edge, compacted the lanes and extended the street frontages, cleared camera sightlines, rerouted the ghat path around the temple.
- `PLOT_SCHEDULE.csv`, `ASSET_REGISTRY.csv`, `WORLD_BIBLE.md` created. All items **pending G1**.

## 2026-11-12 - G0 + G1 approved
- User approved the visual bible and layout/blockout v001. Plot IDs P01-P50 are now stable.
- Started the quality benchmark: hero common tiled house (02_ARCHITECTURE/HOUSES_MEDIUM).

- Hero house v001 built: `SCRIPTS/hero_lib.py` (production material library + builder) and `SCRIPTS/hero_house_common.py`. 7 Cycles review renders in `10_EXPORTS/REVIEWS/G3_HERO_HOUSE_COMMON_A_v001/`. One internal fix pass (plinth texture projection, wood grain, annex roof gap, veranda barge boards, roof lap, lipai edge).


## 2026-11-12 - Hero house approved; Phase 1b environment hero pass started
- User approved HERO_House_Common_A v001 as the quality benchmark and asked for the same quality on trees, water, bridge, ghat, ground.
- Order: trees, then water/bridge/ghat, then terrain/roads/fields, then integration into the master.

- Trees v001: `SCRIPTS/hero_trees.py` -> `01_ENVIRONMENT/LANDSCAPE/LIB_Trees.blend` (palm, mango, neem, peepal, banyan with aerial roots, amaltas in bloom; hero + LOD1). Two internal passes (clumps were reading as balls; banyan limb growth).
- River kit v001: `SCRIPTS/hero_river.py` -> `01_ENVIRONMENT/WATER/LIB_River_Bridge_Ghat.blend` (water with refraction + volume colour, height-graded riverbank, 3-arch stone bridge, ghat with chhatri, boulders, reeds, grass tufts). Three internal passes (ghat step stacking, bank buried the ghat, water too dark from above).


## 2026-11-13 - Polish pass from the reference board
- Bridge v002: humpback deck (+2.4 m), graduated arches 8/11/8 m, plan curve (22 deg Simple Deform bend), sliced body so the bend is smooth.
- Props library `SCRIPTS/hero_props.py` -> `06_PROPS/LIB_Village_Props.blend`: street light, lantern post, wall lantern, planters (tulsi, marigold, money plant), bougainvillea, banana, hibiscus, hand pump, haystack, drum and bucket, boundary wall, hero tabela. Dressed-street review in day and dusk.
- Mountains `SCRIPTS/hero_mountains.py`: four look iterations (layered-cake strata, then dune stripes, then turtle-shell cracks, finally soft hills with real-size sandstone outcrops). Waterfall with cascades, foam, mist and plunge pool.
- House v002: tulsi chaura now uses real leaf instances; matkas smooth-shaded.


## 2026-11-13 - Phase 1b library approved; integration into MASTER_WORLD started
- User approved trees, river kit (bridge v002, ghat, water), props, tabela, mountains/waterfall. Integration into the master village started (build_master_v2.py).


## 2026-11-13 - Work paused here (handoff)
- In progress, NOT yet built: geo.py lowers the old northern hills (amplitude 38 m, starting y=560) so the rocky massif is visible; build_blockout.py softens the outer ring and raises tree density; config_layout.py sets TREE_COUNT_TARGET 1600 / spacing 5.5. MASTER_WORLD.blend in the repo was built BEFORE these edits.
- Next: move the mountain massif to about (149, 900, 0) so its waterfall stream meets the river, and cut the master terrain under it. Then add tree lines along roads and bunds, orchards, shrubs and grass tufts; farm detail (field bunds, machaan, tubewell, scarecrows, more haystacks); rebuild with build_master_v2.py and render with render_reviews.py --use-cycles.
- Open question for the user: bullock approach (proper generated/supplied model vs placeholder vs wait for Phase 6).
- Rendering tip: run only one Cycles job at a time on the 8 GB GPU (two at once crashed).



## 2026-11-13 - Master integration v2 + first character style tests (laptop session)
- Machine: GTX 1650 4 GB / 8 GB RAM / Blender 5.2.3. OptiX fails here -> render scripts use CUDA. Full-village Cycles runs out of
  memory; EEVEE previews work with foliage baked (`BAKE_FOLIAGE`, env `AMALTASPUR_BAKE_FOLIAGE=0` to disable on the RTX PC).
- Massif + waterfall moved to (149, 900, -4.5); river now starts at the falls; terrain shaped around the massif (geo.MASSIF);
  open country lifted 2.5 m outside the village core. Known issue: massif flanks still read as cut walls from the air.
- New `SCRIPTS/hero_farm.py` -> `06_PROPS/LIB_Farm_Props.blend`: machaan, tubewell (pump room, hauz, channel, LT pole), scarecrow,
  3 shrubs, green/dry grass tufts, kans grass. Review renders in `PH1C_FARM_PROPS_v001`.
- build_master_v2: field bunds (21.6 km), 3 orchards, 4 tubewell yards, 8 machaans, 15 scarecrows, +haystacks, +1,121 trees
  (avenues, orchards, bunds, north valley), shrubs + ~37k grass tufts + kans on the banks, chowk kerb, new review cameras.
  Plot IDs P01-P50 unchanged. EEVEE previews in `G4_INTEGRATED_v002_wip`.
- Characters (style tests, NOT approved): `CHR_Animal_Bullock_001` (script-built; user: "bullock is good") and
  `CHR_Human_Woman_001` v002 on an MPFB 2.0.18 CC0 base mesh with the built-in Mixamo-named rig (arm pose test only;
  no Mixamo animation tested yet). v001 (pure script) superseded.
- Hair: `SCRIPTS/hair_strands.py` - real strand hair (Blender hair curves) on a rig-deformed scalp surface; Woman_001
  braid built with the bundled "Braid Hair Curves" node and simulated with "Hair Dynamics" (Physics mode); 48-frame
  test clip `G5_HUMAN_WOMAN_001_v002/braid_anim/braid_physics_test.mp4`. Sideburns/ear gap fixed, cap hidden under strands.
- New: `CHR_Human_Man_001` (farmer ~55, dhoti-kurta, gamchha, salt-and-pepper strand hair, strand moustache/brows,
  Mixamo-named rig) and `LIB_Animals_Farm.blend` (cow, buffalo, goat, dog, hen) in the bullock style. All pending review.

## 2026-11-13 - Environment upgrade Batches 1-6 (laptop session, Blender 5.2)
- B1 `SCRIPTS/lighting_atmosphere.py`: physical sky + clouds, warm morning sun, haze on geometry only (mist pass,
  sky re-added from the environment pass), grade + bloom + vignette; presets morning / golden / dusk / night.
  Night = moon, stars, and warm practical lights generated at every lamp asset and every building's own lamp list.
- Hero banyan `SCRIPTS/hero_banyan_chowk.py` -> `01_ENVIRONMENT/LANDSCAPE/LIB_Hero_Banyan.blend` (30 m canopy, aerial
  and pillar roots, kalava, shrine, diyas, 12 hanging lanterns) replaces the chowk banyan.
- B2 `arch_kit.py` + `hero_buildings_b2.py` -> `02_ARCHITECTURE/LIB_Buildings_B2.blend` (middle house, haveli, kirana /
  chai / cloth shops, 2-storey hardware shop, Shiv temple, school, panchayat - all with interiors) and
  `hero_house_poor.py` -> `HOUSES_SMALL/HERO_House_Small_Kaccha_A.blend`. All 29 blockout plots now hero buildings
  (blockouts kept hidden in B2_REPLACED_BLOCKOUT).  Signs are English for now (Blender can't shape Devanagari).
- B3 `hero_props_b3.py` + `place_b3.py`: poles + sagging wires, drains, taps, benches, bins, direction board, thelas,
  buntings, bicycles, charpais, bus stop, milestone, water tower, mobile tower.
- B4 `hero_trees_b4.py` -> `LIB_Trees_B4.blend` (bamboo, eucalyptus, babool, gulmohar, ashoka, ber, sugarcane, hedge);
  B5 weathering in hero_lib (plaster streaks/patches/flaking, tile variation + moss, mud cracks, wood grain, stone damp)
  and master terrain (dry patches, wildflowers) / dirt roads (pebbles); B6 footpaths, pebbles, far ridge ring.
  Placement: `patch_b456.py` (also called from build_master_v2).  Not re-generated with B5 materials yet: the older
  approved libraries (house common, props, trees, river kit, mountains) - those need the RTX PC (Blender 5.3).
- Checkpoints: 99_ARCHIVE/MASTER_WORLD_preB1/preBanyan/preB2/preB3/preB456_*.blend

## 2026-11-13 - RTX PC session: portability fix, libraries refreshed, storybook day + night chowk lighting
- PORTABILITY BUG FIXED: MASTER_WORLD linked 5 libraries by absolute laptop paths (C:\Users\<laptop>\Downloads\...):
  B2 buildings, kaccha house, hero banyan, B3 props, B4 trees. On any other PC they were missing (shops gone, banyan
  rendered black, no banyan lanterns at night). New `SCRIPTS/fix_library_paths.py` re-points them inside the checkout
  (relative). Both characters linked Blender 5.2 bundled hair node assets - re-pointed to the running Blender and made
  local. All `libraries.load(..., link=True)` calls now pass `relative=True`. Checkpoints: 99_ARCHIVE/*_prePathFix_*.
- Older approved libraries regenerated with the B5 weathering materials on Blender 5.3 (house common, props, trees,
  river kit, mountains). The master's BAKED tree copies were made from the old trees (rebuild master with
  AMALTASPUR_BAKE_FOLIAGE=0 on this PC to pick them up).
- lighting_atmosphere.py: new `storybook` preset (user reference board 2: low warm west sun, warmer grade, more cumulus).
  `night` v2 per the user's night brief: moon disc + maria in frame, subtle clouds, deep navy sky, softer moon key,
  chowk rig (6 amber trunk uplights, warm canopy-underside bounce, 10 root accents, canopy-only cool moon spot, warm pools
  under every chowk lantern, glowing windows on ~75% of hero houses, interior glow in hero buildings), shadow pool 2 GB.
  Banyan detection fixed for the _BAKED copy (lanterns now light at night).
- Reviews: G4_NIGHT_CHOWK_v002 and G4_DAY_STORYBOOK_v001 (with before/after compares). Master saved with its existing
  morning preset; presets are applied at render time (`--preset storybook|night`).
- Known: banyan canopy underside stays darker than the reference (baked leaf material barely takes light from below);
  the massif flank still reads as a cut wall in CAM_Village_Hero.
