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

