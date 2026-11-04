# From a protocol to an executed result, in one sitting

Run CDISC's Analysis Concepts application yourself, on a public simulated oncology trial, and
take one endpoint from its definition to a number. About an hour. Nothing to install but git
and Python; no R, the analysis runs in the browser.

## Versions — read this first

The application belongs to CDISC and is under active development. These steps were written
against one commit of it, and a later commit may show different screens or need different
clicks. Everything here is pinned, so what you get is what these steps describe.

| What | Where | Pinned at |
|---|---|---|
| The application and concept libraries | [cdisc-org/analysis-concepts](https://github.com/cdisc-org/analysis-concepts) | `739344c` |
| The study: TORIVA-LUNG 301, fully synthetic | [OpenTrialReporting/torivumab-nsclc-301](https://github.com/OpenTrialReporting/torivumab-nsclc-301) | `0f78331` |
| The set-up that pins both, plus the study definition and the saved chains | [Lovemore-Gakava/usdm-acdc-in-practice](https://github.com/Lovemore-Gakava/usdm-acdc-in-practice) | tag `quickstart-2026-11.1` |

You check out the third one. It carries the first as a read-only submodule at its pin and
fetches the second at its pin. Nothing is modified in CDISC's repository: the study and the
chains are staged into it while the server runs and removed when it stops.

## Or skip the set-up: the hosted application

The same application, at the same commit, is hosted at
<https://lovemore-gakava.github.io/usdm-acdc-quickstart/>. Nothing to install: open it, load
your own study definition at step 1 (a USDM v4 JSON file, or `?usdm=<url>` in the address),
upload your own `.xpt` datasets at step 8, and run. The study used below is not hosted, so
the worked example with its exact figure needs the local set-up; the hosted copy is for
bringing your own documents. It is assembled from the pinned sources on every publish by
`tools/build_site.py`, which refuses to build if this table and `pins.yml` disagree.

## 1. Set up

**Windows only, before cloning.** CDISC's repository has file names that overrun Windows's
default path limit once the clone sits a few folders deep, and the clone fails part-way with
*Filename too long*. Once per machine:

```bash
git config --global core.longpaths true
```

```bash
git clone --recurse-submodules https://github.com/Lovemore-Gakava/usdm-acdc-in-practice.git
cd usdm-acdc-in-practice
git checkout quickstart-2026-11.1 && git submodule update --init
python tools/bootstrap.py            # python3 on macOS and Linux; py -3 on Windows
```

The last command builds an isolated Python environment, fetches 10 MB of the study into a
sibling folder named `torivumab-nsclc-301`, and ends by running a check. It should finish with
no failures and no skips, and print the two commands for the next step. It is safe to re-run.
On a fresh Windows machine the whole step took about two minutes.

If you cloned on Windows before setting the long-path option, the clone printed three
*Filename too long* errors and left three files missing. The bootstrap restores them, and sets
the option for that clone if Windows refuses again, so run it as above; no need to re-clone.

**Windows only**, once per clone, or the engine refuses to parse at step 8:

```bash
git -C upstream/analysis-concepts config core.autocrlf false
git -C upstream/analysis-concepts checkout -- .
```

## 2. Start the application

```bash
.venv/bin/python tools/walkthrough.py serve          # macOS, Linux
.venv\Scripts\python.exe tools/walkthrough.py serve  # Windows
```

Open <http://localhost:8080/ac-dc-app/index.html>. You should see three study cards, with
**TORIVA-LUNG 301** in the middle. Press Ctrl-C when you are done; the server cleans up after
itself.

## 3. Click through to the number

The application has eight numbered steps along the top. The click-by-click version of each,
with a screenshot of what every screen should show, is served beside the app at
<http://localhost:8080/walkthrough> while the server runs. In outline:

| Step | What you do | What it establishes |
|---|---|---|
| 1 Select Study | Click the **TORIVA-LUNG 301** card | The protocol, already structured as data |
| 2 Study Overview | Read the arms, visits and estimands | Where the endpoint sits |
| 3 Endpoint | Category *Change (Comparison)*; tick the smart phrases; Parameter **Alanine Aminotransferase**, timepoint **C2D1** | What is measured, when, in whom |
| 4 Analysis | Tick **Change From Baseline ANCOVA** | How it is analysed |
| 5 Summary | One card, the endpoint in a sentence | One declaration, end to end |
| 6 Derivations | For each measure node pick *use source data directly*, tick the **ALT** concept; confirm Treatment | How the number is made, from which columns |
| 7 eSAP Builder | Generate | The analysis plan, as data |
| 8 Execute | Initialise WebR, upload `adsl.xpt` and `adlb.xpt`, set the bindings and slices as the walkthrough lists | The number |

Step 8 has one setting that fails the run if missed: the **Treatment** slice must be set to
*no filter*. The walkthrough's step 8 opens with it.

**What you should get**, at these pins: change from baseline in alanine aminotransferase at
cycle 2 day 1, placebo arm minus torivumab arm, estimate 1.276 with standard error 2.215. The
same run is recorded in the set-up repository at `endpoints/01-simple-lab-cfb/results.json`. If
yours differs, step 6 and step 8 are where the choices that move it are made.

**To skip the authoring** and go straight to execution: at step 1, click the card first, then
**Load** the saved chain `lab-chain.json`, which the server staged for you and names in its
console output. Clicking the card first matters; the walkthrough says why.

## If something goes wrong

- **Step 2 says *NOT CLEAN — foreign changes, fix by hand* and lists three *Scenario* files as
  deleted.** The clone was made before the Windows long-path setting in step 1, so the three
  files could not be written. Re-run the bootstrap; it restores them. By hand: set the option,
  then `git -C upstream/analysis-concepts checkout -- .` inside the clone. No need to re-clone.
- **`python3` fails on an import after set-up.** Use the environment's interpreter shown in
  step 2, not the system one.
- **Step 8 says *unexpected invalid token*.** The Windows line-ending fix in step 1.
- **Step 8 says *contrasts can be applied only to factors with 2 or more levels*.** The
  Treatment slice was left filtered; set it to *no filter*.
- **A concept's Reference link answers 401.** It needs a CDISC Library API key, one line in a
  file named `.cdisc-api-key` in your home directory. Nothing else needs it.
- Anything else: the set-up repository's `docs/troubleshooting.md`.

## Where this comes from

Everything you clone in step 1 is
[`Lovemore-Gakava/usdm-acdc-in-practice`](https://github.com/Lovemore-Gakava/usdm-acdc-in-practice),
the repository the work was done in. Beyond the server and the saved chains it holds the book,
[*Protocol to result*](https://lovemore-gakava.github.io/usdm-acdc-in-practice/), which explains
what each of the eight steps means and why; the click-by-click walkthrough this page summarises;
both endpoints' runs and their comparison against the study's own datasets; and the working
record of how it was all authored, including what went wrong. This page is the short way in;
that repository is the long one.

## Licences

Content based on [CDISC Analysis Concepts (GitHub)](https://github.com/cdisc-org/analysis-concepts)
is used under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). TORIVA-LUNG 301 is a
fully synthetic study, used under CC BY 4.0; its sponsor and drug do not exist. This page: MIT.
