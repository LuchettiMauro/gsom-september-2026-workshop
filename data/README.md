# data/

| File | What it is | Committed? |
|---|---|---|
| `corpus_manifest.json` | The 42 chosen documents: id, title, theme | yes |
| `docs/*.md` | The documents themselves, as OCR text | fetched |
| `nuforc.parquet` | ~60,000 UFO sighting reports | fetched |
| `lancedb_prebuilt.tar.gz` | The vector index, prebuilt | yes |
| `example_traces.json` | Fallback traces for session 2 | yes |
| `eval_labels_multi.csv` | Human labels for judge alignment | yes, incomplete |

Fetch the two downloadable ones with:

```bash
uv run python scripts/fetch_data.py
```

Provenance and licensing: see [`../NOTICE`](../NOTICE).

---

## `eval_labels_multi.csv` — needs real annotators

**This file currently holds labels from one annotator and that is not enough.**

Notebook 08's closing move is to show that before you can align a judge with
humans, the humans have to agree — and that they frequently don't. That requires
**two or three people labelling the same traces independently**.

The file is in long format, so adding an annotator means adding rows:

```csv
trace_ref,annotator,grounded,note
example-00,author,false,counting question answered from retrieved prose
example-00,anna,false,made up a number
example-00,luca,true,seemed fine to me
```

`grounded` is binary. `true` means every claim is supported by the corpus **and**
claims made by the documents are reported as claims rather than asserted as
fact. That distinction is where annotators disagree, which is the point.

Roughly 30 minutes per annotator for the 20 traces.

**Do not synthesise the disagreement.** Two competent people genuinely differing
on "is this grounded?" teaches something; invented disagreement teaches a number.
Until real annotators are added, notebook 08 will say so rather than print a
meaningless kappa.
