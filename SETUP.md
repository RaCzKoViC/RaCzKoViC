# Profile deployment

1. Create a **public** GitHub repository named exactly `RaCzKoViC`, owned by `RaCzKoViC`.
2. Upload the package contents at the repository root, including `assets`, `scripts` and `.github`. Do not upload just this ZIP or put the files inside an extra folder.
3. Keep `README.md` at the root of the default branch. GitHub displays it on the profile Overview.
4. The telemetry workflow runs on its initial push, then every six hours. You can also run **Actions → Update profile telemetry → Run workflow**. It uses the built-in `GITHUB_TOKEN`; no personal token is required.
5. If Actions are restricted by repository settings, allow this workflow and its `contents: write` permission. Branch rules can also block the bot from pushing.

## Layout and reliability

- Single-column Markdown and a separate portrait keep body text readable on phones.
- Both SVG cards are self-contained and include `viewBox` scaling and accessible descriptions.
- All images are stored in this repository. No external stats, streak or icon service is required.
- Telemetry is fetched completely before the SVG is replaced. An API failure leaves the last successful card intact.
- Numbers cover public data only; star and fork totals exclude forked repositories.
- The timestamp indicates freshness. GitHub Actions schedules and image caching can delay visible updates.

## Final verification after publication

Open the actual profile at desktop and phone widths. Check image loading, navigation links and all five project links. Verify that the initial Actions run succeeds and the statistics timestamp refreshes. Local checks cannot substitute for checking the published profile.
