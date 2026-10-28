"""Cek struktur skill agent-workflow: invarian yang harus tetap benar di setiap versi.

- frontmatter SKILL.md (nama, panjang description) dan versi yang sama di SKILL.md, changelog, dan plugin.json;
- file yang dirujuk SKILL.md ada, fence Markdown seimbang, akhir baris LF, skrip bisa dikompilasi;
- template T1–T9 lengkap, brief executor RENDAH (T2b) tetap ringkas, Pelajaran bernomor urut;
- setiap penanda di blok `penanda` changelog punya baris tabel, teksnya ada di template yang menghasilkan file
  sasarannya, dan aturannya membawa tag `<!-- aw: ID -->` di setiap varian template (TINGGI/SEDANG, RENDAH, LITE).

Pemakaian: python tests/check_skill.py <folder skill>
"""
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):  # konsol Windows (cp1252) tidak boleh membuat cek crash
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
d = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "plugins/agent-workflow/skills/agent-workflow"
gagal = []


def cek(cond, pesan):
    print(("OK    " if cond else "GAGAL ") + pesan)
    if not cond:
        gagal.append(pesan)


def baca(rel):
    return (d / rel).read_text(encoding="utf-8")


sk, tp, cl = baca("SKILL.md"), baca("references/templates.md"), baca("references/changelog.md")

# Frontmatter dan versi
fm = re.match(r"^---\n(.*?)\n---\n", sk, re.S)
cek(bool(fm), "SKILL.md diawali frontmatter")
nama = re.search(r"^name: (.+)$", fm.group(1), re.M).group(1).strip() if fm else ""
desc = re.search(r"^description: (.+)$", fm.group(1), re.M).group(1).strip() if fm else ""
cek(nama == d.name and re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", nama or "-") is not None, f"name '{nama}' = nama folder, kebab-case")
cek(0 < len(desc) <= 1024 and "<" not in desc and ">" not in desc, f"description {len(desc)} karakter (≤ 1024, tanpa < >)")
n_baris = sk.count("\n")
cek(n_baris <= 500, f"SKILL.md {n_baris} baris (≤ 500; rincian dipindah ke references/)")
mv = re.search(r"\*\*Versi skill: (\d+(?:\.\d+)*)\.\*\*", sk)
blok = re.search(r"```penanda\n(.*?)\n```", cl, re.S)
rows = [l.split(None, 2) for l in (blok.group(1).splitlines() if blok else []) if l.strip() and not l.lstrip().startswith("#")]
versi = sorted({r[0] for r in rows}, key=lambda v: tuple(map(int, v.split("."))))
cek(bool(mv) and bool(versi) and mv.group(1) == versi[-1], f"versi SKILL.md ({mv and mv.group(1)}) = versi penanda tertinggi ({versi and versi[-1]})")
for v in versi:
    cek(re.search(rf"^## v{re.escape(v)} ", cl, re.M) is not None, f"changelog punya bagian ## v{v}")
plugin = d.parent.parent / ".claude-plugin" / "plugin.json"
if plugin.is_file():
    pj = json.loads(plugin.read_text(encoding="utf-8"))
    cek(pj.get("version", "").split(".")[:len(mv.group(1).split("."))] == mv.group(1).split(".") if mv else False,
        f"plugin.json version {pj.get('version')} sesuai versi skill {mv and mv.group(1)}")

# File, fence, akhir baris, kompilasi
for rel in sorted(set(re.findall(r"`((?:references|scripts)/[\w.-]+\.(?:md|py))`", sk))):
    cek((d / rel).is_file(), f"{rel} yang dirujuk SKILL.md ada")
for p in sorted(d.rglob("*")):
    if p.is_file() and p.suffix in (".md", ".py"):
        rel = p.relative_to(d).as_posix()
        isi = p.read_bytes()
        cek(b"\r\n" not in isi, f"{rel}: akhir baris LF")
        if p.suffix == ".md":
            t = isi.decode("utf-8")
            cek(t.count("```") % 2 == 0 and t.count("~~~") % 2 == 0, f"{rel}: fence seimbang")
        else:
            try:
                compile(isi.decode("utf-8"), rel, "exec")
                cek(True, f"{rel}: terkompilasi")
            except SyntaxError as e:
                cek(False, f"{rel}: terkompilasi ({e})")
cek("{{" not in sk.replace("`{{...}}`", "").replace("`{{`", ""), "SKILL.md tanpa placeholder {{...}} yang tertinggal")

# Template dan Pelajaran
seksi = {}
for k in ("T1", "T2a", "T2b", "T3", "T4", "T5", "T6", "T7", "T8", "T9"):
    ada = f"### {k} " in tp
    cek(ada, f"templates.md punya {k}")
    seksi[k] = tp.split(f"### {k} ")[1].split("\n### ")[0].split("\n## Penyesuaian")[0] if ada else ""
m2b = re.search(r"~~~markdown\n(.*?)\n~~~", seksi["T2b"], re.S)
cek(bool(m2b) and m2b.group(1).count("\n") + 1 <= 80, f"T2b (brief executor RENDAH) ≤ 80 baris ({m2b.group(1).count(chr(10)) + 1 if m2b else '-'})")
pel = sk.split("## Pelajaran")[1].split("\n## ")[0] if "## Pelajaran" in sk else ""
nomor = [int(n) for n in re.findall(r"^(\d+)\. \*\*", pel, re.M)]
cek(bool(nomor) and nomor == list(range(1, len(nomor) + 1)), f"Pelajaran bernomor urut 1..{len(nomor)}")
for n in sorted({int(n) for n in re.findall(r"Pelajaran (\d+)", sk + tp + baca("references/rendah.md"))}):
    cek(n <= len(nomor), f"rujukan Pelajaran {n} ada")

# Penanda changelog vs template dan tag
ids = [r[1] for r in rows]
cek(len(ids) == len(set(ids)), "ID penanda unik")
tabel = set(re.findall(r"^\|\s*([A-Z]\d*-?\d+)\s*\|", cl, re.M))
cek(set(ids) <= tabel, f"setiap penanda punya baris tabel di changelog (kurang: {sorted(set(ids) - tabel)})")
TAG = re.compile(r"<!--\s*aw:([^>]*?)-->")
FILE_SEKSI = {"handoff/reports/REPORT_TEMPLATE.md": "T6", "handoff/STRUKTUR.md": "T9", "handoff/PROMPT_EXECUTOR.md": "T7",
              "handoff/README.md": "T3", "handoff/ROADMAP.md": "T4"}
VARIAN = {"TINGGI/SEDANG": {"head": "T1", "executor": "T2a", "readme": "T3", "roadmap": "T4", "notes": "T5"},
          "RENDAH": {"head": "T1", "executor": "T2b", "readme": "T3", "roadmap": "T4", "notes": "T5"},
          "LITE": {"dev": "T8", "notes": "T5", "roadmap": "T4"}}


def tag_di(sek):
    return {i for m in TAG.finditer(seksi.get(sek, "")) for i in re.split(r"[\s,]+", m.group(1).strip()) if i}


def cocok(teks, isi):
    teks = teks.strip()
    return re.search(teks[3:], isi, re.I) is not None if teks.startswith("re:") else teks.lower() in isi.lower()


def nilai(spec, varian, pid):
    """(teks dipenuhi template, tag ada) untuk satu spesifikasi; None untuk penanda netral bahasa."""
    spec = spec.strip()
    if spec.startswith("tampak~"):
        return None
    if spec.startswith("ada~"):
        return None
    jenis, teks = spec.split("~", 1)
    if jenis.startswith("file:"):
        path = jenis[5:].strip()
        if path.startswith("handoff/tools/"):
            skrip = d / "scripts" / Path(path).name
            return (skrip.is_file() and cocok(teks, skrip.read_text(encoding="utf-8")), True)
        sek = FILE_SEKSI.get(path)
    else:
        sek = varian.get(jenis.strip())
    if not sek:
        return (False, False)
    return (cocok(teks, seksi[sek]), pid in tag_di(sek))


for versi_p, pid, sisa in rows:
    specs = [s for s in re.sub(r"@bila_\w+", "", sisa).split("||") if s.strip()]
    for nama_var, varian in VARIAN.items():
        if nama_var == "LITE" and not any(s.strip().split("~")[0] in ("dev", "notes") for s in specs):
            continue
        hasil = [h for h in (nilai(s, varian, pid) for s in specs) if h is not None]
        if not hasil:
            continue
        cek(any(t for t, _ in hasil), f"penanda {pid} (v{versi_p}): teksnya ada di template ({nama_var})")
        cek(any(g for _, g in hasil), f"penanda {pid} (v{versi_p}): bertag <!-- aw: {pid} --> di template ({nama_var})")
semua_tag = {i for m in TAG.finditer(tp) for i in re.split(r"[\s,]+", m.group(1).strip()) if i and i != "ID"}
cek(semua_tag <= set(ids), f"setiap tag di templates.md menyebut penanda yang ada (asing: {sorted(semua_tag - set(ids))})")

print(f"\nHASIL: {'SEMUA OK' if not gagal else f'{len(gagal)} GAGAL'}")
sys.exit(1 if gagal else 0)
