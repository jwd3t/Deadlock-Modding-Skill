---
name: deadlock-modding
description: >-
  Expert guide, workflows, and tools for creating and debugging mods for Valve's Deadlock (Source 2).
  Use when creating or modifying audio (.vsnd_c, .vsndevts_c), textures (.vtex_c), particle systems (.vpcf_c),
  or packaging VPK mods for Deadlock Mod Manager.
---

# Deadlock & Source 2 Modding Runbook

This skill equips the agent with complete reverse-engineering and compilation knowledge for modding Valve's **Deadlock** (Source 2 engine) safely, VAC-compliantly, and reliably.

---

## 🤖 Instructions for the Agent (Standard Operating Procedure)

When invoked to create or modify a Deadlock mod, **always adhere to these rules**:
1. **Never Touch Steam Directories Directly**: NEVER write files to `C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\citadel\addons\`. Always generate outputs in the user's local workspace/repository for them to install manually.
2. **Use the Provided Tools**: Utilize `scripts/pack_vpk.py` (if available) or `ValvePak` for VPK creation.
3. **Verify Prerequisites**: Ensure .NET SDK, `ValveResourceFormat` (Decompiler), `BCnEncoder.NET` (for textures), and Python are available in the environment before starting.
4. **Communicate Clearly**: When providing the final mod, give the user absolute file links to the `.vpk` and `.zip` files so they can easily click and copy them.

---

## 1. Audio Modding (`.vsnd_c` & `.vsndevts_c`)

### A. Compiled Sound Files (`.vsnd_c`)
- **Structure**: Header (12 bytes) + `RED2` (ResourceEditInfo2) + `CTRL` (BinaryKV3 v5 compressed with LZ4) + `DATA` (raw audio frames).
- **LZ4 Decompression Rule**: Binary patching raw bytes directly in an existing `.vsnd_c` corrupts the LZ4 stream (`Failed to decompress LZ4`), causing Deadlock to mute the sound completely.
- **Compilation Process**:
  1. Remove ID3v2 / metadata tags from MP3 files. Must provide raw MPEG audio frames (48,000 Hz stereo).
  2. Compute `SampleCount`, `StreamingSize`, and `Duration` ($Duration = \frac{Samples}{Rate}$).
  3. Update the BinaryKV3 control block and recompress with standard LZ4 or use `ValveResourceFormat` (`res.Serialize(stream)`).

### B. Sound Event Coordination (`.vsndevts_c`)
- The engine checks `soundevents/player.vsndevts_c` (or hero-specific event scripts) before playing sounds.
- **Duration Match**: Set `vsnd_duration` in the sound event to match the replacement audio duration. If omitted or lower than the audio length, the engine cuts the audio abruptly at the vanilla duration.
- **Decibel Gain & Mixing**:
  - `volume`: Base event gain in dB (e.g., `4.5` dB).
  - `volume_offset_player`: Local player offset (vanilla is `-2.5` dB; setting `+1.0` dB yields a `+3.5` dB net boost).
  - `volume_enemy_targeting_boost`: Enemy warning boost (e.g., `6.0` dB for clear audible alerts).
- **Mod Compatibility Warning**: `player.vsndevts_c` is a monolithic file containing sound events for *all* player actions (parries, footsteps, jumps, melee). Overriding it will overwrite any separate sound mods installed by the user (such as custom Parry sound mods). If maximum compatibility with other mods is required, omit `player.vsndevts_c` and rely on direct `.vsnd_c` asset replacement with normalized peak volume.

---

## 2. Texture Modding (`.vtex_c`)

### Hardware Compression Requirement
- **Critical Rule**: Deadlock's `SpriteCard` particle shaders **reject uncompressed RGBA8888** textures. If an uncompressed texture is loaded in a particle system, the GPU sampler fails and displays the engine's fallback error sprite: **a dark red/orange checkerboard "X"**.
- **Format**: Textures must be compiled as **DXT5 (BC3)** with full color and alpha channel.
- **Texture Header Layout**:
  - 2,068-byte header containing `RED2` and `DATA` blocks cloned from a 256x256 DXT5 texture (e.g. `particle_ring_wave_10.vtex_c`).
  - Block compression: 256x256 DXT5 produces exactly 65,536 bytes of BC3 pixel data.
  - Total file size: 2,068 + 65,536 = 67,604 bytes.

---

## 3. Particle Systems (`.vpcf_c`)

### A. KeyValues 3 Resource Typing (`KVFlag.Resource`)
- In Source 2 KV3 files, asset paths (like `m_hTexture` in `C_OP_RenderSprites` or `m_ChildRef` in `m_Children`) **must have `KVFlag.Resource` (enum: 1)**.
- If assigned as a plain string, the engine does not treat it as a resource handle, leaving the runtime texture pointer null and rendering error "X"s.
- KV3 syntax output: `m_hTexture = resource:"materials/particle/<name>.vtex"`.

### B. Preserving Base Game Particles vs. Isolating Effects
- Vanilla parent particles (such as `melee_heavy_activate_charge.vpcf`) spawn multiple child particles simultaneously (`outer`, `bits`, `model`, `tube`, `burst`).
- **Best Practice (Mod Compatibility & Visual Richness)**:
  - **Do NOT clear `m_Children` or `ExternalReferences`** unless explicitly requested.
  - Leave `outer`, `bits`, `model`, and `tube` intact in `m_Children`, and only override the specific child (`burst.vpcf`).
  - This preserves the hero's fist glows, charging energy, sparks, and ensures full compatibility with other mods that modify those components.
- **Full Isolation (Optional)**:
  - Only when the user explicitly requests removing all secondary clutter: clear `m_Children` to contain only the single child and prune `ResourceRefInfoList`.

### C. Overhead Billboard Positioning & Dynamic Player Tracking (`C_OP_SetControlPointToPlayer`)
- **Dynamic Local Player Attachment**:
  - Instead of attaching only to `CP0` (which is the attacker), use `C_OP_SetControlPointToPlayer` in `m_PreEmissionOperators` of the particle.
  - Set `m_nCP1 = 2`, `m_vecCP1Pos = [0, 0, 75.0]`, and `m_bOrientToEyes = false`.
  - This dynamically anchors `CP2` to the player's head, regardless of who casts the ability.
- **Spawn & Lock**:
  - Spawn on `CP2`: In `C_INIT_CreateWithinSphereTransform`, set `m_TransformInput: { m_nControlPoint: 2 }`.
  - Lock to `CP2`: In `C_OP_PositionLock`, set `m_TransformInput: { m_nControlPoint: 2 }` and `m_bLockRot = true`.
- **Optimal Overhead Height**:
  - $+75.0$ units in Z is the calibrated height for Deadlock heroes (avoids clipping into tall hero models while preventing excessive floating in the air).
- **Billboard Facing**: Set `m_bUseYawWithNormalAligned = false` on `C_OP_RenderSprites` so the sprite always directly faces the active camera.
- **Roll Orientation Compensation**: In Source 2, screen-facing billboards aligned to player entities experience a 90° clockwise coordinate shift. **Pre-rotate texture images 90° counter-clockwise (to the left)** so they render upright in-game.

### D. High-Impact Sparks & Refractive Shockwaves
- **Particle Trail Output Fields (`C_INIT_InitFloat`)**:
  - `m_nOutputField = 1`: Lifetime.
  - `m_nOutputField = 3` (default): Radius/thickness. Vanilla sparks use tiny values ($4-8$); molten metal sparks require $14-24$.
  - `m_nOutputField = 7`: Alpha opacity.
  - `m_nOutputField = 10`: Trail length multiplier. Vanilla uses $0.04-0.08$; long molten streaks require $0.30-0.65$.
- **Trail Luminosity (`C_OP_RenderTrails`)**: Set `m_flOverbrightFactor` to $25.0+$ and `m_flAddSelfAmount` to $5.0+$ for dazzling bloom.
- **Refractive Shockwave Ripple (`m_bRefract = true`)**: Use `materials/particle/warp_ripple_normal.vtex` with `m_flRefractAmount = 0.20-0.25` for high-impact air distortion rings.

### E. Proximity Detection & Distance Culling (`C_OP_DistanceCull` vs `C_OP_DistanceToTransform`)
- **Valve's Engine Quirk in `C_OP_DistanceCull`**:
  - `C_OP_DistanceCull` contains an early-exit optimization in `particles.dll` that calculates distance between the Control Point and the particle collection's Bounding Box (AABB).
  - If `dist_to_AABB > flDistance`, the engine executes an immediate return (`ja 0x18018805f`) without checking particles, assuming culling is only done inside a sphere (`m_bCullInside = true`).
  - **CRITICAL RULE**: NEVER use `C_OP_DistanceCull` with `m_bCullInside = false` to cull distant particles. Distant particles will trigger the early exit, skipping culling entirely and remaining 100% visible.
- **The Correct Self-Immunity Pattern (`C_OP_DistanceCull`)**:
  - Use `C_OP_DistanceCull` in `m_Operators` with `m_nControlPoint = 0`, `m_flDistance = 80.0` (as scalar double), and `m_bCullInside = true`.
  - **Mathematical Proof**:
    - Local Player: Root (`CP0`) to head offset (`CP2`, $+75Z$) is $\sqrt{0^2 + 0^2 + 75^2} = 75.0$ units. Since $75 < 80$, the particle is immediately purged on frame 0.
    - Point-Blank Touching Enemy: Capsule separation is $\ge 40$ units horizontally. Distance is $\sqrt{40^2 + 75^2} \approx 85.0$ units. Since $85 > 80$, the alert survives.
  - Setting $80.0$ avoids false-culling enemies when standing face-to-face.
- **The Correct Max Distance Cut-Off Pattern (`C_OP_DistanceToTransform`)**:
  - To prevent telegraphs from triggering when enemies charge abilities from far away (> 13 meters / 512 units), use `C_OP_DistanceToTransform` in `m_Operators`.
  - Drive Alpha (`m_nFieldOutput = 7`): `m_flInputMin = 480.0`, `m_flInputMax = 512.0`, `m_flOutputMin = 1.0`, `m_flOutputMax = 0.0` with `m_nSetMethod = PARTICLE_SET_SCALE_CURRENT_VALUE`.
  - Drive Radius (`m_nFieldOutput = 3`): `m_flInputMin = 480.0`, `m_flInputMax = 512.0`, `m_flOutputMin = 1.0`, `m_flOutputMax = 0.0` with `m_nSetMethod = PARTICLE_SET_SCALE_CURRENT_VALUE`.
  - Set `m_TransformStart` to `{ m_nControlPoint: 0 }` (the attacker). Beyond 512 units, Alpha and Radius are clamped to 0.0, rendering the particle completely invisible.
  - **CRITICAL OPERATOR ORDER**: Place `C_OP_DistanceToTransform` filters at the **VERY END** of `m_Operators` (after `C_OP_FadeInSimple` and `C_OP_InterpolateRadius`). If animation operators run after distance culling, `C_OP_FadeInSimple` will temporarily force Alpha > 0 during frame 0-3, causing distant particles to flash/pop-in briefly before disappearing.

---

## 4. Packaging and Anti-Cheat Safety

1. **VPK Packaging**:
   - Pack using standard Source 2 VPK v1 / v2 directory trees.
   - For standalone distribution without dependencies, use a pure Python VPK packager (see Section 7).
2. **Anti-Cheat (VAC) Compliance**:
   - Only modify client-side cosmetic assets (sound events, particles, audio, textures).
   - Never inject DLLs or read memory overlays (which trigger permanent VAC bans).

---

## 5. Architectural Boundaries: Panorama UI (2D) vs World Particles (3D)

### A. The In-Game Options Menu Boundary
- **Panorama Mod Scope**: Mods that add custom settings tabs into `popup_settings.vxml` (like *KillFade*) can ONLY affect 2D screen overlays, HUD panels, and JavaScript-driven UI elements.
- **Particle System Isolation**: 3D world particles (`.vpcf_c`) are compiled binary GPU assets spawned directly by Deadlock's C++ game engine. There is **no runtime bridge, ConVar, or API** allowing Panorama JavaScript to alter particle parameters (color, radius, count) during gameplay.
- **Settings File Collision**: Only ONE mod can override `panorama/layout/popups/popup_settings.vxml_c` at a time. Distributing a custom `popup_settings.vxml_c` will conflict with and disable any other UI/settings mods installed by the user.

### B. Standard Pattern for Particle Customization
- **Pre-Compiled Presets**: Distribute multiple modular VPKs (e.g., `Parry_Sparks_Orange.vpk`, `Parry_Sparks_Blue.vpk`) for users to toggle via Deadlock Mod Manager.
- **External Local Configurator**: Provide a lightweight Python / CLI builder that regenerates and packs `pak01_dir.vpk` with user-selected colors, radii, and spark counts in 1 second.

---

## 6. Architecture of a Defensive Warning System ("True" Telegraph)

To convert an offensive ability telegraph (e.g. charging heavy melee) into a personal defensive alert (like the Sekiro Perilous Attack indicator):

```
[Attacker Starts Action]
         │
         ├──► Attacker Entity Origin = CP0
         │
         ▼
[C_OP_SetControlPointToPlayer] (Pre-Emission)
         │
         └──► Binds CP2 to Local Player Entity Head (+75.0 Z)
         │
         ▼
[C_INIT_CreateWithinSphereTransform] (Initializers)
         │
         └──► Particle born directly at CP2
         │
         ▼
[C_OP_PositionLock] (Operators)
         │
         └──► Particle locked to CP2 throughout its lifetime
         │
         ▼
[C_OP_DistanceCull (m_bCullInside = true, dist = 80.0)]
         ├── If Attacker == Local Player: dist = 75.0 < 80.0 ──► DESTROY IMMEDIATELY (Self-Immunity)
         └── If Attacker == Enemy: dist >= 85.0 ──────────────► SURVIVE
         │
         ▼
[C_OP_InterpolateRadius & C_OP_FadeInSimple]
         │
         └──► Computes standard pop-in and fade curves
         │
         ▼
[C_OP_DistanceToTransform (Alpha & Radius, SCALE_CURRENT_VALUE)] (END OF PIPELINE)
         ├── If Enemy Dist <= 480u: Scale = 1.0 ──────────────► Full crisp visibility
         └── If Enemy Dist > 512u:  Scale = 0.0 ──────────────► Completely invisible (No ghost pop-in)
```

---

## 7. Standalone Python VPK v1 Packager Recipe

When packaging mods in Python without requiring external executables (`vpk.exe` or C# SDKs), use this pure standard-library packer:

```python
import os, struct, zlib, zipfile

def build_vpk(file_dict: dict[str, bytes], output_path: str):
    """Packages {internal_rel_path: file_bytes} into a valid Source 2 VPK v1."""
    tree = {}
    for path, data in file_dict.items():
        dirname, basename = os.path.split(path)
        name, ext = os.path.splitext(basename)
        ext = ext.lstrip('.')
        tree.setdefault(ext, {}).setdefault(dirname, {})[name] = data

    data_blobs, dir_entries, current_offset = [], [], 0
    for ext, dirs in tree.items():
        for dirname, files in dirs.items():
            for name, data in files.items():
                crc = zlib.crc32(data) & 0xffffffff
                length = len(data)
                dir_entries.append((ext, dirname, name, crc, current_offset, length))
                data_blobs.append(data)
                current_offset += length

    tree_bytes = bytearray()
    for ext, dirs in tree.items():
        tree_bytes.extend(ext.encode('utf-8') + b'\x00')
        for dirname, files in dirs.items():
            dir_str = dirname.replace('\\', '/') if dirname else ' '
            tree_bytes.extend(dir_str.encode('utf-8') + b'\x00')
            for name in files:
                for e in dir_entries:
                    if e[0] == ext and e[1] == dirname and e[2] == name:
                        tree_bytes.extend(name.encode('utf-8') + b'\x00')
                        tree_bytes.extend(struct.pack('<IHHIIH', e[3], 0, 0x7fff, e[4], e[5], 0xffff))
                        break
            tree_bytes.append(0)
        tree_bytes.append(0)
    tree_bytes.append(0)

    header = struct.pack('<III', 0x55aa1234, 1, len(tree_bytes))
    with open(output_path, 'wb') as f:
        f.write(header)
        f.write(tree_bytes)
        for blob in data_blobs:
            f.write(blob)
```

---

## 8. C# Asset Pipeline (`ValveResourceFormat`, `ValvePak` & `BCnEncoder.NET`)

While standalone Python scripts are ideal for packaging VPKs, **C# (.NET) is the gold standard for asset manipulation in Source 2**. The `ValveResourceFormat` (VRF) ecosystem provides complete programmatic control over binary KeyValues 3 (KV3), particle system ASTs, and resource serialization without requiring Valve's proprietary compiler tools.

### A. Recommended `.csproj` Dependencies
```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <!-- Source 2 Resource Decompiler & Serializer -->
    <PackageReference Include="ValveResourceFormat" Version="10.0.0-*" />
    <!-- VPK Archive Parser -->
    <PackageReference Include="ValvePak" Version="0.4.0-*" />
    <!-- Hardware BC3 / DXT5 Texture Compression -->
    <PackageReference Include="BCnEncoder.Net" Version="2.1.0" />
    <!-- Image Decoding & Resizing -->
    <PackageReference Include="SkiaSharp" Version="2.88.8" />
  </ItemGroup>
</Project>
```

### B. Extracting & Inspecting Game Assets from VPK (`ValvePak`)
Search and extract compiled files directly from Deadlock's `pak01_dir.vpk`:
```csharp
using ValvePak;

var package = new Package();
package.Read(@"C:\Program Files (x86)\Steam\steamapps\common\Deadlock\game\citadel\pak01_dir.vpk");

// Find entry by internal relative path
var entry = package.FindEntry("particles/abilities/melee/melee_heavy_activate_charge.vpcf_c");
if (entry != null) {
    package.ReadEntry(entry, out var bytes);
    Console.WriteLine($"Extracted {entry.FileName}.{entry.TypeName}: {bytes.Length} bytes");
}
```

### C. Programmatically Modifying and Recompiling Particles (`.vpcf_c`)
Load a binary `.vpcf_c`, manipulate its operators/initializers AST, apply `KVFlag.Resource`, and serialize back to an engine-ready binary:
```csharp
using System.IO;
using ValveResourceFormat;
using ValveResourceFormat.ResourceTypes;
using ValveKeyValue;

// 1. Load compiled resource
using var res = new Resource();
using var inStream = new MemoryStream(bytes);
res.Read(inStream);

// 2. Access the KeyValues 3 ParticleSystem data block
var ps = (ParticleSystem)res.DataBlock!;
var data = ps.Data;

// 3. Update external resource references (RERL block)
var rerl = res.ExternalReferences!;
rerl.ResourceRefInfoList.Clear();
rerl.ResourceRefInfoList.Add(new ValveResourceFormat.Blocks.ResourceExtRefList.ResourceReferenceInfo {
    Id = 0,
    Name = "materials/particle/custom_sprite.vtex"
});

// 4. Inject a PreEmission Operator (e.g. anchor CP2 to player head)
var setPlayerOp = KVObject.Collection(new[] {
    new KeyValuePair<string, KVObject>("_class", (KVObject)"C_OP_SetControlPointToPlayer"),
    new KeyValuePair<string, KVObject>("m_nCP1", (KVObject)2),
    new KeyValuePair<string, KVObject>("m_vecCP1Pos", KVObject.Array(new[] { (KVObject)0.0, (KVObject)0.0, (KVObject)75.0 })),
    new KeyValuePair<string, KVObject>("m_bOrientToEyes", (KVObject)false)
});
data["m_PreEmissionOperators"] = KVObject.Array(new[] { setPlayerOp });

// 5. CRITICAL: Reference textures or child particles with KVFlag.Resource
var childTexture = (KVObject)"materials/particle/custom_sprite.vtex";
childTexture.Flag = KVFlag.Resource; // Must set flag 1, otherwise GPU renders error 'X'

// 6. Serialize back to valid binary .vpcf_c
using var outStream = new MemoryStream();
res.Serialize(outStream);
File.WriteAllBytes("output/melee_heavy_activate_charge.vpcf_c", outStream.ToArray());
```

### D. Compiling Custom Textures (`.vtex_c`) with `BCnEncoder.NET`
Generate GPU-compliant DXT5/BC3 textures from standard PNGs:
```csharp
using BCnEncoder.Encoder;
using BCnEncoder.Shared;
using SkiaSharp;

// 1. Decode PNG and resize to power-of-two (e.g. 256x256)
using var bmp = SKBitmap.Decode("texture.png");
using var resized = bmp.Resize(new SKImageInfo(256, 256, SKColorType.Rgba8888, SKAlphaType.Unpremul), SKSamplingOptions.Default);

// 2. Hardware BC3 (DXT5) encode
var encoder = new BcEncoder();
encoder.OutputOptions.Format = CompressionFormat.Bc3;
encoder.OutputOptions.GenerateMipMaps = false;
encoder.OutputOptions.Quality = CompressionQuality.BestQuality;
var dxt5Blocks = encoder.EncodeToRawBytes(resized.Bytes, 256, 256, PixelFormat.Rgba32);

// 3. Assemble Source 2 .vtex_c binary (2068-byte header + BC3 data blocks)
// (Clone the 2068-byte RED2/DATA header from an existing vanilla 256x256 DXT5 texture)
var finalVtex = new byte[2068 + dxt5Blocks[0].Length];
Array.Copy(vanillaVtexHeader, 0, finalVtex, 0, 2068);
Array.Copy(dxt5Blocks[0], 0, finalVtex, 2068, dxt5Blocks[0].Length);
File.WriteAllBytes("materials/particle/custom_sprite.vtex_c", finalVtex);
```

---

## 9. Reverse Engineering `particles.dll` (Assembly & Binary Forensics)

During the development and debugging of low-level particle mods (such as proximity-based defensive telegraphs), binary reverse engineering of `game/bin/win64/particles.dll` via Capstone and x86-64 disassemblers revealed critical engine internals, VTable layouts, and a fundamental bug in Valve's culling logic.

### A. `C_OP_DistanceCull::Operate` & The Early-Exit Bug (`0x180187e0a`)
- **Symbol / VTable**: `C_OP_DistanceCull::Operate` (`0x180187d20 - 0x180188065`), VTable: `0x18044d9d0`, RTTI Complete Object Locator: `0x180494218`.
- **Class Memory Layout**:
  - `+0x1d8`: `m_nControlPoint` (`int32`, default: 0)
  - `+0x1dc`: `m_vecPointOffset` (`Vector3`, 12 bytes)
  - `+0x1e8`: `m_flDistance` (`CParticleCollectionFloatInput`, 368 bytes, extends to `+0x358`)
  - `+0x358`: `m_bCullInside` (`bool`, 1 byte)
  - `+0x35c`: `m_nAttribute` (`int32`, default: 1 = `LifeTime`)

- **Disassembly of the Valve Early-Exit Bug**:
  ```asm
  0x180187d20: push    rbp
  0x180187d22: push    r15
  0x180187d24: push    r14
  ...
  0x180187e05: call    0x1802cb880        ; Calculate particle collection Bounding Box (AABB) dist^2 to CP
  0x180187e0a: comiss  xmm0, xmm6         ; Compare AABB dist^2 (xmm0) with flDistance^2 (xmm6)
  0x180187e0e: jbe     0x180187e20        ; If AABB <= flDistance^2, proceed to particle loop
  0x180187e14: cmp     byte ptr [rbx+0x358], 0 ; Check m_bCullInside flag
  0x180187e18: ja      0x18018805f        ; <--- BUG! Early return without checking individual particles
  ...
  0x18018805f: pop     rbx
  0x180188060: pop     rbp
  0x180188061: ret
  ```

- **Forensic Breakdown of the Failure**:
  - Valve optimized the operator assuming `m_bCullInside == true` (culling particles *inside* a protective sphere). Under that assumption, if the entire particle bounding box is farther than `flDistance`, no particles can possibly be inside, so returning immediately (`ja 0x18018805f`) skips unnecessary SIMD loops.
  - **The Flaw**: When a developer sets `m_bCullInside = false` to cull *distant* particles, this early-exit optimization inverts into a catastrophic bypass: if an enemy particle collection is distant (`AABB > flDistance`), the engine aborts the function before checking particles. Consequently, **0 particles are culled**, and distant particles remain permanently rendered.
  - **Verdict**: `C_OP_DistanceCull` **cannot be used for maximum distance culling** (`m_bCullInside = false`). It can only be used for proximity self-immunity (`m_bCullInside = true`).

---

### B. `CParticleCollectionFloatInput` Evaluation & Deserialization (`0x18005b3a0`)
- **Evaluation Subroutine**: `0x18005b3a0` (368-byte struct evaluator).
- **Internal Offsets**:
  - `+0x14`: `m_nType` (`0 = PF_TYPE_LITERAL`, `1 = PF_TYPE_NAMED_VALUE`, `2 = PF_TYPE_MAP_RANGE`, etc.)
  - `+0x18`: `m_flLiteralValue` (`float32`, IEEE-754)
- **KV3 Serialization Quirk**:
  - If authored as a primitive scalar double in KV3 (`m_flDistance = 80.0`), the Source 2 deserializer correctly populates `m_nType = 0` and `m_flLiteralValue = 80.0f`.
  - If authored as a verbose nested subtable (`m_flDistance = { m_nType = 0, m_flLiteralValue = 80.0 }`) without exact engine schema type hashes, the dispatcher at `0x18005b50b` fails the type switch, defaulting `m_flDistance` to `0.0`. This causes proximity checks to never trigger.

---

### C. `C_INIT_DistanceCull::Operate` & Emission-Time Purge (`0x180110d90`)
- **Symbol / VTable**: `C_INIT_DistanceCull::Operate` (`0x180110d90 - 0x180110f24`), VTable: `0x180447368`.
- **Disassembly of Particle Termination**:
  ```asm
  0x180110ed4: comiss  xmm1, xmm0         ; Compare particle distance with flDistance
  0x180110ed7: jbe     0x180110f13        ; Branch if particle falls within cull condition
  ...
  0x180110f13: mov     dword ptr [rcx + rax*4], 0xbf800000 ; LifeTime = -1.0f (IEEE-754 float: -1.0)
  0x180110f1b: inc     rax
  0x180110f1e: dec     r8
  0x180110f21: jnz     0x180110ecc
  ```
- **How Source 2 Eliminates Particles**:
  - Source 2 does not deallocate memory for culled particles on the fly; it writes `-1.0f` (`0xbf800000`) into the particle's `LifeTime` attribute array (`rcx + rax*4`).
  - During the subsequent operator phase, `C_OP_Decay` checks if `LifeTime <= 0.0f` and invalidates the particle index before the GPU render submission.
- **Why `C_INIT_DistanceCull` is Insufficient for Dynamic Telegraphs**:
  - `C_INIT` operators only execute once at emission (frame 0).
  - If an enemy begins charging an ability 1,000 units away and sprints towards the player, an emission-time cull will permanently kill the particle at birth, preventing the alert from ever appearing when they enter range.
  - Furthermore, if the particle is anchored to the local player's head (+75Z), `C_INIT` measures distance to the local player, not the enemy attacker.

---

### D. `C_OP_DistanceToTransform::Operate` SIMD Batch Processing (`0x1801cb250`)
- **Symbol**: `C_OP_DistanceToTransform::Operate` (`0x1801cb250`).
- **SIMD Vectorization**:
  - Evaluates distances in batches of 4 particles using vectorized SSE/AVX instructions (`subps`, `mulps`, `sqrtps`, `maxps`, `minps`, `divps`).
  - Calculates Euclidean distance: $\Delta = \sqrt{(P_x - T_x)^2 + (P_y - T_y)^2 + (P_z - T_z)^2}$.
  - Maps $\Delta$ from `[m_flInputMin, m_flInputMax]` to `[m_flOutputMin, m_flOutputMax]`.
- **Mathematical Formula for Alpha / Radius Scaling**:
  $$\text{Factor} = \text{clamp}\left(\frac{\Delta - \text{InputMin}}{\text{InputMax} - \text{InputMin}}, 0.0, 1.0\right)$$
  $$\text{Multiplier} = \text{OutputMin} + \text{Factor} \times (\text{OutputMax} - \text{OutputMin})$$
- **Why Operator Pipeline Placement is Critical**:
  - `PARTICLE_SET_SCALE_CURRENT_VALUE` (`m_nSetMethod = 3`) performs:
    $$\text{Attribute}_{\text{final}} = \text{Attribute}_{\text{current}} \times \text{Multiplier}$$
  - If placed **before** `C_OP_FadeInSimple` or `C_OP_InterpolateRadius`, those subsequent operators blindly overwrite `Attribute`, causing distant enemies to flash a 50ms "ghost" alert before fading.
  - Placed at the **very end** of `m_Operators`, when $\Delta \ge 512.0$, $\text{Multiplier} = 0.0$, multiplying any accumulated alpha and radius by zero:
    $$\text{Alpha} = \text{Alpha}_{\text{fade}} \times 0.0 = 0.0$$
  - This mathematically guarantees zero pop-in and complete visual silence at distance.

---

## 10. Troubleshooting Guide (For the Agent)
- **Problem: "X" Error Sprites instead of Texture.**
  - *Check 1*: Is the `.vtex_c` correctly encoded in hardware DXT5 (BC3)? Uncompressed formats will fail.
  - *Check 2*: Does the `.vpcf_c` reference have `KVFlag.Resource` applied to the texture path?
- **Problem: Distant particles flash or pop in before disappearing.**
  - *Check*: Are `C_OP_DistanceToTransform` operators placed after `C_OP_FadeInSimple` and `C_OP_InterpolateRadius`? Animation operators will overwrite alpha if placed after distance filters.
- **Problem: Warning triggers on the player themselves.**
  - *Check*: Is `C_OP_DistanceCull` set to `m_bCullInside = true` with `m_flDistance = 80.0`? Player head offset (+75.0Z) must fall strictly inside this radius.
- **Problem: Distant particles never cull despite setting `C_OP_DistanceCull` with `m_bCullInside = false`.**
  - *Check*: This is caused by the engine early-exit bug in `particles.dll` (`0x180187e18`). Switch to `C_OP_DistanceToTransform` with `m_nSetMethod = PARTICLE_SET_SCALE_CURRENT_VALUE` placed at the end of `m_Operators`.
- **Problem: Sound cuts off too early.**
  - *Check*: Did you update `vsnd_duration` in `.vsndevts_c`? It must match the true duration of the new audio file.
- **Problem: No sound plays at all.**
  - *Check*: The LZ4 control block in the `.vsnd_c` is likely corrupted. Recompile via `ValveResourceFormat` (`res.Serialize()`) instead of manually hex-patching random bytes.


