# Amaltaspur - 3D Indian Village Universe (Blender 5.3)

Fictional Indian village for Hindi animated storytelling, built procedurally with Blender Python.

- `VILLAGE_UNIVERSE/00_MASTER` - MASTER_WORLD.blend, world bible, plot schedule, asset registry, changelog, all build scripts (`SCRIPTS/`)
- `01_ENVIRONMENT` - tree library, river/bridge/ghat kit, mountains + waterfall
- `02_ARCHITECTURE` - hero houses
- `06_PROPS` - props library + tabela
- `10_EXPORTS/REVIEWS` - review renders per gate
- `99_ARCHIVE` - automatic checkpoints of previous builds

Rebuild the master: `blender -b --factory-startup --python VILLAGE_UNIVERSE/00_MASTER/SCRIPTS/build_master_v2.py`
