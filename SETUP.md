# Profile telemetry

The profile uses real selectable ASCII text. The portrait is 48 columns wide; the information panel is 60 columns. GitHub sanitizes custom text colors in README HTML.

## Event updates

The profile refreshes on a default-branch push, manual workflow run, `repository_dispatch` (`project_changed` / legacy `code_changed`), and a daily scheduled run (03:23 UTC). The schedule is a safety net for changes that emit no event to the profile: repository description, topics, homepage, stars, Pages, and repositories that are created, published or archived. A run whose data is unchanged makes no commit.

RacOS, The-MinerGuy, AgentBox and CodeMap have `.github/workflows/notify-profile.yml`, also available as [a template](integrations/notify-profile.yml). Odysseus-Lab's integration was merged through [PR #44](https://github.com/RaCzKoViC/Odysseus-Lab/pull/44) after its required checks passed. It notifies the profile on main pushes, published/edited/deleted releases and CI runs starting/completing on main. Odysseus-Lab uses a reusable notification job after each main CI workflow instead of workflow_run; the receiver briefly waits for that specific notifying run to finish so its final verdict is captured. Delivery failures in that reusable job are advisory and do not change the application CI verdict. It does not check out or execute project code, consume artifacts or caches. Its own runs and fork-origin runs are excluded. Future repositories should get this workflow plus the secret below for immediate updates; without it, a newly published repository is still discovered by the next daily run.

### Required activation

Create a fine-grained personal access token owned by RaCzKoViC, restricted to **RaCzKoViC/RaCzKoViC**, with **Contents: Read and write** (metadata read is automatic), and a short expiration. Add it as an Actions repository secret named **PROFILE_DISPATCH_TOKEN** in RacOS, The-MinerGuy, Odysseus-Lab, AgentBox and CodeMap. Do not put the token in code, README, chat or workflow output.

Then run `Notify profile` manually in each project. A successful sender receives HTTP 204; verify the profile's `Update profile telemetry` run triggered by `repository_dispatch`. Until this secret exists, senders fail with an explicit setup message and cross-repository event updates are **not active**. Token expiration/revocation also stops dispatch and requires renewal. Built-in `GITHUB_TOKEN` cannot dispatch into another repository.

The generated data includes all public owned repositories that GitHub marks as non-forks. GitHub's fork flag is a counting scope, not a claim of original authorship; Odysseus-Lab's upstream origin is disclosed in the portfolio. Private repositories are excluded.

Stars and followers are captured at the next project/profile event, the daily run, or a manual refresh; GitHub sends no star or follower events to this workflow.

## Featured portfolio

The `## Featured portfolio` section is generated between `<!-- PORTFOLIO:START -->` and `<!-- PORTFOLIO:END -->` by `scripts/portfolio.py` (called from `scripts/generate_stats.py`). Do not edit that block by hand; edit [`portfolio.yml`](portfolio.yml):

- `featured` sets the order, heading, label, hand-written summary and Markdown body (run instructions and links) of each highlighted repository. Bodies may use `{{repo_url}}`, `{{website}}`, `{{latest_release}}` and `{{release_tag}}`, which resolve from live data.
- Every other public, non-fork, non-archived repository is listed automatically under *More public projects* (`more.exclude` hides repositories such as this profile). A featured entry for a private repository is skipped until the repository becomes public.

Live data per repository: description (shown as a tagline unless `tagline: false`), language, latest stable release with publication date, GitHub Actions status of the default-branch HEAD, stars, website (homepage, otherwise the GitHub Pages URL), topics and last change. Rendering contains no clock values, so identical data yields an identical README and no commit; the terminal's *Updated* time changes only when its statistics change.

## Counting rules

Counts come from archives pinned to the default branch's commit SHA, not cumulative additions minus deletions. They count **nonblank physical lines, including comments** in UTF-8 text files. This is a file-category metric, not a claim about authored executable statements.

- Source: Rust, Python, JavaScript/TypeScript, C/C++/C#, Java, Go, shell/PowerShell, SQL, HTML/CSS and other explicit extensions in `scripts/project_telemetry.py`. Tests and tooling source are included.
- Documentation: Markdown, reStructuredText, AsciiDoc, text, LaTeX and license/notice files.
- Configuration: JSON, YAML, TOML, INI, XML, project files, lockfiles, environment templates, Dockerfile, Makefile and Justfile.
- Excluded directories: node_modules, vendor, target, dist, build, bin, obj, .git, .venv, venv, __pycache__, coverage.
- Binary/non-UTF-8 files, unknown extensions and files over 10 MB are excluded. The generated profile README is excluded to prevent feedback. The generated portrait text is counted as documentation.

Classification is exclusive and deterministic; extension rules take precedence over containing directory names. The per-project table and aggregate use the same rules. Full archives are scanned on an event. API/archive failures preserve the existing README and fail the run rather than publishing zeros.

## Project status

Last change is the default branch HEAD commit's committer date (UTC), linked to that SHA. CI uses the latest run of every workflow on that exact SHA and branch, excluding notification workflows. A running check takes precedence; completed failure, cancellation and neutral/no-CI results are distinct. It is GitHub Actions status, not external CI. The profile repository itself publishes only file counts: its HEAD is normally the previous refresh commit, so recording its SHA, date or CI state would make every run commit again. Releases use the latest published stable GitHub release; no release is shown honestly, without inferring versions from package files.

## Validation

Run `python3 -m unittest discover -s tests` and `python3 scripts/generate_stats.py`. Only a complete snapshot is written atomically. Repeat snapshots with identical data leave README unchanged. The workflow serializes profile updates; bot refresh commits do not retrigger through the built-in token.

## Source provenance

The headline source counter measures project source **including retained upstream**, with identified bundled/adapted third-party source removed. It is not labelled as personal authorship. Documentation and configuration likewise describe repository files, not an author's contribution.

For Odysseus-Lab, each snapshot reads `UPSTREAM_BASE` at that snapshot's commit. It validates the repository identity and 40-character SHA, then fetches exactly that commit from `odysseus-dev/odysseus`. No moving upstream branch is used. Per same-path source file, a deterministic sequence comparison divides the current nonblank lines into retained upstream matches and surviving added/replaced lines. Deleted upstream lines are not counted. New files count as additions; renames can appear as new files. Whitespace changes can count as replacements. Later upstream imports may count as changes against the original import, so this metric is a baseline delta, not verified individual authorship.

Identified third-party source is separate: directories named node_modules, vendor, third_party, third-party, external or site-packages; plus Odysseus-Lab's `static/lib/` and adapted-code paths documented in ACKNOWLEDGMENTS.md (`services/hwfit/`, `services/research/`, `services/search/`, cookbook routes/UI, research/hwfit handlers and the cookbook script). Whole documented adapted paths are conservatively credited to third-party/adapted code; this does not claim that every line is unmodified vendor code. Unidentified third-party code can remain in project counts. Other projects have no verified upstream baseline; their source totals do not prove exclusive personal authorship.

Only tracked UTF-8 source files under the snapshot size limit are counted. Dependencies referenced by manifests, Docker images and CDN libraries are not downloaded or counted. Third-party source is not added to the headline project source count. Aggregate project source equals project-maintained/local-baseline-delta source plus retained upstream source; dependency source is disjoint.

## Narrow-screen reading

The opening text and anchor links wrap normally. The real ASCII terminal remains selectable and can be collapsed using its summary. The portfolio follows the terminal immediately, with shortened launch commands. Project status and provenance are vertical blocks, avoiding wide tables. GitHub does not support custom responsive CSS in profile Markdown; the ASCII terminal can still scroll horizontally on a narrow screen while ordinary prose wraps.
