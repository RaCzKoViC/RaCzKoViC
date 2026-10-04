# Profile telemetry

The profile uses real selectable ASCII text. The portrait is 48 columns wide; the information panel is 60 columns. GitHub sanitizes custom text colors in README HTML.

## Event updates

The profile refreshes on a default-branch push, manual workflow run, or `repository_dispatch` (`project_changed` / legacy `code_changed`). There is no scheduled polling.

Each existing project has `.github/workflows/notify-profile.yml`, also available as [a template](integrations/notify-profile.yml). It notifies the profile on main pushes, published/edited/deleted releases and CI runs starting/completing on main. It does not check out or execute project code, consume artifacts or caches. Its own runs and fork-origin runs are excluded. Future repositories need this workflow plus the secret below; discovery of new repositories requires a profile event.

### Required activation

Create a fine-grained personal access token owned by RaCzKoViC, restricted to **RaCzKoViC/RaCzKoViC**, with **Contents: Read and write** (metadata read is automatic), and a short expiration. Add it as an Actions repository secret named **PROFILE_DISPATCH_TOKEN** in RacOS, The-MinerGuy, Odysseus-Lab, AgentBox and CodeMap. Do not put the token in code, README, chat or workflow output.

Then run `Notify profile` manually in each project. A successful sender receives HTTP 204; verify the profile's `Update profile telemetry` run triggered by `repository_dispatch`. Until this secret exists, senders fail with an explicit setup message and cross-repository event updates are **not active**. Token expiration/revocation also stops dispatch and requires renewal. Built-in `GITHUB_TOKEN` cannot dispatch into another repository.

The generated data includes all public owned repositories that GitHub marks as non-forks. GitHub's fork flag is a counting scope, not a claim of original authorship; Odysseus-Lab's upstream origin is disclosed in the portfolio. Private repositories are excluded.

Stars and followers are captured at the next project/profile event or manual refresh; this workflow does not receive follower events.

## Counting rules

Counts come from archives pinned to the default branch's commit SHA, not cumulative additions minus deletions. They count **nonblank physical lines, including comments** in UTF-8 text files. This is a file-category metric, not a claim about authored executable statements.

- Source: Rust, Python, JavaScript/TypeScript, C/C++/C#, Java, Go, shell/PowerShell, SQL, HTML/CSS and other explicit extensions in `scripts/project_telemetry.py`. Tests and tooling source are included.
- Documentation: Markdown, reStructuredText, AsciiDoc, text, LaTeX and license/notice files.
- Configuration: JSON, YAML, TOML, INI, XML, project files, lockfiles, environment templates, Dockerfile, Makefile and Justfile.
- Excluded directories: node_modules, vendor, target, dist, build, bin, obj, .git, .venv, venv, __pycache__, coverage.
- Binary/non-UTF-8 files, unknown extensions and files over 10 MB are excluded. The generated profile README is excluded to prevent feedback. The generated portrait text is counted as documentation.

Classification is exclusive and deterministic; extension rules take precedence over containing directory names. The per-project table and aggregate use the same rules. Full archives are scanned on an event. API/archive failures preserve the existing README and fail the run rather than publishing zeros.

## Project status

Last change is the default branch HEAD commit's committer date (UTC), linked to that SHA. CI uses the latest run of every workflow on that exact SHA and branch, excluding notification workflows. A running check takes precedence; completed failure, cancellation and neutral/no-CI results are distinct. It is GitHub Actions status, not external CI. Releases use the latest published stable GitHub release; no release is shown honestly, without inferring versions from package files.

## Validation

Run `python3 -m unittest discover -s tests` and `python3 scripts/generate_stats.py`. Only a complete snapshot is written atomically. Repeat snapshots with identical data leave README unchanged. The workflow serializes profile updates; bot refresh commits do not retrigger through the built-in token.
